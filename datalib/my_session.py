#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Used to store and retrieve session data from DynamodDB
    
    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

from datalib.datalib import Connection  
    
res_ok = lambda x : 'Item' in x
def_sess = lambda x: {'HashKey': x}
def get_session(sessionid):
    db = Connection()
    table = db.get_table("Session")
    res = table.get_item(Key={"HashKey":sessionid})
    
    return res['Item'] if res_ok(res) else def_sess(sessionid)

def save_session(session):
    
    db = Connection()
    table = db.get_table("Session")
    table.put_item(Item=session)
    


       
