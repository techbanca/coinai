#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Basic Statistics

    This module contains basic hedge Coin statistics.
    It does not include any statistics that incorporate benchmark. 

    Note that for Sortino we use two different ways of calculating denominator
    1. Downside deviation (standard deviation where mean is 0)
    2. Standard deviation - (actual standard deviation of losses)

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import numpy as np
import scipy.stats as stats
from pandas import Series,  DataFrame
from analytics.time_series import get_frequency
from logger.client import debug_info

ann_factor = {"M":12, "A":1,"D":365,"B":250,"W":52 ,"Z":0, "H":8760,"h":72}

def adj_z_score(z_0, s, k):
    """
        Adjusted z-score for calculating Cornish Fisher VaR
    """
    z = np.abs(z_0)
    z2 = z ** 2
    z3 = z ** 3
    a =  z + (z2 - 1) * s / 6 
    b = (z3 - 3 * z) * k / 24
    c = (2 * z3 - 5 * z) * (s**2) / 36 
    return a + b - c

def cvar(rets):
    mu = np.mean(rets)
    st = np.std(rets)
    sk = stats.skew(rets)
    ku = stats.kurtosis(rets) + 3.0
    zadj = adj_z_score(1.96, sk,ku)
    z_step = (5 -zadj) * 0.0001
    
    z_values = [zadj + z_step * i for i in range(1000)]
    cvar_losses = [mu - st * z for z in z_values]
    
    return np.mean(cvar_losses)
    
class BasicStats:

    def __init__(self, perf_ts, risk_free= 0, z_score = 1.96, folio_name=""):
        debug_info("BasicStats perf_ts : %s"%(str(perf_ts)))
        self.perf_ts = perf_ts
        self.z_score = z_score
        self.risk_free = risk_free
        freq = get_frequency(self.perf_ts)
        
        self.freq = "Day" if freq == "D" else freq
        self.ann_factor = ann_factor[self.freq[0]]
        self.sqrt_factor = self.ann_factor ** 0.55
        self.tsarr = self.perf_ts.values  # [perf["NetReturn"] for perf in perf_ts]
        self.tsarr_rf = [float(x) - risk_free / self.ann_factor for x in self.tsarr] if self.ann_factor else []
        self.perf_rf = Series(data=self.tsarr_rf, index=self.perf_ts.index)
        self.T = len(self.perf_ts)
        self.mean = np.mean(self.tsarr)
        self.std = np.std(self.tsarr)
        self.skew = stats.skew(self.tsarr)
        self.kurt = stats.kurtosis(self.tsarr)+3
        self.mdd_ser = BasicStats.under_water_series(self.perf_ts)
        
        self.maxdd = min(self.mdd_ser) if self.ann_factor else 0
        self.up_returns = [r for r in self.tsarr if r > 0]
        self.dn_returns = [r for r in self.tsarr if r < 0]
        self.T_UP = len(self.up_returns)
        
        self.T_DN = len(self.dn_returns)
        self.pct_up = self.T_UP / float(self.T)
        self.pct_dn = self.T_DN / float(self.T)
        self.avg_gain = np.mean(self.up_returns)
        self.avg_loss = np.mean(self.dn_returns)
        self.std_gain = np.std(self.up_returns)
        self.std_loss = np.std(self.dn_returns)
        self.vami = BasicStats.vami_arr(self.perf_ts)
        
        self.vami_rf = BasicStats.vami_arr(self.perf_rf)
        self.cum_return = self.vami[-1] -1
        self.cum_return_rf = self.vami_rf[-1] - 1
        self.ann_return = ((1+self.cum_return) **(self.ann_factor / self.T) - 1) #if self.T >=365 else self.cum_return / self.T * 365
        self.ann_return_rf = (1+self.cum_return_rf) **(self.ann_factor / self.T) - 1 #if self.T >=365 else self.cum_return_rf / self.T * 365
        self.ann_std = self.std * np.sqrt(self.ann_factor)
        self.std_rf = np.std(self.tsarr_rf)
        self.mean_rf = np.mean(self.tsarr_rf)
        self.sharpe = self.mean_rf * self.sqrt_factor / self.std_rf
        self.var = self.mean - self.z_score * self.std
        self.adj_z = adj_z_score(self.z_score, self.skew, self.kurt)
        self.var_adj = self.mean - self.adj_z * self.std
        self.cvar = cvar(self.tsarr)
        self.best = max(self.tsarr)
        
        self.worst = min(self.tsarr)
        self.down_dev = self.downside_deviation(self.tsarr_rf)
        self.sortino = self.ann_return_rf / (self.std_loss * self.sqrt_factor)
        self.sortino_adj = self.ann_return_rf / (self.down_dev * self.sqrt_factor)
        X = self.perf_ts[1:].values
        X_1 = self.perf_ts[:-1].values
        self.ser_df = DataFrame([X,X_1]).transpose()
        self.serr_corr = self.ser_df.corr().iloc[0,1]
        self.socre = self.sharpe * 5 + self.ann_return * 10 + self.sortino * 5 - self.maxdd * 5

    def downside_deviation(self,ts, mar = 0 ):
        res = sum([(t -mar)**2 for t in ts if t < mar])
        return (res / len(ts))**0.5
        
    def __repr__(self):
        return str(self.__dict__)

    def vami_arr(ts):
        cum = [1]
        vami = (ts+1).cumprod().values
        cum.extend(vami)
        return cum
        
    def under_water_series(ts):
        
        vami = BasicStats.vami_arr(ts)
        cummax = lambda arr, t: max(arr[:t+1])
        T = len(vami)
        maxvami = [vami[t] / cummax(vami,t) - 1for t in range(T)]
       
        return Series(data=maxvami[1:],index=ts.index)
