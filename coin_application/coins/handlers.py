import json

from lib.redis import Redis
from coin_application.coins import dao
from lib.apis import Page
from lib.baseweb import get
from lib.utils import get_page_index, _
from settings import hotCoins

@get('/coinai/get/coins/list',auth=False)
async def get_coin_list(request, *, offset=0, limit=20, name=""):

    result = {"error": 0, "data": "", "message": ""}
    if name:
        dataList = await dao.findCoinByName(name)
        count = len(dataList)
    else:
        count = 702
        page_index = get_page_index(offset)
        limit = int(limit)
        if limit > 20:
            limit = 20
        page = Page(count, page_index, limit)
        dataList = await dao.findCoinAllList(page.offset, page.limit)

    result["data"] = {"items":dataList, "count": count}
    return result


#search coin info
@get('/coinai/get/coins/search',auth=False)
async def get_coin_search(request, *, name):

    result = {"error": 0, "data": "", "message": ""}
    if name:
        dataList = await dao.findCoinByName(name)
    else:
        dataList = await dao.findHotCoinList()
    result["data"] = dataList
    return result

#get coin list
@get('/coinai/get/coins/namelist',auth=False)
async def get_coin_name_list(request):

    result = {"error": 0, "data": "", "message": ""}
    redis_obj = Redis.getInstance()
    coin_name_list = redis_obj.get("coin_name_list")
    
    if not coin_name_list:
        dataList = await dao.findHotCoinList(all=1)
        redis_obj.set("coin_name_list", json.dumps(dataList))
    else:
        dataList = json.loads(coin_name_list.decode())
    result["data"] = dataList
    return result


#get coin info
@get('/coinai/get/coins/detail/{coin_id}',auth=True)
async def get_coin_detail(coin_id, request):
    """
    :param coin_id:
    :param request:
    :return:
    {
      "coin_name": "",
      "coin_id": "",
      "coin_url": "",
      "simple_name": "",
      "market_cap": "",
      "supply_pvolume": "",
      "trading_24_volume": "",
      "hours_1_index": "",
      "hours_24_index": "",
      "day_7_index": "",
      "price": "",
      "price_btc": "",
      "price_rate": "",
      "price_btc_rate": "",
      "trading_24_volume": "",
      "trading_24_btc_volume": ""
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    if coin_id:
        coin_info = await dao.findCoinDetail(coin_id)
    else:
        coin_info = {}
    if coin_info:
        result["data"] = coin_info
    else:
        result["error"] = 411
        result['data'] = {}
        result['message'] = _("411_COIN_NOT_EXIST", language)  # "This coin does not exist."
    return result


@get('/coinai/get/coins/analysis',auth=False)
async def get_coin_analysis(request):
    """
    :param request:
    :return:
    {"error": 0,
    "data": [
        {
        "coin_name":"",
        "coin_id":"",
        "coin_url":"",
        "price":"",
        "price_btc":"",
        "price_rate":"",
        "price_btc_rate":"",
        "trading_24_volume":"",
        "trading_24_btc_volume":"",
        }
    ],
    "message": ""
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    coin_list =  ["Banca"]
    
    coin_list.extend(hotCoins)
    dataList = await dao.findCoinByNames(coin_list)
    
    result["data"] = dataList
    return result
