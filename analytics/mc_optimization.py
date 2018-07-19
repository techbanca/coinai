#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Monte Carlo based portfolio optimization
    Optimizain works by creating a bunch of portfolio with random weights for
    all Coins in the portfolio
    
    The more portfolios / trials are created the more accurate the results 
    would be. To improve performance we usually start on the page with just 100 trials

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from analytics.time_series import  get_frequency, freq_map
from numpy import random, zeros, mean, std

class ResampleTrial:
    def __init__(self, weights,series):
        self.weights = weights
        self.series = series
        self.mean = mean(series)
        self.std = std(series)
        self.freq = get_frequency(series)
        self.ann_factor = freq_map[self.freq]
        self.ann_return = self.mean * self.ann_factor
        self.ann_vol = self.std * (self.ann_factor ** 0.5)

class Resampler:
    def __init__(self,db, portfolio, n_trials,target_er):
        self.portfolio = portfolio
        self.N = len(self.portfolio.Allocations)
        self.n_trials = n_trials
        self.db = db
        
    def trial_weights(self):
        """
        generate random weights
        """
        total_w = 0
        weights = zeros(self.N)
        
        for i in range(self.N-1):
            w = random.random()*(1-total_w)
            total_w += w
            weights[i] = w
            
        weights[-1] = 1-total_w
        return weights   
            
    def calc_trial(self):
       """
       calculate single trial:
           use random weights to calcualte proforma time series
       """
       weights = self.trial_weights()
       proforma = self.portfolio.calc_proforma(self.db,weights,False)
       return ResampleTrial(weights, proforma)
        
    def run(self):
        self.portfolio.calc_proforma(self.db,[1/float(self.N) for _ in range(self.N)],True)
        self.trials = [self.calc_trial() for _ in range(self.n_trials)]
        
        for trial in self.trials:
            er = trial.mean
            vl = trial.std
            hr = [t for t in self.trials if t.mean > er and t.std <= vl]
            trial.is_efficient = len(hr) == 0

"""
    For testing: provide correct portid and user id
"""
if __name__ == '__main__':
    
    pass
