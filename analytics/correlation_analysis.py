    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Simple correlation analysis enhanced by adding correlation in up/down markets

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from analytics.time_series import align_series

class CorrelationAnalysis:
    
    def __init__(self, ts, bench_ts):
        self.ts = ts
        self.bench_ts = bench_ts
        self.common_data = align_series([self.ts, self.bench_ts])
        self.columns = self.common_data.columns
        
        self.idx_up = self.common_data[self.columns[1]] > 0
        self.idx_dn = self.common_data[self.columns[1]] < 0
       
        self.data_up = self.common_data[self.idx_up]
        self.data_dn = self.common_data[self.idx_dn]
        self.XY = self.common_data.values
        self.T = len(self.common_data)
        if len(self.common_data) >= 6:
            self.corr = self.common_data.corr().iloc[1,0]

        if len(self.data_up) >= 5:
            self.corr_up = self.data_up.corr().iloc[1,0]
        
        if len(self.data_dn) >= 5:
            self.corr_dn = self.data_dn.corr().iloc[1,0]
