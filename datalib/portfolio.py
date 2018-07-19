#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Wrapper around portfolio information from DynamoDB
    
    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from uuid import uuid1
from decimal import Decimal
from analytics.time_series import align_series
from numpy import matrix
from pandas import Series

class Portfolio:
    def __init__(self, data):

        self.coins = None
        for key in data.keys():
            self.__dict__[key] = data[key]

        if 'HashKey' not in data:
            self.HashKey = str(uuid1())
            
        if 'Allocations' not in data:
            self.Allocations = []

    def __repr__(self):
        return str(self.__dict__)

    def to_db_item(self):
        """
            prepare dictionary data that can be presisted to dynamodb
        """
        data = {}
        for k in self.__dict__.keys():
            val = self.__dict__[k]
            if type(val) is float:
                val = Decimal(str(val))
            data[k] = val
        return data
  
    def get_coins(self, db):
        return [db.get_coin(a['HashKey'],get_ts=True) for a in self.Allocations]
                 
    def calc_proforma(self,db, new_weights = [],update_common_ts=True):
        """
            calcualte portfolio proforma time series
        """
        if len(self.Allocations) > 0:
            get_w = lambda : [float(a['Allocation']) for a in self.Allocations]
            
            weights =  new_weights if len(new_weights) > 0 else get_w()
            good_weights = [w for w in weights if w > 0.0]
            
            if update_common_ts:
                if not self.coins:
                    self.coins = self.get_coins(db)
                   
                perfs = []
                for coin,w in zip(self.coins,weights):
                    if w > 0:
                        if len(coin.Performance) == 0.0:
                            coin2 = db.get_coin(coin.HashKey,get_ts=True)
                            coin.Performance = coin2.Performance
                        else:
                            perfs.append(coin.Performance)
     
                self.common_ts = align_series(perfs)
  
            ret_m = matrix(self.common_ts.values)
            W = matrix(good_weights)
           
            proforma = ret_m * W.T
            prof_array = [p[0,0] for p in proforma]
            dates = self.common_ts.index
            return Series(data=prof_array, index=dates, name=self.Name)            
        return Series()
        
