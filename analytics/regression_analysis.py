   #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Regression Analysis

    Functions used for style / regression analysis

    Developed by Coin-AI, 2017-2018
    Contact: banca

"""

import statsmodels.api as sm
from numpy import cov, var, matmul, cumsum

from analytics.time_series import align_series
from lib.utils import toDecimal


def SimpleReg(y,x,has_const = False):
    common_data = align_series([y,x])
    y = common_data.iloc[:,0]
    x = common_data.iloc[:,1]

    if has_const:
        x = sm.add_constant(x)
    model = sm.OLS(y,x)
    res = model.fit()
    return list(res.params.values)
    

class RegressionAnalysis:
    
    def __init__(self, y, x):
        self.ts_y = y
        
        if type(x) is list:
            self.ts_x = x
        else:
            self.ts_x = [x]
        self.all_series = self.ts_x.copy()
        self.all_series.insert(0, self.ts_y)
        self.common_data = align_series(self.all_series)
        self.columns = self.common_data.columns
        self.Y = self.common_data[self.columns[0]].values
        self.X = self.common_data[self.columns[1:]].values
        self.X = sm.add_constant(self.X)
        self.model = sm.OLS(self.Y, self.X)
        self.reg_results = self.model.fit()
        betas = list(self.reg_results.params)[1:]
        self.betas = [toDecimal(b) for b in betas]
        self.pvalues =  self.reg_results.pvalues[1:]
        self.alpha = self.reg_results.params[0]
        self.rsq_adj = self.reg_results.rsquared_adj
        self.rsq = self.reg_results.rsquared
        self.coin_vol = var(self.Y)
        if len(self.ts_x) > 1:
            self.factor_cov = cov(self.X[:,1:], rowvar=False)
            betas = [float(betas) for betas in self.betas]
            self.fcmtr = matmul(self.factor_cov, betas)
            self.crisk =  [ b * v / self.coin_vol for (b,v) in zip(betas, self.fcmtr)]
        else:
            self.factor_cov = [cov(self.X[:,1])]
            self.crisk = [self.rsq]
        self.crisk.append(1- sum(self.crisk))
        self.crisk_cum = cumsum(self.crisk)
        
        
if __name__ == '__main__':
    pass