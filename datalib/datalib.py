# -*- coding: utf-8 -*-
"""
    
    Main class for accessing data in Amazon DynamoDB tables

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

import boto3, json, os
from boto3.dynamodb.conditions import Key
from analytics.time_series import get_frequency
from hashlib import sha1
from decimal import Decimal

#For Testing purposes
from conf import dynamodb_config

if __name__ == '__main__':
    from coin import Coin
    from user import User  
    from regime_model import RegimeModel
    from portfolio import Portfolio
else:  
    from datalib.coin import Coin
    from datalib.user import User
    from datalib.regime_model import RegimeModel
    from datalib.portfolio import Portfolio

s2hex = lambda s: sha1(s.encode("utf-8")).hexdigest()
current_path = os.path.realpath(__file__)
conf_path = current_path.split("datalib")[0] + "conf/"

sort_by_name = lambda f: f.Name

def getdb():
    """
        returns connection to dynamo db
        Normally boto3.resource("dynamodb") is the right way of doing this.
        However, if aws cli is not configured properlly then actual account 
        information can be supplied (not ideal)
    """
    conf = dynamodb_config.dynamoDB
    region = conf["region"]
    url="https://dynamodb.%s.amazonaws.com.cn" % region
    dynamodb = boto3.resource('dynamodb',
                                aws_access_key_id=conf["aws_access_key_id"],
                                aws_secret_access_key=conf["aws_secret_access_key"],
                              region_name=region,
                              endpoint_url=url)
    return dynamodb
    
def ts_to_db_map( ts):
    T = len(ts)  
    row = lambda i: {"EffectiveDate": int(ts.index[i].timestamp()),
                    "NetReturn": Decimal(str(ts[i]))}
    return [row(i) for i in range(T)]


class Allocation:
    def __init__(self, data):
        self.HashKey = data['HashKey']
        self.Name = data['Name']
        self.Weight = data['Allocation']


class Connection:
    """
        main class for getting data in/out of dyanamodb
    """
    def __init__(self):
        self.db = getdb()
    
    
    def get_table(self,table_name):
        return self.db.Table(name=table_name)

    def get_user_by_id(self,userid):
        key = {'UserID':userid}  
        users = self.get_table('Users')
        resp = users.get_item(Key=key)
        if 'Item' in resp:
            item = resp['Item'] 
            return User(item)
        return None

    def get_users(self):
        table = self.get_table("Users")
        user_res = table.scan()
        if "Items" in user_res:
            return [User(item) for item in user_res["Items"]]
        return []
                    
    def get_user(self,email):
        return self.get_user_by_id(s2hex(email))
    
    def checkLogin(self,email, password):        
        user = self.get_user(email)
        if user:
            user.authenticate( s2hex(password))
            return user
        return None
        
    def get_coin(self,hashkey,get_ts=True):
        table = self.get_table("Coin")
        res = table.get_item(Key={
            'HashKey':hashkey
        })
        
        if 'Item' in res:
            if get_ts:
                self.update_perf_item(res['Item'])
            return Coin(Data=res['Item'])
        return None

    def get_all_coins(self):
        table = self.get_table("Coin")
        res = table.scan()
        coins = [Coin(Data=item) for item in res['Items']]
        return coins
        
    def update_perf_item(self,item):

        if 'HashKey' in item:
            item['Performance'] = self.get_performance(item['HashKey'])
            
      
    
    def get_coin_by_name(self, *, owner, name, get_ts = False):
         
        table = self.get_table("Coin")
        qvals = {"#Coinname":name}
        qvals[':owner'] = owner
        
        proj = "HashKey, #CoinName, T, MaxDate, MinDate, Frequency, StrategyCode"
        # since Coin data is stored with Coin table the projection is used to
        # determine if the performance data need to be retrieved
        if get_ts:
            proj = proj + ',Performance'
        
        res = table.query(IndexName="OwnerID-Name-index",
                          KeyConditionExpression=Key('OwnerID').eq(owner) & Key("Name").eq(name), 
                          ExpressionAttributeNames={"#CoinName":"Name"},
                          ProjectionExpression=proj)
      
        if res['Count'] > 0:
            if get_ts:
                for item in res['Items']:
                    self.update_perf_item(item)

            return [Coin(OwnerId=owner,Data=f) for f in res['Items']]
        return []
        
    def get_performance(self, hashkey):
        table = self.get_table("PerformanceData")
        res = table.get_item(Key={"HashKey":hashkey})
        if 'Item' in res:
            return res['Item']['Performance']
        return []

    def get_perf_items(self,hashkey,ts):
        perf_point = lambda d,p: {
                                  'EffectiveDate':int(d.timestamp()),
                                  'NetReturn':Decimal(str(p))}
        dates = ts.index
        rets = ts.values
        return [perf_point(d,p) for d,p in zip(dates, rets)]
                
    def save_performance(self, hashkey, ts):

        perf_points = self.get_perf_items(hashkey,ts)
        perf_table = self.get_table("PerformanceData")
        item = {'HashKey':hashkey,'Performance':perf_points}
        perf_table.put_item(Item=item)
        
    def delete_performance(self, hashkey):
        perf = self.get_performance(hashkey)
        perf_table = self.get_table("Performance")
        with perf_table.batch_writer() as batch:
            for p in perf: 
                batch.delete_item(Key={'EffectiveDate':p['EffectiveDate'],
                                        'HashKey':hashkey})
        return True

    def get_coins(self, *, owner, coinids, get_ts = False):
         
        query = "OwnerID=:owner"
        table = self.get_table("Coin")

        N = len(coinids)
        vallist = [':hashkey_%s' %i for i in range(N)]
        filterexp = 'HashKey in (' + ','.join(vallist)  + ')'     
        
        qvals = dict([(':hashkey_%s' % i , coinids[i]) for i in range(N)])
        qvals[':owner'] = owner
    
        proj = "HashKey, #CoinName, T, MaxDate, MinDate, Frequency, StrategyCode"
        if get_ts:
            proj = proj + ',Performance'
        res = table.query(IndexName="OwnerID-index",
                          FilterExpression = filterexp,
                          KeyConditionExpression=query,
                          ExpressionAttributeValues=qvals, 
                          ExpressionAttributeNames={"#CoinName":"Name"},
                          ProjectionExpression=proj)
        if res['Count'] > 0:
            if get_ts:
                for item in res['Items']:
                    self.update_perf_item(item)
            return [Coin(OwnerId=owner,Data=f) for f in res['Items']]
        return []

    def get_risk_factors(self, tickers, get_ts = True):
        return [self.get_risk_factor(t,get_ts=get_ts) for t in tickers]

    def list_risk_factors(self):
        table = self.get_table("RiskFactor")
        proj = "Ticker,#FactorName,T,FactorType,MaxDate"
        res= table.scan(ProjectionExpression=proj, 
                        ExpressionAttributeNames={"#FactorName":"Name"})
        if 'Items' in res:
            return [Coin(OwnerId='Coin-AI',Data=item) for item in res['Items']]
        return []

    def get_coins_by_owner(self, *, owner, name = None):
        query = "OwnerID=:owner"
        query_vals = {":owner":owner}
        table = self.get_table("Coin")
        if name:
            filters = "contains (lowername,:Coinname)"
            query_vals[":Coinname"] = name.lower()
        else:
            filters = None

        proj = "HashKey, #CoinName, T, MaxDate, MinDate, Frequency, StrategyCode"
        if filters:
            res = table.query(IndexName="OwnerID-index",
                              FilterExpression = filters,
                              KeyConditionExpression=query,
                              ExpressionAttributeValues=query_vals, 
                              ExpressionAttributeNames={"#CoinName":"Name"},
                              ProjectionExpression=proj)
        else:
           res = table.query(IndexName="OwnerID-index",
                             KeyConditionExpression=query,
                             ExpressionAttributeValues=query_vals, 
                             ExpressionAttributeNames={"#CoinName":"Name"},
                             ProjectionExpression=proj)
      
        if res['Count'] > 0:
            return sorted([Coin(OwnerId=owner,Data=f) for f in res['Items']],
                           key=sort_by_name)
        return []

        
    def get_watched_coins(self, owner, get_ts = False):
        query = "OwnerID=:owner"
        query_vals = {":owner":owner}
        table = self.get_table("Coin")
        proj =  "HashKey, #CoinName, MaxDate, IsPortfolio"
        res = table.query(IndexName="IsWatchList-index",
                          KeyConditionExpression=Key('IsWatchList').eq(1),
                          FilterExpression=query, 
                          ExpressionAttributeValues=query_vals, 
                          ExpressionAttributeNames={"#CoinName":"Name"},
                          ProjectionExpression=proj)
        
        if res['Count'] > 0:
            if get_ts:
                for item in res['Items']:
                    self.update_perf_item(item)

            return sorted([Coin(OwnerId=owner,Data=f) for f in res['Items']],
                           key=sort_by_name)
        return []

    def get_risk_factor(self,ticker, get_ts = True):
        table = self.get_table("RiskFactor")
        res =table.get_item(Key={"Ticker":ticker}, 
                                ExpressionAttributeNames={"#FactorName":"Name"},
                                ProjectionExpression="Ticker,#FactorName,FactorType,T,HashKey")
        if 'Item' in res:        
            item = res['Item']
            self.update_perf_item(item)
            return Coin(OwnerId='risk-ai',Data=item)
        return None
        
    def get_factor_model(self,code):
        table = self.get_table("FactorModel")
        res = table.get_item(Key={"Code":code})
        if 'Item' in res:
            return res['Item']
    
    def get_factor_models(self):
        table = self.get_table("FactorModel")
        res = table.scan()
        if 'Items' in res:
            return res['Items']
        return []
        
        
    def get_regime_model(self, model_name):
        table = self.get_table("RegimeModel")
        res = table.get_item(Key={"ModelName":model_name})
        if 'Item' in res:
            item = res['Item']
            return RegimeModel(item)
        
    def get_regime_model_list(self):
        table = self.get_table("RegimeModel")
        res = table.scan(ProjectionExpression="ModelName,FactorModel,NRegimes")
        if 'Items' in res:
            return res['Items']
        return []

    def update_coin(self, coinid, field, value):
        updates = {field:{"Value":value, "Action":"PUT"}}
        key = {"HashKey": coinid}
        table = self.get_table("Coin")
        table.update_item(Key=key, AttributeUpdates=updates)
           
    def update_user(self, userid, field, value):
        updates = {field:{"Value":value, "Action":"PUT"}}
        key = {"UserID": userid}
        table = self.get_table("Users")
        table.update_item(Key=key, AttributeUpdates=updates)

    def get_coins_by_Frequency_Points(self, freq, T,MaxDate = None):
        table = self.get_table("Coin")
        idx_name = "idx_Freq_Time"
        
        query_vals = {":freq":freq, 
                      ":t":int(T),
                      ":maxdate": int(MaxDate.timestamp()) if MaxDate else 0
                      }
  
        proj =  "HashKey, #CoinName, T, MaxDate, MinDate,OwnerID,StrategyCode"
        res = table.query(IndexName=idx_name,
                          KeyConditionExpression="Frequency=:freq and T>=:t",
                          FilterExpression="MaxDate >= :maxdate  ", 
                          ExpressionAttributeValues=query_vals, 
                          ExpressionAttributeNames={"#CoinName":"Name"},
                          ProjectionExpression=proj)
        return [Coin(Data=item) for item in res['Items']]
        
    def get_portfolio(self,userid, hashkey,*,get_coins=False,
                      get_coin_ts=False,recalc=False):
        
        table = self.get_table("Portfolio")
        res = table.get_item(Key={"CompanyID":userid, "HashKey":hashkey})
        if 'Item' in res:
            port = Portfolio(res['Item'])
            port.W = sum([float(a['Allocation']) for a in port.Allocations])

            if get_coins:
                hashkeys = [a['HashKey'] for a in port.Allocations]
                if hashkeys:
                    coins = self.get_coins(owner=userid,coinids = hashkeys)
                    coin_hash = dict([(f.HashKey,f) for f in coins])
       
                    for a in port.Allocations:
                        coinid = a['HashKey']
                        if coinid in coin_hash:
                            a['Coin'] = coin_hash[coinid]
            return port
           
        return None
        
    def get_ref_data(self, code):
        table = self.get_table("ReferenceData")
        res = table.get_item(Key={"Code":code})
        if 'Item' in res:
            return res['Item']
        return []
        
    def get_user_portfolios(self, userid):
        table = self.get_table("Portfolio")
        query_vals = {":userid":userid}
        keyexp = "CompanyID=:userid"
        proj = "HashKey, #PortName, UserID, CompanyID"
        res = table.query(KeyConditionExpression=keyexp,
                          ExpressionAttributeValues=query_vals,
                          ExpressionAttributeNames={"#PortName":"Name"},
                          ProjectionExpression=proj)
        if 'Items' in res:
            return [Portfolio(item) for item in res['Items']]
        return []
                

    def get_portfolio_coin(self, portfolio):
        owner = portfolio.CompanyID
        hashkey = portfolio.HashKey
        coin = self.get_coin(hashkey)
        if coin == None:
            coin = Coin(OwnerId =owner)
            coin.HashKey = hashkey
            self.get_table("Coin").put_item(Item=coin.to_db_item())
        return coin

    
    def update_portfolio_coin(self, portfolio):

        coin = self.get_portfolio_coin(portfolio)
        coin.Name = portfolio.Name
        coin.StrategyCode = 'Portfolio'
        coin.lowername = portfolio.Name.lower()
        prof = portfolio.calc_proforma(self)

        coin.Performance = prof
        coin.T = len(prof)
        coin.MaxDate = int(prof.index[-1].timestamp())
        coin.Frequency = get_frequency(prof)
        self.get_table("Coin").put_item(Item=coin.to_db_item())
        return coin
        
        
    def recalculate_portfolio_coin(self,portfolio_id, user_id, db = None):
            
        port = self.get_portfolio(user_id, portfolio_id)
        proforma_ts = port.calc_proforma(db)
    
        coin = self.get_coin(portfolio_id)
        if not coin:
            data = {'HashKey':portfolio_id,
                    'Name':port.Name,
                    'IsPortfolio':1,
                    'OwnerID' : user_id}
            coin = Coin(owner=user_id,Data=data)
        coin.ManagementFee = 0
        coin.PerformanceFee = 0
        coin.CurrencyCode = 'USD'
        coin.CoinCAP = 0
        coin.Name = port.Name
        coin.HurdleRate = 0
        coin.lowername = port.Name.lower()
        coin.ManagerName = 'Banca'
        coin.MinInvestment = 0
        coin.RedemptionFrequency = 0
        coin.StrategyCode = 'Coin of Coins'
        coin.T = len(proforma_ts)
       
        coin_table = db.get_table("Coin")
        coin_table.put_item(Item=coin.to_db_item())
        self.save_performance(portfolio_id, proforma_ts)
        return coin, proforma_ts
