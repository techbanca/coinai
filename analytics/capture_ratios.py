#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Capture Ratios analytics

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from analytics.time_series import logreturns, align_series

import statsmodels.api as sm 

class CaptureRatios:
    
    def calc_capture(self,ts1,ts2,idx):
        r1 = logreturns(ts1[idx])
        r2 = logreturns(ts2[idx])
        return r1/r2
    
    def calc_beta(self,ts_y, ts_x, idx):
        
        x = ts_x[idx]
        x = sm.add_constant(x)
        model = sm.OLS(ts_y[idx],x,hasconst=True)
        fit = model.fit()
        return fit.params

    def __init__(self, ts, bench_ts):
        """
            Constructor accepts to Series objects (for Coin and benchmark)
        """       
        self.common_df = align_series([ts,bench_ts])
        self.data = self.common_df.values
        self.bench_data = self.data[:,1]
        self.coin_data = self.data[:,0]
        self.idx_bench_up = self.bench_data > 0
        self.idx_bench_dn = self.bench_data < 0
        self.T = len(self.bench_data)
        
        self.T_Up = len([i for i in self.idx_bench_up if i ])
        self.T_Dn = len([i for i in self.idx_bench_dn if i ])
        
        self.coin_bench = self.coin_data - self.bench_data
        self.coin_bench_up = self.coin_bench[self.idx_bench_up]
        self.coin_bench_dn = self.coin_bench[self.idx_bench_dn]

        reg_up = self.calc_beta(self.coin_data, self.bench_data, self.idx_bench_up)
        reg_dn = self.calc_beta(self.coin_data, self.bench_data, self.idx_bench_dn)
        
        
        self.alpha_up = reg_up[0]
        self.alpha_dn = reg_dn[0]
        self.beta_up = reg_up[1]
        self.beta_dn = reg_dn[1]
        
        if self.T_Up > 0:
            self.up_capture = self.calc_capture(self.coin_data, self.bench_data, self.idx_bench_up)
            self.T_Up_outperf = len([f for f in self.coin_bench_up if f > 0])
            self.up_outperf =  self.T_Up_outperf / self.T_Up
            self.perf_bench_up = self.coin_bench_up.mean()
            self.bench_up = self.bench_data[self.idx_bench_up].mean()
        else:
            self.up_outperf = 0
        
        if self.T_Dn > 0:
            self.dn_capture = self.calc_capture(self.coin_data, self.bench_data, self.idx_bench_dn)
            self.T_Dn_outperf = len([f for f in self.coin_bench_dn if f > 0])
            self.dn_outperf = self.T_Dn_outperf / self.T_Dn
            self.perf_bench_dn = self.coin_bench_dn.mean()
            self.bench_dn = self.bench_data[self.idx_bench_dn].mean()
        else:
            self.dn_outperf = 0

    def __repr__(self):
        return str(self.__dict__)
