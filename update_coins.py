#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 13:11:48 2016

@author: coin-ai
"""

from datalib.datalib import Connection 
from datalib.coin import Coin
from datetime import datetime 
from analytics.time_series import get_frequency

db = Connection()
COINS = db.get_all_coins()
table = db.get_table("COIN")

for COIN in COINS:
    # print(COIN.Name)
    ts = COIN.Performance
    T = len(ts)
    mx = int(max(ts.index).timestamp())
    mn = int(min(ts.index).timestamp())
    item = COIN.to_db_item()
    item['MaxDate'] = mx
    item['MinDate'] = mn
    item['Frequency'] = get_frequency(ts)
    item['T'] = T
    table.put_item(Item=item)
    # print("COIN updated: %s" % COIN.Name)

 
