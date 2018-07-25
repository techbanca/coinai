#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Classes for dealing with time series data
    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import math
from numpy import mean
from pandas import  infer_freq, DataFrame
from dateutil.relativedelta import relativedelta


def prev_eom(dt):
    """
    previous calendar end of month
    """
    day = dt.day
    delta = relativedelta(days = -1* day)
    return dt + delta

def has_strings(array):
    r = [a for a in array if type(a) is str]
    return len(r) > 0

def logreturns(array):
    
    """
        Calculate cumulative returns 
    """
    if has_strings(array):
        return array[-1]
    return math.exp(sum([math.log(a+1) for a in array]))-1

#Mapping of time series frequency codes to number of periods and back
#B - business day. D- Calendar day
freq_map  = {"B":250,"D":365,"d":365, "W":52,"H":8760,"h":144,"M":12,"A":1,"2":52,"Z":9999}
freq_rev_map = {250:"B", 365:"D", 1:"A",12:"M", 52:"W", 0:"Z", 8760:"H",144:"h"}

def count(array):
    try:
        return len(array)
    except:
        return 1

def get_frequency(series, per_type="day"):
    """
        figure out time series frequency
    """
    if len(series) < 3:
        return "Z"

    f = infer_freq(series.index)
    if f == None:
        if per_type == "hour":
            ts2 = series.resample('h').apply(count)
            m = mean(ts2.values)
        else:
            ts2 = series.resample('M').apply(count)
            m = mean(ts2.values)
        if m == 1:
            if per_type == "hour":
                return 'h'
            else:
                return 'M'
        if m < 6:
            if per_type == "hour":
                return 'h'
            else:
                return 'W'
        return 'D'
    return f[0]


def convert_freq(ser,target_freq):

    return ser.resample(target_freq, fill_method=None).apply(logreturns)
    
    
def align_series_frequency(series_arr, per_type="day"):
    """
        bring an array of time series to the most common frequency for all
        So if we have an array with daily, weekly and monthly series we will 
        get an array of monthly series where daily and weekly series will be 
        aggregated by month using logreturns function
    """
    
    good_series = [s for s in series_arr if len(s) > 0]
    freqs = [freq_map[get_frequency(ser, per_type)[0]] for ser in good_series]
    min_freq = min(freqs)
    target_freq = freq_rev_map[min_freq]
    series_list = [ser.resample(target_freq, fill_method=None).apply(logreturns) for ser in good_series]
    return series_list

def align_series(series_arr, jointype='inner', per_type="day"):
    """
        Allign series to have the same start and end dates.
        If join type is not inner then some returns may turn out to be NA but 
        overall time series would be longer since N/A points won't be dropped
    """

    series_common = align_series_frequency(series_arr, per_type=per_type)
    df = DataFrame(series_common[0])
    df['Date'] = df.index
    N = len(series_common)
    for i in range(1,N):
        newdf = DataFrame(series_common[i])
        newdf['Date'] = newdf.index                        
        df = df.merge(newdf,how=jointype,on='Date')
    df.index = df['Date']
    df = df.drop('Date',axis=1)
    
    return df
