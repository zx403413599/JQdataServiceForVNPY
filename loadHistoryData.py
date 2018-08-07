# -*- coding: utf-8 -*-
# @Time    : 2018-08-06 14:35
# @Author  : Dingzh.tobest
# 文件描述  ： 加载历史数据到mongodb

# encoding: UTF-8

from __future__ import print_function
import sys
import json
from datetime import datetime
from time import time, sleep

from pymongo import MongoClient, ASCENDING

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME

import pandas as pd
import os

# 加载配置
config = open('config.json')
setting = json.load(config)

MONGO_HOST = setting['MONGO_HOST']
MONGO_PORT = setting['MONGO_PORT']

mc = MongoClient(MONGO_HOST, MONGO_PORT)        # Mongo连接
db = mc[MINUTE_DB_NAME]                         # 数据库

futures_symbol_map = {}


# ----------------------------------------------------------------------
def generateVtBar(symbol, d):
    """生成K线"""
    bar = VtBarData()
    bar.vtSymbol = symbol
    bar.symbol = symbol
    bar.open = float(d['open'])
    bar.high = float(d['high'])
    bar.low = float(d['low'])
    bar.close = float(d['close'])
    bar.date = datetime.strptime(d['Unnamed: 0'][0:10], '%Y-%m-%d').strftime('%Y%m%d')
    bar.time = d['Unnamed: 0'][11:]
    bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
    bar.volume = d['volume']

    return bar

def loadHistoryData(data_path):
    file_list = os.listdir(data_path)
    # 上次添加到670， BU1512已导入
    last = 548

    i = 1
    count = len(file_list)
    for file_name in file_list:
        start = time()

        symbol_name = file_name[0: -8]

        if last <= i:
            print(u'合约%s数据开始导入' % (symbol_name))
        else:
            print(u'合约%s数据已经导入，跳过' % (symbol_name))
            i += 1
            continue

        if symbol_name[0: -4] in futures_symbol_map.keys():
            symbol_name = futures_symbol_map[symbol_name[0: -4]] + symbol_name[-4:]

        file_path = data_path + '\\' + file_name
        minute_df = pd.read_csv(file_path, encoding='GBK')
        i += 1
        if minute_df.empty:
            print(u'合约%s数据为空跳过，进度(%s / %s)' % (symbol_name, str(i), str(count)))
            continue

        cl = db[symbol_name]
        cl.ensure_index([('datetime', ASCENDING)], unique=True)  # 添加索引
        data_list = []
        for index, row in minute_df.iterrows():
            bar = generateVtBar(symbol_name, row)
            d = bar.__dict__
            # 单条插入效率太低，并且首次数据都是批量进行插入，不存在修改的问题，改为批量插入
            # flt = {'datetime': bar.datetime}
            # cl.replace_one(flt, d, True)
            data_list.append(d)

        cl.insert_many(data_list)

        e = time()
        cost = (e - start) * 1000

        print(u'合约%s数据导入完成，耗时%s毫秒，进度(%s / %s)' % (symbol_name, cost, str(i), str(count)))

    print('--------历史数据导入完成--------')

if __name__ == '__main__':
    # 加载字典信息，历史数据文件中品种都是大写，需要增加信息，将某些转化为小写
    print('------历史数据文件导入开始------')
    symbol_df = pd.read_csv('futures_type.csv', encoding='GBK')

    for index, row in symbol_df.iterrows():
        futures_symbol_map[row['type'].upper()] = row['type']
    print('字典信息加载完毕，开始导入历史数据')

    loadHistoryData('D:\\stockdata\\futuresminuteprices')
