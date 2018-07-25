
from decimal import Decimal
from coin_application.coins.models import Coin, Performance, PerformanceHour
from lib.utils import get_hotCoins, toRound
from settings import img_path

async def findCoinAllList(offset, limit):

    dataList = []
    coins = await Coin.findAll()
    coins = sorted(coins, key=lambda coin : float(coin.market_cap.replace(",","").replace("$","")), reverse=True)
    coins = coins[:702]
    hotCoins = get_hotCoins()
    for c in coins[int(offset):int(limit)+int(offset)]:
        item = {}
        item["coin_id"] = c.id
        item["coin_url"] = img_path + (c.website_slug.lower() + ".png" if c.website_slug else c.name.lower().replace(" ","-") + ".png")
        item["coin_name"] = c.name
        item["simple_name"] = c.simple_name
        item["market_cap"] = c.market_cap
        
        item["supply_pvolume"] = c.supply_pvolume
        item["trading_24_volume"] = c.trading_24_volume
        item["price"] = c.price
        item["hours_1_index"] = c.hours_1_index
        item["hours_24_index"] = c.hours_24_index
        item["day_7_index"] = c.day_7_index
        item["isHot"] = 1 if c.name in hotCoins else 0
        dataList.append(item)
    return dataList

async def findHotCoinList(all=0):

    dataList = []
    coins = await Coin.findAll()
    coins = sorted(coins, key=lambda coin: float(coin.market_cap.replace(",", "").replace("$", "")), reverse=True)
    coins = coins[:702]
    hotCoins = get_hotCoins()
    for c in coins:
        if not all and c.name not in hotCoins:
            continue
        item = {}
        if all:
            if c.simple_name.lower() == "usdt":
                continue
            item["coin_id"] = c.id
            item["coin_name"] = c.name
            item["simple_name"] = c.simple_name
        else:
            
            item["coin_id"] = c.id
            item["coin_url"] = img_path + (c.website_slug.lower() + ".png" if c.website_slug else c.name.lower().replace(" ","-") + ".png")
            item["coin_name"] = c.name
            item["simple_name"] = c.simple_name
            item["market_cap"] = c.market_cap
            item["supply_pvolume"] = c.supply_pvolume
            item["trading_24_volume"] = c.trading_24_volume
            item["price"] = c.price
            item["hours_1_index"] = c.hours_1_index
            item["hours_24_index"] = c.hours_24_index
            item["day_7_index"] = c.day_7_index
        dataList.append(item)
    return dataList


async def findCoin(pk=""):
    coin = await Coin.find(pk)
    return coin


async def findObjByName(name=""):

    coins = await Coin.findAll(where='name=? or simple_name=?', args=[name, name.upper()])
    if coins:
        coins = coins[0]
    return coins


async def findCoinNumber(where="", args=[]):
    count = await Coin.findNumber("count(id)", where=where, args=args)
    return count


async def findCoinDetail(pk=""):
    coin = await Coin.find(pk)
    item = {}
    if coin:
        item["coin_id"] = coin.id
        item["coin_url"] = img_path + (coin.website_slug.lower() + ".png" if coin.website_slug else coin.name.lower().replace(" ","-") + ".png")
        item["coin_name"] = coin.name
        item["simple_name"] = coin.simple_name
        item["market_cap"] = coin.market_cap
        item["supply_pvolume"] = coin.supply_pvolume
        item["trading_24_volume"] = coin.trading_24_volume
        item["price"] = coin.price
        item["hours_1_index"] = coin.hours_1_index
        item["hours_24_index"] = coin.hours_24_index
        item["day_7_index"] = coin.day_7_index
        item["price_btc"] = toRound(coin.price_btc,rate=7)
        item["price_rate"] = toRound(coin.price_rate,rate=3)
        item["price_btc_rate"] =  toRound(coin.price_btc_rate,rate=3)
        item["trading_24_btc_volume"] = toRound(coin.trading_24_btc_volume,rate=3)
    return item

async def findCoinByIds(coin_ids=[]):
    range_str = "("
    for _ in coin_ids:
        range_str += "?,"
    coins = await Coin.findAll(where='id in %s)'%range_str.rstrip(","), args=coin_ids)
    return coins

async def getCoinIds(allocations):
    coin_ids = []
    for allo in allocations:
        if allo["coin_id"]:
            coin_ids.append(allo["coin_id"])
        else:
            coin_obj = await findObjByName(allo["coin_name"])
            coin_id = coin_obj.id if coin_obj else ""
            coin_ids.append(coin_id)
    return coin_ids

async def findCoinByNames(coin_names=[]):
    range_str = "("
    dataList = []
    for _ in coin_names:
        range_str += "?,"
    coin_names = [name for name in coin_names]
    coin_names.extend(coin_names)
    coins = await Coin.findAll(where='name in %s) or simple_name in %s)'%(range_str.rstrip(","), range_str.rstrip(",")), args=coin_names)
    for c in coins:
        item = {}
        item["coin_name"] = c.name
        item["coin_id"] = c.id
        item["coin_url"] = img_path + (c.website_slug.lower() + ".png" if c.website_slug else c.name.lower().replace(" ","-") + ".png")
        item["simple_name"] = c.simple_name
        item["price"] = c.price
        item["price_btc"] = toRound(c.price_btc,rate=7)
        item["price_rate"] = c.price_rate.strip("%")
        item["hours_24_index"] = c.hours_24_index
        item["price_btc_rate"] = c.price_btc_rate.strip("%")
        item["trading_24_volume"] = c.trading_24_volume
        item["trading_24_btc_volume"] = c.trading_24_btc_volume
        dataList.append(item)
    return dataList

async def findCoinByName(name):

    dataList = []
    coins = await Coin.findAll(where='name=? or simple_name=?', args=[name,name.upper()])
    for c in coins:
        item = {}
        item["coin_name"] = c.name
        item["simple_name"] = c.simple_name
        item["coin_id"] = c.id
        item["coin_url"] = img_path + (c.website_slug.lower() + ".png" if c.website_slug else c.name.lower().replace(" ","-") + ".png")
        item["price"] = c.price
        item["hours_1_index"] = c.hours_1_index
        item["hours_24_index"] = c.hours_24_index
        item["market_cap"] = c.market_cap
        item["supply_pvolume"] = c.supply_pvolume
        item["trading_24_volume"] = c.trading_24_volume
        item["day_7_index"] = c.day_7_index
        dataList.append(item)
    return dataList

async def get_hour_24_coin_history(allocations=[]):

    hour_24_history = 0.0
    params = []
    sql_args = "("
    coin_dict = {}
    for data in allocations:
        coin_dict[data['coin_id']] = float(data['weight'])
        params.append(data['coin_id'])
        sql_args += "?,"

    coins = await Coin.findAll(where="id in %s)"%(sql_args.rstrip(",")), args=params)
    for coin in coins:
        weight = coin_dict.get(coin.id, "")
        hours_24_index = float(coin.hours_24_index.split("%")[0]) * float(weight)
        hour_24_history += hours_24_index

    return hour_24_history


async def findPerformance(coin_id, start_time=None, end_time=None):

    dataList = []
    if start_time:
        if end_time:
            performances = await Performance.findAll(where='coin_id=? and effective_date>=? and effective_date<?',
                                                     args=[coin_id, start_time, end_time])
        else:
            performances = await Performance.findAll(where='coin_id=? and effective_date>=?',
                                                      args=[coin_id, start_time])
    else:
        performances = await Performance.findAll(where='coin_id=?', args=[coin_id,])
    for per in performances:
        item = {}
        item["NetReturn"] = Decimal(per.net_return)
        item["EffectiveDate"] = per.effective_date
        dataList.append(item)
    return dataList


async def findPerformanceHour(coin_id, start_time=None, end_time=None):

    dataList = []
    if start_time:
        if end_time:
            performances_hour = await PerformanceHour.findAll(where='coin_id=? and effective_date>=? and effective_date<=?',
                                                     args=[coin_id, start_time, end_time])
        else:
            performances_hour = await PerformanceHour.findAll(where='coin_id=? and effective_date>=?',
                                                      args=[coin_id, start_time])
    else:
        performances_hour = await PerformanceHour.findAll(where='coin_id=?', args=[coin_id,])
    for per in performances_hour:
        item = {}
        item["NetReturn"] = Decimal(per.net_return)
        item["EffectiveDate"] = per.effective_date
        dataList.append(item)
    return dataList
