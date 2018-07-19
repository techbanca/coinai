#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Library for uploading portfolio allocation data to DynamoDB

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import xlwt
import pandas as pd
from datalib.datalib import Connection 
from decimal import Decimal
from datalib.coin import Coin
from analytics.time_series import get_frequency
from datalib.portfolio import Portfolio

alloc_sort = lambda a: a.Name

def create_allocation_template(userid,portfolio_id, target_file):
    """
        Creates excel file with current allocations as well as all Coins
        that can be included in portfolios
    """
    try:

        db = Connection()
        watched_coins = sorted(db.get_watched_coins(userid,get_ts=True),key=alloc_sort)
        port = db.get_portfolio(userid,portfolio_id)
        allocs = port.Allocations
        alloc_ids = [a['HashKey'] for a in allocs]
        wb = xlwt.Workbook()
        wsh = wb.add_sheet('Allocations')
        wsh.write(0,0,"CoinID")
        wsh.write(0,1,"Name")
        wsh.write(0,2,"Allocation")
        wsh.write(0,3,"T")
        wsh.write(0,4,"Start Date")
        wsh.write(0,5,"End Date")
        wsh.write(0,6,"Frequency")

        def write_coin_stats(coin,i):
            wsh.write(i+1,3,len(coin.Performance))
            if (len(coin.Performance)) > 0:
                    wsh.write(i+1,4,min(coin.Performance.index).to_datetime().strftime("%m/%d/%Y"))
                    wsh.write(i+1,5,max(coin.Performance.index).to_datetime().strftime("%m/%d/%Y"))
                    wsh.write(i+1,6,get_frequency(coin.Performance))
        
        for i,alloc in enumerate(allocs):
            hashkey = alloc['HashKey']
            name = alloc['Name']
            coin = db.get_coin(hashkey)
            w = alloc['Allocation']
            wsh.write(i+1,0,hashkey)
            wsh.write(i+1,1,name) 
            wsh.write(i+1,3,w)
            write_coin_stats(coin,i)
       
        i = len(allocs)
        for coin in watched_coins:
            if coin.HashKey not in alloc_ids:
                wsh.write(i+1,0,coin.HashKey)
                wsh.write(i+1,1,coin.Name)
                wsh.write(i+1,2,0)
                write_coin_stats(coin,i)
                i = i + 1
        wb.save(target_file)

    except Exception as ex:
        return False
    return True
    
def recalculate_portfolio_coin(portfolio_id, user_id, proforma, name,db = None):
    """
         recalculate performance of the Coin associated with portfolio
    """
    coin = db.get_coin(portfolio_id)
    if not coin:
        data = {'HashKey':portfolio_id,'IsPortfolio':1,'OwnerID' : user_id,"Name":name}
        coin = Coin(owner=user_id,Data=data)
        coin.ManagementFee = 0
        coin.PerformanceFee = 0
        coin.CurrencyCode = 'USD'
        coin.CoinCAP = 0
        coin.Name = name
        coin.HurdleRate = 0
        coin.lowername = name.lower()
        coin.ManagerName = 'Banca'
        coin.MinInvestment = 0
        coin.RedemptionFrequency = 0
        coin.StrategyCode = 'Coin of Coins'
        coin.T = len(proforma)
    
    coin_table = db.get_table("Coin")
    coin_table.put_item(Item=coin.to_db_item())
    
    db.save_performance(portfolio_id, proforma)
    return coin



def upload_portfolio_allocations(user_id, portfolio_id, filename,name):
    df = pd.read_excel(filename)
    db = Connection()
    table = db.get_table("Portfolio")
    info = lambda f: {"HashKey":f["CoinID"], "Name":f["Name"], "Allocation":Decimal(str(f["Allocation"]))}
    
    allocs = [info(df.iloc[i]) for i in range(len(df))]
    
    for a in allocs:
        coin = db.get_coin(a['HashKey'],get_ts=True)
        if len(coin.Performance) < 6:
            a['Allocation'] = Decimal(0)
    
    updates = {"Allocations":{"Value":allocs,"Action":"PUT"}}
    key = {"CompanyID":user_id, "HashKey":portfolio_id}
    table.update_item(Key=key,AttributeUpdates=updates)
    port = Portfolio({"HashKey":portfolio_id, "Allocations":allocs, "Name":name})
    
    proforma = port.calc_proforma(db)
    recalculate_portfolio_coin(portfolio_id, user_id, proforma, name,db)
