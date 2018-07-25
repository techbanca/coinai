
import datetime
import json
import time, copy

from coin_application.reports.coinReport import portfolio_ratios
from datalib.portfolio import Portfolio as port_folio
from coin_application.portfolios.models import Portfolio, FolioPerformance
from coin_application.coins import dao as coin_dao
from coin_application.users import dao as user_dao
from datalib.datalib import Connection
from lib.utils import toPreTimestamp, getPerformanceList


async def calculate_weight(allocations=[]):

    init_assets = 0
    weight_dict = {}
    coin_ids = await coin_dao.getCoinIds(allocations)
    coins = await coin_dao.findCoinByIds(coin_ids)
    coin_dict = {}
    for obj in coins:
        obj = obj.json()
        coin_dict[obj["simple_name"].lower()] = obj
        coin_dict[obj["name"].lower()] = obj
    for allo in allocations:
        price = coin_dict.get(allo["coin_name"].lower(),{}).get("price","")
        price = float(price.split("$")[-1]) if price else 0.0
        if "price" in allo:
            pre_price = float(allo["price"].split("$")[-1])
        else:
            pre_price = price
            allo["price"] = price

        if "number" not in allo:
            weight = allo["weight"]
            number = round(float(1000000 * weight / float(price)), 3)
            allo["number"] = number
        else:
            number = allo["number"]

        rate = float(price / pre_price - 1)
        allo["rate"] = float(round(rate, 4))
        coin_assets = number * price
        
        init_assets += float(coin_assets)
        weight_dict[allo["coin_name"]] = coin_assets

    for allo in allocations:
        allo["weight"] = float(round(weight_dict[allo["coin_name"]]/init_assets, 4))

    return allocations, float(round(init_assets, 3))


async def calculate_portfolio(folio_id, folio=None, re_cal=False, is_modify=False, is_create=False,
                              folio_name="", new_allocations=[], modify_at=None, is_ratio=True, to_roi_rate=False):

    if not folio:
        folio = await Portfolio.find(folio_id)

    if not folio:
        return None

    if is_modify:
        allocations = new_allocations
    else:
        allocations = json.loads(folio.allocations) if isinstance(folio.allocations, str) else json.loads(folio.allocations.decode())

    if not is_create:
        init_assets = 0
        coin_ids = await coin_dao.getCoinIds(allocations)
        coins = await coin_dao.findCoinByIds(coin_ids)
        coin_dict = {}
        for obj in coins:
            obj = obj.json()
            coin_dict[obj["simple_name"].lower()] = obj
            coin_dict[obj["name"].lower()] = obj
        for allo in allocations:
            price = coin_dict.get(allo["coin_name"].lower(), {}).get("price", "")
            if not price:
                continue
            price = float(price.split("$")[-1]) if price else 0.0
            if "price" in allo:
                pre_price = float(allo["price"].split("$")[-1])
            else:
                pre_price = price
                allo["price"] = price

            if "number" not in allo:
                weight = allo["weight"]
                number = round(float(1000000 * weight / float(price)), 3)
                
                allo["number"] = number
            else:
                number = allo["number"]
            rate = float(price/pre_price - 1)
            allo["rate"] = float(round(rate, 4))
            coin_assets = number * price
            init_assets += float(coin_assets)
    else:
        init_assets = 1000000

    performance = {}
    init_assets = float(round(init_assets, 3))
    roi = float(round(float(init_assets / 1000000), 4))
    timestamp = modify_at if modify_at else int(time.time())
    user_id = folio.user_id

    if re_cal or is_create:
        styleTime = datetime.datetime.utcfromtimestamp(int(time.time()))
        pre_date = str(styleTime).split(" ")[0]
        if folio.pre_roi:
            pre_roi = folio.pre_roi
        else:
            pre_roi = 1.0
        roi_rate = float(round(float((roi - pre_roi) / pre_roi), 5))
        if to_roi_rate:
            return roi_rate

        effective_date = pre_date + " 00:00:00"
        effective_time = time.mktime(time.strptime(effective_date, '%Y-%m-%d %H:%M:%S'))
        performance = {int(effective_time): roi_rate}
        if folio.pre_date != pre_date or is_create:
            folio.pre_roi = roi
            folio.pre_date = pre_date
        try:
            if re_cal:
                await updateFolioPerformance(folio_id, user_id, proforma=performance, modify_at=timestamp)
        except:
            pass

    if is_modify:
        if folio.name == folio_name:
            return -1
        folio.modify_at = timestamp
        old_allocations = json.loads(folio.allocations) if isinstance(folio.allocations, str) else json.loads(folio.allocations.decode())
        allocations_history = json.loads(folio.allocations_history.decode()) if folio.allocations_history else []
        allocations_history.append(
            [{"coin_name": allo["coin_name"], "weight": allo["weight"], "price": allo["price"]} for allo in
             old_allocations])
        folio.allocations = json.dumps(allocations)
        folio.allocations_history = json.dumps(allocations_history[-30:])
        await toFolioPerformance(user_id, folio_id, folio, timestamp, allocations)

    if is_create:
        folio.modify_at = timestamp
        await toFolioPerformance(user_id, folio_id, folio, timestamp, allocations)
        if performance:
            await updateFolioPerformance(folio_id, user_id, proforma=performance, modify_at=timestamp)
    else:
        folio.init_assets = init_assets
    await folio.update()

    if is_ratio:
        await portfolio_ratios(folio)

    return folio


async def toFolioPerformance(user_id, folio_id, folio, timestamp, allocations):

    port = port_folio({"folio_id": folio.id, "Allocations": allocations, "Name": folio.name})
    modify_at = toPreTimestamp(folio.created_at, day_num=365)
    db = Connection.getInstance()
    effective_date = datetime.datetime.utcfromtimestamp(int(folio.created_at))
    effective_date = str(effective_date).split(" ")[0] + " 00:00:00"
    pre_at = int(time.mktime(time.strptime(effective_date, '%Y-%m-%d %H:%M:%S')))
    proforma = await port.calc_proforma(db, modify_at, pre_at, folioPerformance=False, modify_num=365)
    if len(proforma):
        dates = proforma.index
        rets = proforma.values
        performance = {int(d.timestamp()):float(str(p))  for d, p in zip(dates, rets)}
        await updateFolioPerformance(folio_id, user_id, proforma=performance, pre=1, modify_at=timestamp)


async def updateFolio(folio_id, folio_name, modify_at, allocations=[]):

    folio = await Portfolio.find(folio_id)
    pre_data = {}
    if folio:
        if folio.name == folio_name:
            return -1, pre_data
        else:
            pre_data = copy.deepcopy(folio.json())
            folio.name = folio_name
            folio.allocations = json.dumps(allocations)
            allocations_history = json.loads(folio.allocations_history.decode()) if folio.allocations_history else []
            allocations_history.append(
                [{"coin_name": allo["coin_name"], "weight": allo["weight"], "price": allo["price"]} for allo in
                 allocations])
            folio.allocations_history = json.dumps(allocations_history[-30:])
            folio.modify_at = modify_at
            await folio.update()
    return folio, pre_data


async def updateHour24History(folio_id, folio=None):
    """
    :param folio_id:
    :return:
    """
    if not folio:
        folio = await Portfolio.find(folio_id)
    if folio:
        hour_24_history = await calculate_portfolio(folio_id, folio=folio, re_cal=True, to_roi_rate=True)
        hour_24_history = float(round(float(hour_24_history * 100), 3))
        folio.hour_24_history = hour_24_history if hour_24_history else 0.001
        await folio.update()
        try:
            timestamp = int(time.time())
            styleTime = datetime.datetime.utcfromtimestamp(timestamp)
            pre_date = str(styleTime).split(" ")[0]
            effective_date = pre_date + " 00:00:00"
            effective_time = time.mktime(time.strptime(effective_date, '%Y-%m-%d %H:%M:%S'))
            performance = {int(effective_time): hour_24_history}
            if folio.pre_date == pre_date:
                 await updateFolioPerformance(folio_id, folio.user_id, proforma=performance, modify_at=timestamp)
        except:
            pass

    return folio


async def updateFolioHistory(folio_id, folio_data={}):
    """
    :param folio_id:
    :param folio_data:  {"Annualized Return":[],
                   "Period volatility":{"volatility":""},
                   "Max Drawdown":{"max_drawdown":"","day_7_drawdown":""}}
    :return:
    """
    folio = await Portfolio.find(folio_id)
    if folio:
        return_data = folio_data["Cumulative Return"]
        hour_24_history = await calculate_portfolio(folio_id, folio=folio, re_cal=True, to_roi_rate=True)
        folio.entire_history = folio_data.get("entire_history",0)
        folio.day_7_history = folio_data.get("day_7_history", 0)
        folio.max_history = float(round(float(return_data[0].split("%")[0]), 3)) if len(return_data) > 0 else 0.0
        folio.hour_24_history = float(round(float(hour_24_history*100), 3)) if hour_24_history else 0.001
        folio.day_30_history = float(round(float(return_data[2].split("%")[0]), 3)) if len(return_data) > 2 else 0.0
        folio.day_60_history = str(return_data[3]) if len(return_data) > 3 else "0.0"
        folio.day_90_history = str(return_data[4]) if len(return_data) > 4 else "0.0"
        folio.day_182_history = str(return_data[5]) if len(return_data) > 5 else "0.0"
        folio.day_365_history = str(return_data[6]) if len(return_data) > 6 else "0.0"
        folio.max_drawdown = str(folio_data["Max Drawdown"]["max_drawdown"])
        folio.day_7_drawdown = str(folio_data["Max Drawdown"]["day_7_drawdown"])
        folio.day_7_volatility = str(folio_data["Period volatility"]["day_7_volatility"])
        folio.volatility = str(folio_data["Period volatility"]["volatility"])
        await folio.update()
    return folio


async def saveFolio(user_id, name, allocations, modify_at):

    port_folio = Portfolio(user_id=user_id, name=name, allocations=json.dumps(allocations), modify_at=modify_at)
    rows = await port_folio.save()
    return port_folio, rows


async def findFolio(pk=""):

    port_folio = await Portfolio.find(pk)
    return port_folio


async def findFolioNumber(where="", args=[]):

    count = await Portfolio.findNumber("count(id)", where=where, args=args)
    return count


async def findFolioRate(history_value="entire_history", args=[]):

    win_count = await Portfolio.findNumber("count(id)", where="%s <= ?"%history_value, args=args)
    fail_count = await Portfolio.findNumber("count(id)", where="%s > ?"%history_value, args=args)
    sumCount = win_count + fail_count
    return win_count, fail_count, sumCount

async def find_folios_by_userId(user_id):

    folios = await Portfolio.findAll(where="user_id=?", args=[user_id,])
    return folios

async def find_folio_sort(user_id, history_value):
    folios_list = []
    folios = await find_folios_by_userId(user_id)
    sumCount = await Portfolio.findNumber("count(id)")
    for fol in folios:
        folio_id = fol.id
        folio = fol.json()
        win_count = await Portfolio.findNumber("count(id)", where="%s <= ?"%history_value, args=[folio[history_value]])
        fail_count = await Portfolio.findNumber("count(id)", where="%s > ?"%history_value, args=[folio[history_value]])
        succe_rate = round(float(win_count) * 100 / float(sumCount), 5)
        allocations = json.loads(folio["allocations"].decode())
        allocations, init_assets = await calculate_weight(allocations)
        hour_24_history = await calculate_portfolio(folio_id, folio=fol, re_cal=True, to_roi_rate=True)
        income_rate = round(float(folio[history_value]), 5) if history_value!="hour_24_history" else round(float(hour_24_history)*100, 5)
        item = {"succe_rate": "%s%%" % str(succe_rate), "entire_history": "%s%%" % str(income_rate), "rank": fail_count + 1}
        item["folio_id"] = folio_id
        item["folio_name"] = folio["name"].rstrip(", ")
        item["current_balance"] = init_assets
        item["allocations"] = [{"coin_name": alloc.get("coin_name", ""),"number": alloc.get("number", ""),
                                "weight": "%s%%"%str(round(float(alloc.get("weight", 0)) * 100, 3)),
                                "rate": "%s%%"%str(round(float(alloc.get("rate",0)) * 100, 3)),
                                "coin_id": alloc.get("coin_id", ""), "price": alloc.get("price", "")}
                               for alloc in allocations]

        item["hour_24_history"] = "%s%%"%str(round(hour_24_history*100,5))
        item["max_drawdown"] = (folio["day_7_drawdown"] if history_value=="day_7_history" else folio["max_drawdown"]) if history_value!="hour_24_history" else "-"
        item["volatility"] = (folio["day_7_volatility"] if history_value=="day_7_history" else folio["volatility"]) if history_value!="hour_24_history" else "-"
        item["read_num"] = folio["read_num"]
        item["created_at"] = folio["created_at"]
        folios_list.append(item)
    return folios_list


async def read_folio(folio_id, folio=None):

    if not folio:
        folio = await Portfolio.find(folio_id)
    if folio:
        folio.read_num = folio.read_num + 1
        await folio.update()
    return folio


async def findFolioAll(history_value, offset, limit, read=False):
    folios_list = []
    folios = await Portfolio.findAll(orderBy='%s desc' % history_value, limit=(int(offset), int(limit)))
    user_ids = [folio.user_id for folio in folios]
    user_objs = await user_dao.findUserByIds(user_ids)
    user_dict = {user_obj.user_id : user_obj for user_obj in user_objs}
    for index, folio in enumerate(folios):
        item = {}
        user_obj = user_dict.get(folio.user_id, None)
        item["folio_id"] = folio.id
        item["head_image_url"] = user_obj.head_image_url if user_obj else ""
        item["folio_name"] = folio.name.rstrip(", ") if read else ""
        allocations = json.loads(folio.allocations) if isinstance(folio.allocations, str) else json.loads(folio.allocations.decode())
        item["allocations"] = [{"coin_name": alloc.get("coin_name",""), "weight": str(round(float(alloc.get("weight",0)) * 100, 3)) + "%",
                                "coin_id": alloc.get("coin_id",""), "price": alloc.get("price","")}
                               for alloc in allocations] if read else []
        item["user_name"] = user_obj.nickname if user_obj else ""
        item["max_drawdown"] = folio.max_drawdown
        item["hour_24_history"] = str(folio.hour_24_history) + "%"
        item["entire_history"] = str(folio.entire_history)+"%"
        item["day_7_history"] = str(folio.day_7_history)+"%"
        item["read_num"] = folio.read_num
        item["created_at"] = folio.created_at
        folios_list.append(item)

    return folios_list

async def delFolioPerformance(folio_id):

    pers = await FolioPerformance.findAll(where="folio_id=?", args=[folio_id, ])
    for per in pers:
        await per.remove()

async def GetFolioPerformance(folio_id, state=None):

    performance_data = {}
    if state:
        pers = await FolioPerformance.findAll(where="folio_id=? and state=?", args=[folio_id, state],
                                              orderBy='created_at asc')
        return pers
    else:
        pers = await FolioPerformance.findAll(where="folio_id=?", args=[folio_id,], orderBy='created_at asc')

    if pers:
        created_at = pers[0].created_at
        modify_at = pers[0].modify_at
        id_str =  pers[0].id
        pre_data = json.loads(pers[0].performance_data.decode())
        pre_performance = getPerformanceList(pre_data)
        now_data = []
        for per in pers[1:]:
            perfor_data = json.loads(per.performance_data.decode())
            performance = getPerformanceList(perfor_data)
            now_data.append({"create_at":per.created_at,"modify_at":per.modify_at, "data":performance, "id":per.id})
        performance_data["pre_data"] = {"create_at":created_at,"modify_at":modify_at, "data":pre_performance, "id":id_str}
        performance_data["now_data"] = now_data
        performance_data["folio_id"] = folio_id

    return performance_data


async def updateFolioPerformance(folio_id, user_id, proforma={}, pre=0, modify_at=""):

    if not isinstance(proforma, dict):
        return None

    pers = await FolioPerformance.findAll(where="folio_id=?", args=[folio_id, ], orderBy='created_at asc')
    if pers:
        if pre:
            per = pers[0]
            per.user_id = user_id
            per.performance_data = json.dumps(proforma)
            per.modify_at = float(modify_at) if modify_at else float(time.time())
            await per.update()
        else:
            if len(pers) == 1:
                per_new = FolioPerformance(folio_id=folio_id, user_id=user_id, performance_data=json.dumps(proforma),
                                           state=1)
                await per_new.save()
            else:
                now_per = None
                for per_item in pers[1:]:
                    if per_item.state > 0:
                        midTime = int(per_item.modify_at) - int(per_item.created_at)
                        if midTime < 3600*24*180:
                            now_per = per_item
                            break
                        elif midTime >= 3600*24*180:
                            per_item.state = -1
                            await per_item.save()
                if now_per:
                    perfor_data = json.loads(now_per.performance_data.decode())
                    for key in proforma:
                        perfor_data[key] = proforma[key]
                    now_per.performance_data = json.dumps(perfor_data)
                    now_per.modify_at = float(modify_at) if modify_at else float(time.time())
                    await now_per.update()
                else:
                    per_new = FolioPerformance(folio_id=folio_id, user_id=user_id, performance_data=json.dumps(proforma),
                                               state=1)
                    await per_new.save()
    else:
        per = FolioPerformance(folio_id=folio_id, user_id=user_id, performance_data=json.dumps(proforma))
        await per.save()

    return True





