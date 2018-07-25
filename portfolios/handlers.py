import json
import time

from coin_application.coins import dao as coin_dao
from coin_application.portfolios import dao
from coin_application.portfolios.dao import calculate_portfolio, calculate_weight
from coin_application.reports.coinReport import portfolio_ratios
from coin_application.users import dao as user_dao
from lib.apis import Page
from lib.baseweb import get, post, options
from lib.utils import get_page_index, _

history_dict = {"total":"entire_history", "hour_24":"hour_24_history" ,"day_7":"day_7_history", "day_30":"day_30_history"}

@post('/coinai/add/portfolio')
async def post_coin_portfolios(request, *, portfolios):

    res = await add_coin_portfolios(request, portfolios)
    return res

@options('/coinai/add/portfolio')
async def options_coin_portfolios(request, *, portfolios):

    res = await add_coin_portfolios(request, portfolios)
    return res

async def add_coin_portfolios(request, portfolios):

    result = {"error": 0, "data": "", "message":""}

    user_id = request.__user__.get("referId", "")
    nickname = request.__user__.get("referName", "")
    head_image_url = request.__user__.get("headImgUrl", "")
    name = request.__user__.get("loginName", "")
    language = request.__user__.get("language", "en")
    status = request.__user__.get("status", 0)
    if int(status) != 1:
        result["error"] = 410
        
        result["message"] = _("410_ACCOUNT_ACCESS", language)  # "This account is not activated and has no access rights."
        return result

    res = await user_dao.saveUser(user_id, name, nickname, head_image_url, "", "", "", 0, status)
    if res != 1:
        res = await user_dao.findAllUser(user_id)
        if not res:
            res = await user_dao.saveUser(user_id, name, nickname, head_image_url, "", "", "", 0, status)
        if not res:
            result["error"] = 431
            result["message"] = _("431_ACCOUNT_ACCESS", language)  # "This account has no access rights."
            return result

    folio_name = ""
    allocations = []
    if len(portfolios) > 10 or len(portfolios) < 1:
        result["error"] = 406
        result["message"] = _("406_NUMBER_COINS", language)  # "The number of coins has to be between 1 and 10."
        return result

    portfolios = sorted(portfolios, key=lambda folio : folio["weight"], reverse=True)
    all_weight = 0.0
    coin_list = []
    repeat = 0
    usdt_w = 0
    modify_at = time.time()
    for folio in portfolios:
        coin_name = folio.get("coin_name","")
        if coin_name not in coin_list:
            if coin_name:
                coin_list.append(coin_name)
            else:
                continue
        else:
            repeat = 1
            break

        weight = folio.get("weight","")
        if not weight:
            continue

        weight = float(round(float(weight), 2))
        if weight < 0:
            result["error"] = 417
            result["message"] = _("417_WEIGHT_NOT_LESS_0", language)  # "The weight should not be less than 0."
            return result

        coin_id = folio.get("coin_id","")
        all_weight += weight
        all_weight = float(round(all_weight,2))
        if not coin_id:
            coin_obj = await coin_dao.findObjByName(coin_name)
            coin_id = coin_obj.id if coin_obj else ""
        else:
            coin_obj = await coin_dao.findCoin(coin_id)
        if not coin_obj:
            continue

        if coin_name.lower() in ("usdt", "tether"):
            usdt_w = weight

        if all_weight <= 1.0:
            folio_name += coin_obj.simple_name + ":" + str(int(float(weight) * 100)) + "% "
            price = coin_obj.price.replace(",", "").replace("$", "")
            net_return = float(round(100*(float(price) - float(coin_obj.pre_price.replace(",","").replace("$",""))) \
                       / float(coin_obj.pre_price.replace(",","").replace("$","")),5))
            effective_date = float(int(modify_at))
            number = round(float(1000000 * weight / float(price)), 3)
            allocations.append(
                {"coin_name": coin_obj.simple_name, "weight": weight, "coin_id": coin_id,
                 "number": float(number), "rate": 0.0, "price": price,
                 "Performance": [{"NetReturn": net_return, "EffectiveDate": effective_date}]})

    if repeat:
        result["error"] = 407
        result["message"] = _("407_DUPLICATION_COIN", language)  # "The portfolio have the duplication of coin."
        
        return result

    if all_weight > 1.0:
        result["error"] = 415
        result["message"] = _("415_WEIGHT_EXCEED", language)  # "Coin weight cannot exceed 100%."
        return result

    if all_weight < 1:
        weight = float(round(float(100 - all_weight*100) / 100, 2))
        if weight > 0.0:
            if usdt_w > 0.0:
                allocations_dict = {alloc["coin_name"].lower():alloc for alloc in allocations}
                alloc = allocations_dict.get("usdt",{})
                if alloc:
                    alloc["weight"] += weight
                    alloc["weight"] = float(round(alloc["weight"], 2))
                    price = alloc["price"]
                    number = round(float(1000000 * alloc["weight"] / float(price)), 3)
                    alloc["number"] = float(number)
                    alloc["rate"] = 0.0
                    allocations_dict["usdt"] = alloc
                allocations = list(allocations_dict.values())
            else:
                coin_items = await coin_dao.findCoinByName("usdt")
                coin_id = coin_items[0].get("coin_id","") if coin_items else ""
                folio_name +=  "USDT:" + str(round(float(weight) * 100, 2)) + "% "
                coin_obj = await coin_dao.findCoin(coin_id)
                price = coin_obj.price.replace(",", "").replace("$", "")
                number = round(float(1000000 * weight / float(price)), 3)
                net_return = float(round(100 * (float(price) - float(coin_obj.pre_price.replace(",", "").replace("$", ""))) \
                                       / float(coin_obj.pre_price.replace(",", "").replace("$", "")), 5))
                effective_date = float(int(modify_at))
                allocations.append({"coin_name": "USDT", "weight": weight, "coin_id": coin_id, "price": price,
                                    "number": float(number), "rate": 0.0, "Performance": [{"NetReturn": net_return,
                                                                                           "EffectiveDate": effective_date}]})

    count = await dao.findFolioNumber(where="user_id=?", args=[user_id])
    if count >= 3:
        result["error"] = 401
        result["message"] = _("401_MAXIMUM_THREE", language)  # "The Maximum number of portfolio is three."
    else:
        port_folio, rows = await dao.saveFolio(user_id, folio_name, allocations, modify_at)
        if rows == 1:
            port_folio = await calculate_portfolio(port_folio.id, port_folio, is_create=True)

        result["data"] = {"folio_id": port_folio.id}
        result["message"] = _("0_ADD_SUCCESSFUL", language)  # "Added successfully."

    return result

@post('/coinai/modify/portfolio/{folio_id}')
async def post_update_coin_portfolios(folio_id, request, *,  portfolios):

    res = await modify_coin_portfolios(request, folio_id, portfolios)
    return res

@options('/coinai/modify/portfolio/{folio_id}')
async def options_update_coin_portfolios(folio_id, request, *, portfolios):

    res = await modify_coin_portfolios(request, folio_id, portfolios)
    return res

async def modify_coin_portfolios(request, folio_id, portfolios):

    result = {"error": 0, "data": {}, "message":""}
    language = request.__user__.get("language", "en")
    folio_name = ""
    allocations = []

    port_folio = await dao.findFolio(folio_id)
    if not port_folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userid = request.__user__.get("referId", "")
    if int(userid) != port_folio.user_id:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    if len(portfolios) > 10 or len(portfolios) < 1:
        result["error"] = 406
        result["message"] = _("406_NUMBER_COINS", language)  # "The number of coins must be between 1 and 10."
        return result

    allo = json.loads(port_folio.allocations) if isinstance(port_folio.allocations, str) else json.loads(port_folio.allocations.decode())
    allo, init_assets = await calculate_weight(allo)
    portfolios = sorted(portfolios, key=lambda folio: folio["weight"], reverse=True)
    all_weight = 0.0
    coin_list = []
    repeat = 0
    usdt_w = 0
    modify_at = time.time()
    for folio in portfolios:
        coin_name = folio.get("coin_name", "")
        if coin_name not in coin_list:
            if coin_name:
                coin_list.append(coin_name)
            else:
                continue
        else:
            repeat = 1
            break

        weight = folio.get("weight", "")
        if not weight:
            continue

        weight = float(round(float(weight), 2))
        if weight < 0:
            result["error"] = 417
            result["message"] = _("417_WEIGHT_NOT_LESS_0", language)  # "The weight should not be less than 0."
            return result

        coin_id = folio.get("coin_id", "")
        all_weight += float(weight)
        all_weight = float(round(all_weight, 2))
        if not coin_id:
            coin_obj = await coin_dao.findObjByName(coin_name)
            coin_id = coin_obj.id if coin_obj else ""
        else:
            coin_obj = await coin_dao.findCoin(coin_id)
        if not coin_obj:
            continue

        if coin_name.lower() in ("usdt", "tether"):
            usdt_w = float(weight)

        if all_weight <= 1.0:
            folio_name += coin_obj.simple_name + ":" + str(int(float(weight) * 100)) + "% "
            net_return = float(round(100 * (float(coin_obj.price.replace(",", "").replace("$", "")) \
                        - float(coin_obj.pre_price.replace(",", "").replace("$", ""))) \
                        / float(coin_obj.pre_price.replace(",", "").replace("$", "")), 5))
            effective_date = float(int(modify_at))
            price = coin_obj.price.replace(",", "").replace("$", "")
            number = round(float(init_assets * weight / float(price)), 3)
            allocations.append(
                {"coin_name": coin_obj.simple_name, "weight": weight, "coin_id": coin_id,
                 "number":number, "rate": 0.0, "price": price, "Performance": [{"NetReturn": net_return,
                                                                "EffectiveDate": effective_date}]})

    if repeat:
        result["error"] = 407
        result["message"] = _("407_DUPLICATION_COIN", language)  # "The portfolio have the duplication of coin."
        return result

    if all_weight > 1.0:
        result["error"] = 415
        result["message"] = _("415_WEIGHT_EXCEED", language)  # "Coin weight cannot exceed 100%."
        return result

    if all_weight < 1:
        weight = float(round(float(100 - all_weight*100) / 100, 2))
        if weight > 0.0:
            if usdt_w > 0.0:
                allocations_dict = {alloc["coin_name"].lower():alloc for alloc in allocations}
                alloc = allocations_dict.get("usdt",{})
                if alloc:
                    alloc["weight"] += weight
                    alloc["weight"] = float(round(alloc["weight"], 2))
                    price = alloc["price"]
                    number = round(float(init_assets * alloc["weight"] / float(price)), 3)
                    alloc["number"] = float(number)
                    alloc["rate"] = 0.0
                    allocations_dict["usdt"] = alloc
                allocations = list(allocations_dict.values())
            else:
                coin_items = await coin_dao.findCoinByName("usdt")
                coin_id = coin_items[0].get("coin_id","") if coin_items else ""
                folio_name +=  "USDT:" + str(round(float(weight) * 100, 2)) + "% "
                coin_obj = await coin_dao.findCoin(coin_id)
                price = coin_obj.price.replace(",", "").replace("$", "")
                number = round(float(init_assets * weight / float(price)), 3)
                net_return = float(round(100 * (float(coin_obj.price.replace(",", "").replace("$", "")) \
                                              - float(coin_obj.pre_price.replace(",", "").replace("$", ""))) \
                                       / float(coin_obj.pre_price.replace(",", "").replace("$", "")), 5))
                effective_date = float(int(modify_at))
                allocations.append({"coin_name": "USDT", "weight": weight, "coin_id": coin_id, "price": price,
                                    "number":number, "rate": 0.0, "Performance": [{"NetReturn": net_return,
                                                                                   "EffectiveDate": effective_date}]})

    folio = await calculate_portfolio(port_folio.id, port_folio, is_modify=True, folio_name=folio_name,
                                      new_allocations=allocations, modify_at=modify_at)
    if folio:
        result["data"] = {"folio_id": folio_id}
        result["message"] = _("0_MODIFY_SUCCESSFUL", language)  # "Modified successfully."
    else:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."

    return result


@get('/coinai/get/portfolio/allocations/{folio_id}',auth=True)
async def portfolio_allocations(folio_id, request):

    result = {"error": 0, "data": "", "message":""}
    language = request.__user__.get("language", "en")

    folio = await dao.findFolio(folio_id)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userid = request.__user__.get("referId", "")
    if int(userid) != folio.user_id:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    allocations = json.loads(folio.allocations) if isinstance(folio.allocations, str) else json.loads(folio.allocations.decode())
    allocations, init_assets = await calculate_weight(allocations)
    portfolio = {"allocations":[{"coin_name": allo['coin_name'], "weight": allo['weight'], "number": allo.get("number", ""),
                                 "coin_id": allo['coin_id'], "price": allo['price']} for allo in allocations],
                 "folio_id": folio_id, "current_balance": init_assets
                 }
    result['data'] = portfolio

    return result


@get('/coinai/get/portfolio/rankinglist',auth=False)
async def portfolio_ranking_list(request, *, sort_type, offset=0, limit=20):

    result = {"error": 0, "data": "", "message":""}
    read = request.__user__.get("read", False)
    count = await dao.findFolioNumber()
    page_index = get_page_index(offset)
    limit = int(limit)
    if limit > 20:
        limit = 20
    page = Page(count, page_index, limit)
    history_value = history_dict.get(sort_type, "entire_history")
    folios_list = await dao.findFolioAll(history_value, page.offset, page.limit, read=read)
    result["data"] = {"items":folios_list, "count": count}

    return result

@get('/coinai/get/portfolio/oneself/folioidlist',auth=True)
async def portfolio_folioIdList_oneself(request):

    result = {"error": 0, "data": "", "message": ""}
    user_id = request.__user__.get("referId", "")
    port_folio_ids = []
    folios_lists = await dao.find_folios_by_userId(user_id)
    for port_folio in folios_lists:
        port_folio_ids.append(port_folio.id)
    result["data"] = {"folio_ids": port_folio_ids}

    return result


@get('/coinai/get/portfolio/oneself',auth=True)
async def portfolio_detail_oneself(request, *, sort_type):

    result = {"error": 0, "data": "", "message": ""}
    user_id = request.__user__.get("referId", "")
    history_value = history_dict.get(sort_type, "entire_history")
    folios_lists = await dao.find_folios_by_userId(user_id)
    for port_folio in folios_lists:
        await portfolio_ratios(port_folio)
    folios_list = await dao.find_folio_sort(user_id, history_value)
    result["data"] = folios_list
    return result


@get('/coinai/delete/portfolio/{folio_id}',auth=True)
async def portfolio_delete(folio_id, request):

    result = {"error": 0, "data": "", "message":""}
    language = request.__user__.get("language", "")

    folio = await dao.findFolio(folio_id)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  #"This portfolio does not exist."
        return result

    userid = request.__user__.get("referId", "")
    if int(userid) != folio.user_id:
        result["error"] = 409
        result["data"] = {}
        result["message"] = _("409_NOT_DELETE", language)  #"You do not have permission to delete this portfolio."
        return result

    rows = await folio.remove()
    if rows == 1:
        await dao.delFolioPerformance(folio_id)
    result["message"] = _("0_DELETE_SUCCESSFUL", language)  #"Deleted successfully."

    return result


@get('/coinai/get/portfolio/detail/{folio_id}',auth=False)
async def portfolio_detail(folio_id, request, *, sort_type=""):

    result = {"error": 0, "data": "", "message":""}

    language = request.__user__.get("language", "")
    folio = await dao.findFolio(folio_id)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  #"This portfolio does not exist."
        return result

    read = request.__user__.get("read", False)
    userid = request.__user__.get("referId", "")
    if int(userid) == folio.user_id:
        read = 1

    history_value = history_dict.get(sort_type, "entire_history")
    if history_value != "hour_24_history":
        income_rate = round(float(folio[history_value]), 5)
    else:
        day_history = await calculate_portfolio(folio_id, folio=folio, re_cal=True, to_roi_rate=True)
        income_rate = round(float(day_history) * 100, 5)
    folio = folio.json()
    user_obj = await user_dao.findAllUser(folio["user_id"])
    win_count, fail_count, sumCount = await dao.findFolioRate(history_value=history_value, args=[float(folio[history_value]),])
    allocations = json.loads(folio["allocations"].decode())
    succe_rate = round(float(win_count) * 100/float(sumCount), 5)
    allocations, init_assets = await calculate_weight(allocations)
    allocations = [{"coin_name": alloc.get("coin_name", ""), "number": alloc.get("number", ""),
                    "weight": "%s%%"%str(round(float(alloc.get("weight", 0)) * 100, 3)),
                    "rate":"%s%%"%str(round(float(alloc.get("rate",0)) * 100, 3)),
                    "coin_id": alloc.get("coin_id", ""), "price": alloc.get("price", "")}
                   for alloc in allocations]

    folio_rate = {"succe_rate": "%s%%"%str(succe_rate), "entire_history":"%s%%"%str(income_rate),
                  "volatility":(folio["day_7_volatility"] if history_value=="day_7_history" else folio["volatility"]) if history_value!="hour_24_history" else "-",
                  "max_drawdown":(folio["day_7_drawdown"] if history_value=="day_7_history" else folio["max_drawdown"]) if history_value!="hour_24_history" else "-",
                  "hour_24_history":"%s%%"%str(folio["hour_24_history"]), "read_num": folio["read_num"], "current_balance": init_assets,
                  "allocations":allocations if read else [], "rank":fail_count + 1, "folio_id": folio_id, "user_name": user_obj.nickname if user_obj else "",
                  "head_image_url":user_obj.head_image_url if user_obj else "", "folio_name":folio["name"].rstrip(", ") if read else ""}

    result['data'] = folio_rate

    return result
