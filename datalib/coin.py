#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Classes for processing / dealing with Coin data

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""


from uuid import uuid1
from datetime import datetime
from pandas import Series

from analytics.time_series import logreturns,get_frequency
from decimal import Decimal
from analytics.time_series import freq_map

class AnnualPerformance:  
    """
        Performance grouped by year
        Useful for presenting performance table in Coin Portal
    """
    def __init__(self, year):
        self.year = year
        self.months = [''] * 12 
        self.ytd = 0
        
    def __repr__(self):
        return "%s:%s" % (self.year, self.months)
        
    def calc_month_table(self):
        to_str = lambda p: "" if p == '' else "%4.2f" % (p*100) 
        self.ytd_str = "%4.2f" % (self.ytd*100)
        self.month_table = [to_str(m) for m in self.months]
                    
class CoinPerformance:
    
    def __init__ (self, series):  
        self.series = series
        if len(series) < 2:
            self.freq = 'M'
        else:
            self.freq = get_frequency(series)
            self.month_dict = {}
        
        freq_idx = freq_map[self.freq[0]]

        """
            month dict contains peformance data for getting list of date 
            with perormance for each month. this allows us to drill down into
            each month performance
        """
        dates = series.index
        values = series.values
        for d,v in zip(dates,values):
            index = d.year * 100 + d.month 
            if index in self.month_dict:
                arr = self.month_dict[index]
                arr.append((d.strftime("%m/%d"),"%0.2f" %(v*100)+"%"))
            else:
                self.month_dict[index] = [(d.strftime("%m/%d"),"%0.2f" %(v*100)+"%")]
  
        if freq_idx == 12:
           self.monthly = series
           
        if freq_idx > 12:
            self.monthly = series.resample("M").apply(logreturns)

        self.annual = series.resample("A").apply(logreturns)
      
        monthly_index = self.monthly.index
        self.ann_perf = []
        for year_index in self.annual.index:
            y = year_index.year
            perf = AnnualPerformance(y)
            midx = [m for m in monthly_index if m.year == y]
            for m in midx:
                perf.months[m.month-1] = self.monthly[m]
           
            perf.ytd = self.annual[year_index]
            perf.calc_month_table()
            self.ann_perf.append(perf)
            
        self.series.sort_index(inplace=True)
 
class Coin:
    """
        Main class for Coin level data
    """

    def import_dict(self,Coindict):
        """
        used for parsing data that comes from JSON type structure or DynamoDB
        """
        for key in Coindict.keys():
            val = Coindict[key]
            classname = val.__class__.__name__
            if 'float' in classname:
                decvalue =  Decimal(str(val))
                if decvalue.is_nan():
                    decvalue = Decimal(0)
                clean_value = decvalue
            else:
                clean_value = val
            self.__dict__[key] = clean_value
        if 'Benchmarks' not in self.__dict__:
            self.Benchmarks = []

    def __init__(self,*,OwnerId=None,Data={}):
        self.import_dict(Data)
        self.OwnerID = OwnerId if OwnerId else Data['OwnerID']
        if 'HashKey' not in self.__dict__:
            self.HashKey = str(uuid1())  

        if "Name" not in self.__dict__:
            if "CoinName" in self.__dict__:
                self.Name = self.__dict__["CoinName"]
            else:
                self.Name = "Coin %s" % self.HashKey

        if 'IsPortfolio' not in Data:
            self.IsPortfolio = False
    
        if 'Frequency' not in Data:
            self.Frequency = "M"
            
        float_fields = ['CoinCAP','ManagementFee','PerformanceFee','ManagerCAP']
        for field in float_fields:
           
            if hasattr(self,field):
                setattr(self,field,float(getattr(self,field)))
            else:
                setattr(self,field,0)
        
        if 'Performance' in self.__dict__:
            
            dates = [datetime.fromtimestamp(p['EffectiveDate']) for p in self.Performance]
            rets = [float(p["NetReturn"]) for p in self.Performance]
            self.Performance = Series(data=rets, index=dates, name=self.Name)
            self.Performance.sort_index(inplace=True)
            if len(self.Performance) > 3:
                self.Frequency = get_frequency(self.Performance)
            self.T = len(self.Performance)
        else:
            self.Performance = Series()
            
        if 'MaxDate' in self.__dict__:
            self.MaxDate = datetime.fromtimestamp(self.MaxDate)
            
        if 'MinDate' in self.__dict__:
            self.MinDate = datetime.fromtimestamp(self.MinDate)

    def perf_data(self):

        if 'Performance' in self.__dict__:
            tm = lambda d: int(d.timestamp())
            dates = [tm(t) for t in self.Performance.index]
            vals = self.Performance.values
            ph = lambda d,v :  {'EffectiveDate':d, 'NetReturn':Decimal(str(v))}
            hist = [ ph(d,v) for d,v in zip(dates,vals)]
            return hist
        return []
      
   

    def to_db_item(self):
        """
            create dictionary object that can be stored in DynamodDB
        """
        data = {}
        for key in self.__dict__.keys():
            if key != 'Performance':
                val = self.__dict__[key]
                if type(val) is float:
                    res = round(Decimal(val),5)
                else:
                    res = val
                data[key] = res
        if 'MaxDate' in data:
            data['MaxDate'] = int(self.MaxDate.timestamp())
        return data
    

    def __repr__(self):
        return str(self.__dict__)
