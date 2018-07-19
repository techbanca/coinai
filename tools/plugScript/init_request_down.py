import os
import contextlib
import sys
import time, json
import asyncio
import aiohttp
import requests, datetime

current_path = os.path.realpath(__file__)
root_path = current_path.split("tools")[0]
sys.path.append(root_path)

from decimal import Decimal
from logger.client import collect_info
from lib.redis import Redis
from coin_application.coins.models import Coin
from coin_application.portfolios.models import Portfolio
from lib import orm
from lib.config import configs

ticker_url = "https://api.coinmarketcap.com/v2/ticker/?convert=BTC&start=%s&limit=100"

output_path = current_path.split("plugScript")[0] + "plugScript/data/csv/"
img_path = current_path.split("plugScript")[0] + "plugScript/data/img/"
coin_url_path = current_path.split("plugScript")[0] + "plugScript/data/coin_url/"

url_list = []

def get_one_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content , response
    else:
        return "",""

async def fetch_async(url, session, toJson=False):

    resp = await session.get(url)
    with contextlib.closing(resp):
        if resp.status == 200:
            data = await resp.read()
            if toJson:
                res = json.loads(data.decode())
                if "Response" in res or "Message" in res:
                    url_list.append(url)
                    return {}
                else:
                    return res
            else:
                return data
        else:
            return {}


async def get_coin_url():

    coins = {}
    objs = await Coin.findAll()
    for coin in objs:
        coins[coin.simple_name] = coin
    return coins


async def bs4_paraser(bit_names):

    all_value = []
    all_dict_value = {}
    value = {}

    coins = await get_coin_url()
    for simple_name in coins:
        if simple_name in bit_names:
            pre_item = bit_names[simple_name]
            modify_at = float(pre_item.get("last_updated", time.time()))
            usd = pre_item.get("quotes", {}).get("USD", {})
            btc_data = pre_item.get("quotes", {}).get("BTC", {})
            bitcoin_name = pre_item.get("name", "")
            simple_name = pre_item.get("symbol", "")
            website_slug = pre_item.get("website_slug", "")
            rank = pre_item.get("rank", "")
            market_cap = "$" + str(usd.get("market_cap", "")).strip("$")
            price = "$" + str(usd.get("price", "")).strip("$")
            supply_pvolume = str(pre_item.get("circulating_supply", ""))
            trading_24_volume = "$" + str(usd.get("volume_24h", "?")).strip("$")
            hours_1_index = str(usd.get("percent_change_1h", "?")).strip("\n") + "%"
            hours_24_index = str(usd.get("percent_change_24h", "?")).strip("\n") + "%"
            percent_change_24h = str(usd.get("percent_change_24h", "?")).strip("$")
            day_7_index = str(usd.get("percent_change_7d", "?")).strip("\n") + "%"
            price_btc = str(btc_data.get("price", "")).strip("$")
            trading_24_btc_volume = str(btc_data.get("volume_24h", "?")).strip("$")
            market_cap_btc = str(btc_data.get("market_cap", "?")).strip("$")
            btc_percent_change_24h = str(btc_data.get("percent_change_24h", "?")).strip("$")

            value['name'] = bitcoin_name
            value['simple_name'] = simple_name
            value['market_cap'] = market_cap
            value['modify_at'] = modify_at
            value['price_btc'] = price_btc
            value['trading_24_btc_volume'] = trading_24_btc_volume
            value['market_cap_btc'] = market_cap_btc
            value['website_slug'] = website_slug
            value['price'] = price
            value['supply_pvolume'] = supply_pvolume
            value['trading_24_volume'] = trading_24_volume
            value['hours_1_index'] = hours_1_index
            value['hours_24_index'] = hours_24_index
            value['day_7_index'] = day_7_index
            value['btc_percent_change_24h'] = btc_percent_change_24h
            value['percent_change_24h'] = percent_change_24h

            all_value.append(value)
            all_dict_value[bitcoin_name] = value
            value = {}
        else:
            pass

    return all_value


async def get_folio():

    folios_lists = await Portfolio.findAll()
    folios_lists = sorted(folios_lists, key=lambda folio: float(folio.entire_history), reverse=True)
    return folios_lists


def __default(obj):

    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        raise TypeError('%r is not JSON serializable' % obj)


async def main(loop, day_num):

    await orm.create_plug_pool(loop=loop, **configs.db)
    session = aiohttp.ClientSession(conn_timeout=1800)

    data_lists = []
    
    for num in range(10):
        result_data = await fetch_async(ticker_url % (num * 100 + 1), session, toJson=True)
        if result_data:
            data_list = result_data["data"].values()
            data_lists.extend(data_list)

    bit_names = {str(val["symbol"]): val for val in data_lists}
    all_value = await bs4_paraser(bit_names)
    collect_info("init_request_down main all_value is %s" % str(all_value))
    redis_obj = Redis.getInstance()
    if day_num == 0:
        folios_lists = await get_folio()
        for folio_val in folios_lists:
            redis_obj.producer("folio_24_hour:queue", json.dumps({"id": folio_val.id}, ensure_ascii=False, default=__default))

            
    if day_num == 1:
        for val in all_value:
            redis_obj.producer("coin_all_day:queue", json.dumps(val))

        folios_lists = await get_folio()
        for folio_val in folios_lists:
            redis_obj.producer("folio_all_items:queue", json.dumps({"id": folio_val.id}, ensure_ascii=False, default=__default))

    if day_num == -1:
        for val in all_value:
            redis_obj.producer("coin_all_minute:queue", json.dumps(val))

    await session.close()


def run_coin_all(day_num=0):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop, day_num=day_num))

if __name__ == '__main__':
    run_coin_all()

