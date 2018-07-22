#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Risk / Return Attribution
    Calculates each Coin's contribution to portfolio return, volatility and marginal var

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import json

from numpy import std,mean
from analytics.regression_analysis import SimpleReg
from lib.utils import toDecimal


class PortfolioAttribution:
    
    def __init__(self, *, portfolio, db):
        """
            Create portfolio attribution with given portfolio
        """
        self.db = db
        self.allocs = json.loads(portfolio.Allocations.decode()) if not isinstance(portfolio.Allocations, list) else portfolio.Allocations
        self.portfolio = portfolio
        self.start_time = portfolio.modify_at if portfolio else ""


    async def analysis(self):

        self.proforma = await self.portfolio.calc_proforma(self.db, self.start_time, folioPerformance=False)
        self.coins = self.portfolio.coins
        self.coins_ts = [f.Performance for f in self.coins]
        self.weights = [float(a['weight']) for a in self.allocs]
        
        self.regs = [SimpleReg(fts,self.proforma)[0] for fts in self.coins_ts]
        self.tot_beta = sum([b * w for b,w in zip(self.regs, self.weights)])
        #contribition to risk
        crisks = [b * w / self.tot_beta for b,w in zip(self.regs, self.weights)]
        self.crisk = [toDecimal(crisk) for crisk in crisks]
        
        self.port_mean, self.port_std, self.port_var = self.calc_port_stats(self.proforma)
        #marginal var
        self.marginal_vars = []
        for i in range(len(self.coins)):
            var = await self.marginal_var(i)
            self.marginal_vars.append(toDecimal(var))
        #return contributions
        self.coin_returns = [mean(ts) for ts in self.coins_ts]
        
        self.coin_ret_contrib = [r * w   for r,w in zip(self.coin_returns, self.weights)]
        self.port_er = sum(self.coin_ret_contrib)
        c_rets = [r / self.port_er for r in self.coin_ret_contrib]
        self.c_ret = [toDecimal(ret) for ret in c_rets]
        self.N = len(self.coins)
             
    def calc_port_stats(self, ts):
        
        port_mean = mean(ts)
        port_std = std(ts)
        port_var = port_mean - 1.96 * port_std        
        return port_mean, port_std, port_var


    async def marginal_var(self, pos_index):
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
        mult = (totw / new_totw) if new_totw else 1
        newweights = [w*mult for w in self.weights]
        newweights[pos_index] = 0
        newprof = await self.portfolio.calc_proforma(self.db, self.start_time, new_weights = newweights, folioPerformance=False)
        res = self.calc_port_stats(newprof)
        return self.port_var - res[2]
