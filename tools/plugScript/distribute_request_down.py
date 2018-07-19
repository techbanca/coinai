import codecs, os
import contextlib
import re, sys
import time, json
import asyncio
import aiohttp
import datetime

from bs4 import BeautifulSoup

current_path = os.path.realpath(__file__)
root_path = current_path.split("tools")[0]
sys.path.append(root_path)

from logger.client import collect_info
from coin_application.portfolios.dao import calculate_portfolio, updateHour24History
from lib.redis import Redis
from coin_application.coins.models import Coin, Performance
from lib import orm
from lib.config import configs

search_url = "https://coinmarketcap.com/currencies/%s/historical-data/?start=%s&end=%s"
output_path = current_path.split("plugScript")[0] + "plugScript/data/csv/"
coin_url_path = current_path.split("plugScript")[0] + "plugScript/data/coin_url/"
url_list = []

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


async def down_paraser_item(pre_item, day_num=0, session=None):

    value_dict = {}

    now = datetime.datetime.now()
    if day_num == 1:
        current = now + datetime.timedelta(days=-2)
        current = datetime.datetime(current.year, current.month, current.day, current.hour, current.minute, 0)
        start_day = str(current).split(" ")[0].replace("-","")
        end_day = now.strftime('%Y%m%d')
    elif day_num == 0:
        start_day = "20170401"
        end_day = now.strftime('%Y%m%d')

    if day_num != -1:
        url = search_url%(pre_item["website_slug"], start_day, end_day)
        html = await fetch_async(url, session)
        soup = BeautifulSoup(html, 'html.parser')
    else:
        soup = None

    simple_name = pre_item["simple_name"].upper()
    bitcoin_name = pre_item["name"]
    value_dict[bitcoin_name] = ""

    modify_at = float(pre_item["modify_at"])
    market_cap = pre_item["market_cap"]
    supply_pvolume = pre_item["supply_pvolume"]
    trading_24_volume = pre_item["trading_24_volume"]
    hours_1_index = pre_item["hours_1_index"]
    hours_24_index = pre_item["hours_24_index"]
    btc_percent_change_24h = pre_item["btc_percent_change_24h"]
    percent_change_24h = pre_item["percent_change_24h"]
    day_7_index = pre_item["day_7_index"]

    
    price = pre_item["price"]
    price_btc = pre_item["price_btc"]
    trading_24_btc_volume = pre_item["trading_24_btc_volume"]
    market_cap_btc = pre_item["market_cap_btc"]

    objs = await Coin.findAll(where="simple_name=?", args=[simple_name.upper()])
    old_coin = True
    if objs:
        coin = objs[0]
        price_rate = percent_change_24h
        price_btc_rate = btc_percent_change_24h
        coin.market_cap = market_cap.strip("\n") if isinstance(market_cap, str) else market_cap
        coin.market_cap_btc = market_cap_btc.strip("\n") if isinstance(market_cap_btc, str) else market_cap_btc
        coin.name = bitcoin_name
        if modify_at - coin.modify_at >= 3600 * 24:
            coin.pre_price = coin.price

        coin.price = price.strip("\n") if isinstance(price, str) else price
        coin.supply_pvolume = supply_pvolume.split("*")[0].strip("\n") if isinstance(supply_pvolume, str) else supply_pvolume
        coin.trading_24_volume = trading_24_volume.strip("\n") if isinstance(trading_24_volume, str) else trading_24_volume
        coin.hours_1_index = hours_1_index.strip("\n") if isinstance(hours_1_index, str) else hours_1_index
        coin.hours_24_index = hours_24_index.strip("\n") if isinstance(hours_24_index, str) else hours_24_index
        coin.day_7_index = day_7_index.strip("\n") if isinstance(day_7_index, str) else day_7_index
        coin.price_rate = price_rate.strip("\n") if isinstance(price_rate, str) else price_rate
        if modify_at - coin.modify_at >= 3600 * 24:
            coin.pre_price_btc = coin.price_btc
        coin.website_slug = pre_item["website_slug"]
        coin.price_btc = price_btc.strip("\n") if isinstance(price_btc, str) else price_btc
        coin.price_btc_rate = price_btc_rate.strip("\n") if isinstance(price_btc_rate, str) else price_btc_rate
        coin.trading_24_btc_volume = trading_24_btc_volume.strip("\n") if isinstance(trading_24_btc_volume, str) else trading_24_btc_volume
        coin.modify_at = modify_at
        await coin.update()
    else:
        old_coin = False
        market_cap = market_cap.strip("\n") if isinstance(market_cap, str) else market_cap
        market_cap_btc = market_cap_btc.strip("\n") if isinstance(market_cap_btc, str) else market_cap_btc
        price = price.strip("\n") if isinstance(price, str) else price
        supply_pvolume = supply_pvolume.split("*")[0].strip("\n") if isinstance(supply_pvolume, str) else supply_pvolume
        trading_24_volume = trading_24_volume.strip("\n") if isinstance(trading_24_volume,str) else trading_24_volume
        hours_1_index = hours_1_index.strip("\n") if isinstance(hours_1_index, str) else hours_1_index
        hours_24_index = hours_24_index.strip("\n") if isinstance(hours_24_index, str) else hours_24_index
        day_7_index = day_7_index.strip("\n") if isinstance(day_7_index, str) else day_7_index
        price_rate = "0"
        price_btc = price_btc.strip("\n") if isinstance(price_btc, str) else price_btc
        price_btc_rate = "0"
        trading_24_btc_volume = trading_24_btc_volume.strip("\n") if isinstance(trading_24_btc_volume,str) else trading_24_btc_volume
        coin = Coin(name=bitcoin_name, simple_name=simple_name.upper(), market_cap=market_cap, price=price, supply_pvolume=supply_pvolume,
                    market_cap_btc=market_cap_btc,trading_24_volume=trading_24_volume, hours_1_index=hours_1_index, hours_24_index=hours_24_index,
                    pre_price=price, day_7_index=day_7_index, price_rate=price_rate, price_btc=price_btc, pre_price_btc=price_btc,website_slug=pre_item["website_slug"],
                    price_btc_rate=price_btc_rate,trading_24_btc_volume=trading_24_btc_volume, modify_at = modify_at, create_at=float(time.time()))
        await coin.save()

        start_day = "20170401"
        end_day = now.strftime('%Y%m%d')
        url = search_url % (pre_item["website_slug"], start_day, end_day)
        html = await fetch_async(url, session)
        soup = BeautifulSoup(html, 'html.parser')
        day_num = 0

    if soup:
        all_div_item = soup.find_all(name="div", attrs={"class": "table-responsive"})
        if not all_div_item:
            all_div_item = soup.find_all(name="div", attrs={"id": "historical-data"})
        for div in all_div_item:
            trs = div.find_all(name="tr", attrs={"class": "text-right"})
            for index, tr in enumerate(trs):
                if day_num and old_coin and index >= day_num:
                    break
                tds = tr.find_all(name="td")
                next_index = index + 1
                next_tds = None
                if next_index < len(trs):
                    next_tds = trs[next_index].find_all(name="td")
                try:
                    struct_time = time.strptime(tds[0].text.replace(",", "").strip(""), "%b %d %Y")
                    current = datetime.datetime(struct_time.tm_year, struct_time.tm_mon, struct_time.tm_mday,
                                                struct_time.tm_hour, struct_time.tm_min, struct_time.tm_sec)
                    current_date = current.strftime('%Y-%m-%d %H:%M:%S')
                    effective_date = str(current_date).split(" ")[0]
                except Exception as e:
                    effective_date = tds[0].text.replace("年", "-").replace("月", "-").replace("日", "")

                effective_date = effective_date + " 00:00:01"
                effective_time = time.mktime(time.strptime(effective_date, '%Y-%m-%d %H:%M:%S'))
                close_value = float(tds[4].text)
                net_return = (
                (float(tds[4].text) - float(next_tds[4].text)) / float(next_tds[4].text)) if next_tds else 0.0
                coin_id = coin.id
                res = await Performance.findNumber("count(id)", where="coin_id=? and effective_date=?",
                                                   args=[coin_id, float(effective_time)])
                if res:
                    continue

                    
                perfor = Performance(coin_id=coin_id, close_value=close_value,
                                     net_return=net_return, effective_date=float(effective_time))
                await perfor.save()
                td_str = tds[0].text.replace("年", "-").replace("月", "-").replace("日", "") + "," + tds[4].text + "\n"
                value_dict[bitcoin_name] += td_str

    file = codecs.open(output_path + '^%s.csv'%bitcoin_name.lower(), 'w', encoding='utf-8')
    file.write(value_dict[bitcoin_name])


async def update_redis():

    date_time = str(int(time.time()))
    update_report = {
        "portfolio_ratios": {"update_at": date_time},
        "portfolio_optimization": {"update_at": date_time},
        "portfolio_basic": {"update_at": date_time},
        "portfolio_ai": {"update_at": date_time},
        "portfolio_style": {"update_at": date_time},
        "portfolio_benchmark": {"update_at": date_time},
        "portfolio_risk": {"update_at": date_time},
        "portfolio_versus": {"update_at": date_time},
        "coins_ai": {"update_at": date_time},
        "coins_basic": {"update_at": date_time},
        "coins_ratios": {"update_at": date_time},
        "coins_versus": {"update_at": date_time}
    }

    redis_obj = Redis.getInstance()
    redis_obj.set("update_report", json.dumps(update_report))


async def update_folio():

    while True:
        redis_obj = Redis.getInstance()
        pre_item = redis_obj.customer("folio_all_items:queue")
        if pre_item:
            pre_item = json.loads(pre_item.decode())
            await calculate_portfolio(pre_item["id"], folio=None, re_cal=True, is_ratio=True)
        else:
            break
        time.sleep(0.1)


async def listen_coin_day_task(loop):

    err_data_List = []
    has_data = 0
    session = None
    await main(loop)
    while True:
        redis_obj = Redis.getInstance()
        pre_item = redis_obj.customer("coin_all_day:queue")
        if pre_item:
            if not session:
                session = aiohttp.ClientSession(conn_timeout=1800)
            has_data = 1
            pre_item = json.loads(pre_item.decode().replace("'", '"'))
            collect_info("listen_coin_day_task pre_item is %s" % str(pre_item))
            err_data_List = await run_paraser_item(pre_item, 1, err_data_List, session)
        else:
            if has_data:
                num = redis_obj.getListLen("coin_all_day:queue")
                if num:
                    continue
                has_data = 0
                await print_error_item(1, err_data_List)
                if session:
                    await session.close()
                    session = None
            err_data_List = []
            time.sleep(6)

async def listen_coin_minute_task(loop):

    err_data_List = []
    has_data = 0
    session = None
    await main(loop)
    while True:
        redis_obj = Redis.getInstance()
        pre_item = redis_obj.customer("coin_all_minute:queue")
        if pre_item:
            if not session:
                session = aiohttp.ClientSession(conn_timeout=1800)
            has_data = 1
            pre_item = json.loads(pre_item.decode().replace("'", '"'))
            collect_info("listen_coin_minute_task pre_item is %s"%str(pre_item))
            err_data_List = await run_paraser_item(pre_item, -1, err_data_List, session)
        else:
            if has_data:
                num = redis_obj.getListLen("coin_all_minute:queue")
                if num:
                    continue
                has_data = 0
                await print_error_item(-1, err_data_List)
                if session:
                    await session.close()
                    session = None
            err_data_List = []
            time.sleep(5)

async def listen_folio_24_hour_task(loop):

    has_data = 1
    await main(loop)
    while True:
        redis_obj = Redis.getInstance()
        pre_item = redis_obj.customer("folio_24_hour:queue")
        if pre_item:
            has_data = 1
            pre_item = json.loads(pre_item.decode())
            await updateHour24History(pre_item["id"], folio=None)
        else:
            if has_data:
                num = redis_obj.getListLen("folio_24_hour:queue")
                if num:
                    continue
                has_data = 0
            time.sleep(5)

async def run_paraser_item(pre_item, day_num, err_data_List=[], session=None):

    try:
        await down_paraser_item(pre_item, day_num, session)
    except:
        err_data_List.append(pre_item)
    return err_data_List


async def print_error_item(day_num, err_data_List=[]):

    today_date = datetime.datetime.now()
    current = datetime.datetime(today_date.year, today_date.month, today_date.day,
                                today_date.hour, today_date.minute, today_date.second)
    current_date = current.strftime('%Y%m%d_%H%M')
    if day_num == 1:
        fileName = "coin_all_day_" + current_date
    elif day_num == 0:
        fileName = "coin_all_items_" + current_date
    else:
        fileName = "coin_all_minute_" + current_date
    file = open(coin_url_path + '%s.txt' % fileName, 'w', encoding='utf-8')
    file.write(str(err_data_List))

    if day_num == 1:
        await update_folio()
        await update_redis()

async def main(loop):

    await orm.create_plug_pool(loop=loop, **configs.db)


def process_start(fun):

    loop=asyncio.get_event_loop()
    loop.run_until_complete(fun(loop))

def run_coin_all():

    from multiprocessing import Process
    funcList = [listen_coin_minute_task,
                listen_coin_day_task,
                listen_folio_24_hour_task]
    for fun in funcList:
        p = Process(target=process_start, args=[fun,])
        p.start()


if __name__ == '__main__':
    run_coin_all()

