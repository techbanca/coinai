# -*- coding: utf-8 -*-
"""
    Classes for parsing Coin data from Excel
    

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""


import pandas as pd 
from decimal import Decimal
from datetime import datetime
from datalib.coin import Coin
   
       
def get_static_info(ownerid, filename,  keyname = 'ManagerName'):
    """
        reads Coin reference data
    """
    coin_info = pd.read_excel(filename,
                              sheetname="List",
                              header=1)
    
    keys = coin_info[keyname].values
    coin_info.index = keys
    cols = coin_info.columns
    coins = []
    for ic in range(1,len(cols)):
        key_value = cols[ic]
        col = coin_info.iloc[:,ic]
        coin_dict = dict(col)
        coin_dict[keyname] = key_value
        coins.append(Coin(OwnerId=ownerid, Data=coin_dict))
    return coins

def parse_coin_from_excel(ownerid,filename,key_field = 'ManagerName'):
    coins = get_static_info(ownerid,filename, keyname=key_field)
    perf_info = pd.read_excel(filename,
                              sheetname="Performance",
                              header=3,index_col=0)
    cols = len(perf_info.columns)
    T = len(perf_info)
    perf_data = []
    for idx, coin in enumerate(coins):
        coin_ts = []
        if idx < cols:
            for t in range(T):
                tstamp = perf_info.index[t]
                if not isinstance(tstamp, pd.tslib.Timestamp):
                    try:
                        tstamp = pd.Timestamp(tstamp)
                    except:
                        continue
                if isinstance(tstamp, pd.tslib.Timestamp):
                    dtvalue = int(tstamp.timestamp())
                    dtstr = datetime.fromtimestamp(dtvalue).strftime("%m/%d/%Y")
                    perf = perf_info.iloc[t,idx]
                    if 'float' in perf.__class__.__name__:
                        val = round(Decimal(str(perf)),3)
                        if not val.is_nan():
                            if not val.is_infinite():
                                coin_ts.append({
                                                "CoinID":coin.HashKey,
                                                "EffectiveDate":dtvalue,
                                                'DateString':dtstr,
                                                "NetReturn":val})
        perf_data.append(coin_ts)

    return coins,perf_data


"""
    For Testing
"""
if __name__ == '__main__':
    coindata = parse_coin_from_excel("73ae8c18e3d964fe0eb5f73db45c5e9dbb34d4d3","/home/ec2-user/Banca/banca_application/static/temp/coinImportTemplateBTC.xlsx","ManagerName")
    
    
    
