#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Risk / Return Attribution
    Calculates each Coin's contribution to portfolio return, volatility and marginal var


    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from analytics.regression_analysis import SimpleReg 
from numpy import std,mean

class PortfolioAttribution:
    
    def __init__(self, *, portfolio, db):
        """
            Create portfolio attribution with given portfolio
        """
        self.db = db
        self.allocs = portfolio.Allocations
        self.portfolio = portfolio
        self.proforma = portfolio.calc_proforma(db)
        self.coins = portfolio.coins
        self.coins_ts = [f.Performance for f in self.coins]
        self.weights = [float(a['Allocation']) for a in self.allocs]
        
        self.regs = [SimpleReg(fts,self.proforma)[0] for fts in self.coins_ts]
        self.tot_beta = sum([b * w for b,w in zip(self.regs, self.weights)])
        #contribition to risk
        self.crisk = [b * w / self.tot_beta for b,w in zip(self.regs, self.weights)]
        self.port_mean, self.port_std, self.port_var = self.calc_port_stats(self.proforma)
        #marginal var
        self.marginal_vars = [self.marginal_var(i) for i in range(len(self.coins))]
        #return contributions
        self.coin_returns = [mean(ts) for ts in self.coins_ts]
        self.coin_ret_contrib = [r * w   for r,w in zip(self.coin_returns, self.weights)]
        self.port_er = sum(self.coin_ret_contrib)
        self.c_ret = [r / self.port_er for r in self.coin_ret_contrib]
        self.N = len(self.coins)
             
    def calc_port_stats(self, ts):
        port_mean = mean(ts)
        port_std = std(ts)
        port_var = port_mean - 1.96 * port_std        
        return port_mean, port_std, port_var
    
    def marginal_var(self, pos_index):
        """
            returns difference bwteen the value at risk(0.95 ci) for current 
            portfolio vs portfolio where the position is removed and Coins reallocated
            proportionatly to other Coins.
            
            So if we have two Coins with equal allocation
            When we remove the first Coin the weights become [0, 1]
            When we remove second Coin the weights become [1,0]
            
            Positive Marginal Var means that removing the position would decrease the risk of the portfolio
            Negaive marginal VaR means that position serves as diversifier and reduces the portfolio risk
        """
        w0 = self.weights[pos_index]
        totw = sum(self.weights)
        new_totw = totw - w0
        mult =  totw / new_totw
        newweights = [w*mult for w in self.weights]
        newweights[pos_index] = 0
        newprof = self.portfolio.calc_proforma(self.db, new_weights = newweights)
        res = self.calc_port_stats(newprof)
        return self.port_var - res[2]