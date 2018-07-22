#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Peer Analysis Calculations

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import json

from datalib.datalib import Connection
from analytics.time_series import align_series
from analytics.basicstats import BasicStats
from analytics.regression_analysis import RegressionAnalysis
from analytics.regime_analysis import RegimeAnalysis

def capture_ex(fun):
    def wrapper(*args, **kwargs):
        try:
            return fun(*args,**kwargs)
        except Exception as ex:
            print(ex)
    return wrapper

# @capture_ex
class PeerStat:
    def __init__(self, folio_ts, peer, user_id=None, factors=None, Index=0, regime_model=None ):

        if user_id:
            peer_folio_ts = peer.folio_ts
        else:
            peer_folio_ts = peer.Performance
        common_data = align_series([folio_ts, peer_folio_ts])
        self.Name = peer.Name
        self.entire_return = peer.entire_history if user_id else 0
        self.HashKey = peer.folio_id if user_id else peer.coin_id
        self.corr = common_data.corr().iloc[0,1]
        self.peer_stats = BasicStats(peer_folio_ts)
        self.coin_stats = BasicStats(folio_ts)
        self.peer_ts = peer_folio_ts
        self.folio_ts = folio_ts
        self.index = Index
        if factors:
            self.factors = factors
            self.factor_ts = [f.Performance for f in self.factors]
            self.peer_style = RegressionAnalysis(self.peer_ts, self.factor_ts)
        else:
            self.coin_style = None
            self.peer_style = None
            
        if regime_model:
            self.regime_stats = RegimeAnalysis(peer, regime_model, peer, user_id)
        self.XY = common_data.values

class PeerAnalysis:
    
    def __init__(self, folio, userid=None, model_ticker=None,regime_model_name=None):

        self.db = Connection.getInstance()
        self.folio = folio
        self.Name = folio.Name
        self.user_id = userid
        self.model_ticker = model_ticker
        self.regime_model_name = regime_model_name

    async def analysis(self):
        if self.user_id:
            self.peer_coins = await self.db.get_portfolio_datas(self.user_id)
        else:
            self.peer_coins = await self.db.get_coins_datas()
        self.peer_coins = [f for f in self.peer_coins if 'Performance' in f.__dict__]
        self.peer_coins = [f for f in self.peer_coins if len(f.Performance) > 3]
        self.folio_ts = self.folio.folio_ts if self.user_id else self.folio.Performance
        self.entire_history = self.folio.entire_history if self.user_id else ""
        
        self.peer_coins.append(self.folio)
        # self.folio_stats = BasicStats(self.folio_ts)
        factors = None
        if self.model_ticker:
            model_info = await self.db.get_factor_model(self.model_ticker)
            tickers = json.loads(model_info.factors.decode())
            factors = await self.db.get_risk_factors(tickers)
        
        if self.regime_model_name:
            regime_model = await self.db.get_regime_model(self.regime_model_name)
        else:
            regime_model = None
        
        stat = lambda i,x: PeerStat(self.folio_ts, x, self.user_id, factors=factors,Index=i,regime_model=regime_model)
        N = len(self.peer_coins)
        if N >= 10:
            N = 11

        self.peer_stats = sorted([stat(i,peer) for i,peer in enumerate(self.peer_coins)],
                                 key=lambda x: x.index,
                                 reverse=True)[:N]
