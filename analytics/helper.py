#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Helper for labeling / formatting basic stats

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

default_filename= "./helper_dict.json"

class FieldInfo:
    def __init__(self, key, lbl, fmt):
        self.key = key
        self.label = lbl
        self.fmt_str = fmt
        self.format = lambda v: self.fmt_str.format(v)

default_dict = {
    "Fields": [
    {"Key":"T", "Label":"Number of Periods"},
    {"Key":"freq", "Label":"Frequency"},
    {"Key":"mean", "Label":"Average Return", "Format":"{:.2%}"},
    {"Key":"std", "Label":"Period Volatility", "Format":"{:.2%}"},
    {"Key":"ann_return", "Label":"Annualized Return", "Format":"{:.2%}"},
    {"Key":"ann_std", "Label":"Annualized Volatility","Format":"{0:.2%}"},
    {"Key":"cum_return", "Label":"Cumulative Return", "Format":"{0:.2%}"},
    {"Key":"best", "Label":"Best Return","Format":"{0:.2%}"}, 
    {"Key":"worst", "Label":"Worst Period","Format":"{0:.2%}"},
    {"Key":"skew", "Label":"Skewness", "Format":"{:0.2f}"},
    {"Key":"kurt", "Label":"Kurtosis","Format":"{:0.2f}"},
    {"Key":"pct_up", "Label":"Percent Gains","Format":"{:.2%}"},
    {"Key":"pct_dn", "Label":"% Losses", "Format":"{:.2%}"},
    {"Key":"avg_gain", "Label":"Average Gain ", "Format":"{:.2%}"},
    {"Key":"std_gain", "Label":"Gain volatility", "Format":"{:.2%}"},
    {"Key":"down_dev", "Label":"Downside Deviation", "Format":"{:.2%}"},
    {"Key":"avg_loss", "Label":"Average Loss", "Format":"{:.2%}"},
    {"Key":"std_loss", "Label":"Loss Std", "Format":"{:.2%}"},  
    {"Key":"maxdd", "Label":"Max Drawdown", "Format":"{:.2%}"},
    {"Key":"var", "Label":"Value At Risk (Normal)", "Format":"{:.2%}"},
    {"Key":"var_adj", "Label":"VaR Adj", "Format":"{:.2%}"},
    {"Key":"risk_free", "Label":"Risk Free Rate", "Format":"{:.2%}"},
    {"Key":"sharpe", "Label":"Sharpe Ratio", "Format":"{:.2f}"},
    {"Key":"sortino", "Label":"Sortino ", "Format":"{:.2f}"},
    {"Key":"sortino_adj", "Label":"Sortino Adj","Format":"{:.2f}"},
    {"Key":"T_UP", "Label":"Number Up"},
    {"Key":"T_DN", "Label":"Number Down"}
    ]
}
    
class StatsHelper:
    def __init__(self, filename = None):
       
        json_data = default_dict 
        self.help_dict = {}
        self.field_list = []
        fields = json_data['Fields']
        
        for field_info in fields:
            field_name = field_info['Key']
            field_label = field_info['Label']
            if 'Format' in field_info:
                fmt = field_info['Format']
            else:
                fmt = "{0}"
           
            field = FieldInfo(field_name, field_label, fmt)
            self.field_list.append(field_name)
            self.help_dict[field_name] = field
    
    def help(self,obj):
        obj_dict = obj.__dict__
        fields = [self.help_dict[f] for f in self.field_list if f in obj_dict]
        return [(f.label, f.format(obj_dict[f.key])) for f in fields]

            
if __name__ == '__main__':
    
    helper = StatsHelper()
    
    from analytics.basicstats import BasicStats
    from datalib.datalib import Connection 
    
    coinid = 'e042001c-9a43-11e6-bfb2-14109fdf0df7'
    db = Connection()
    coin = db.get_coin(coinid)
    stats = BasicStats(coin.Performance)
    res = helper.help(stats)
    
    
