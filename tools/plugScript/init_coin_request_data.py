import asyncio, aiohttp
import codecs, os, sys, re
import contextlib
import datetime
import time, json

from bs4 import BeautifulSoup

current_path = os.path.realpath(__file__)
root_path = current_path.split("tools")[0]
sys.path.append(root_path)

from coin_application.coins.models import Coin, Performance
from lib import orm
from lib.config import configs

ticker_url = "https://api.coinmarketcap.com/v2/ticker/?start=%d&limit=100"
detail_url = 'https://coinmarketcap.com/currencies/%s/'

url = "https://min-api.cryptocompare.com/data/price?fsym=%s&tsyms=BTC,USD,EUR"
url_list = []
output_path = current_path.split("plugScript")[0] + "plugScript/data/coin_url/"


async def get_coin_url():

    urls = {}
    objs = await Coin.findAll()
    for coin in objs:
        coin_name = coin.simple_name.upper()
        urls[coin.id] = {"url":url%coin_name, "simple_name": coin.simple_name.upper()}
    return urls


async def fetch_async(url, session, toJson=True):
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


async def down_paraser_item(pre_item={}, session=None):
    """
    :param pre_item:
    {
            "id": 1720,
            "name": "IOTA",
            "symbol": "MIOTA",
            "website_slug": "iota",
            "rank": 9,
            "circulating_supply": 2779530283.0,
            "total_supply": 2779530283.0,
            "max_supply": 2779530283.0,
            "quotes": {
                "USD": {
                    "price": 1.78076,
                    "volume_24h": 48953000.0,
                    "market_cap": 4949676347.0,
                    "percent_change_1h": 0.21,
                    "percent_change_24h": 2.9,
                    "percent_change_7d": -6.25
                }
            },
            "last_updated": 1526808251
        }
    """

    modify_at = float(pre_item.get("last_updated", time.time()))
    usd = pre_item.get("quotes",{}).get("USD",{})
    bitcoin_name = pre_item.get("name","")
    simple_name = pre_item.get("symbol","")
    website_slug = pre_item.get("website_slug","")
    rank = pre_item.get("rank","")
    market_cap = usd.get("market_cap","")
    price = usd.get("price","")
    supply_pvolume = pre_item.get("circulating_supply","")
    trading_24_volume = usd.get("volume_24h","?")
    hours_1_index = usd.get("percent_change_1h","?")
    hours_24_index = usd.get("percent_change_24h","?")
    
    day_7_index = usd.get("percent_change_7d","?")

    detailUrl = detail_url % website_slug
    content_data = await fetch_async(detailUrl, session, False)
    soup_detail = BeautifulSoup(content_data, 'html.parser')

    span_price_rates = soup_detail.find_all(name="span", attrs={"class": re.compile("(text-large2)|(negative_change)")})
    span_price_rates_len = len(span_price_rates)
    if span_price_rates_len > 1:
        span_price_rate = span_price_rates[1]
        span_price_rate = span_price_rate.find_all(name="span")[0]
    else:
        span_price_rate = span_price_rates[0]

    span_price_btc = soup_detail.find_all(name="span", attrs={"class": "text-gray details-text-medium"})[0]
    span_price_btc = span_price_btc.find_all(name="span")[0]
    try:
        span_price_btc_rates = soup_detail.find_all(name="span", attrs={"class": re.compile("(details-text-medium)|(negative_change)")})
        span_price_btc_rate = span_price_btc_rates[-1] if "%)" in str(span_price_btc_rates) else ""
        span_price_btc_rate = span_price_btc_rate.find_all(name="span")[0] if span_price_btc_rate else ""
    except Exception as e:
        span_price_btc_rate = None

    div_items = soup_detail.find_all(name="div", attrs={"class": "coin-summary-item col-xs-6 col-md-3"})
    div_trading_24_btc_volume = div_items[1].find_all(name="div", attrs={"class": "coin-summary-item-detail details-text-medium"})[0]
    span_trading_24_btc_volume = div_trading_24_btc_volume.find_all(name="span")[1]

    price_rate = span_price_rate.text
    price_btc = span_price_btc.text.strip("\n")
    price_btc_rate = span_price_btc_rate.text if span_price_btc_rate else ""
    trading_24_btc_volume = span_trading_24_btc_volume.text

    objs = await Coin.findAll(where="name=?", args=[bitcoin_name])
    if objs:
        coin = objs[0]
        if span_price_rates_len == 1:
            pre_price = coin.pre_price.replace(",","").replace("$","")
            now_price = price_rate.replace(",", "").replace("$", "")
            price_rate = str(round(100*(float(now_price) - float(pre_price))/float(pre_price),5))
        if not price_btc_rate:
            pre_price_btc = float(coin.pre_price_btc.replace(",","").replace("$",""))
            now_price_btc = float(price_btc.replace(",","").replace("$",""))
            price_btc_rate = str(round(100*(float(now_price_btc) - float(pre_price_btc))/float(pre_price_btc),5))

        coin.market_cap = market_cap.strip("\n") if isinstance(market_cap, str) else market_cap
        coin.pre_price = coin.price
        coin.price = price.strip("\n") if isinstance(price, str) else price
        coin.supply_pvolume = supply_pvolume.split("*")[0].strip("\n") if isinstance(supply_pvolume, str) else supply_pvolume
        coin.trading_24_volume = trading_24_volume.strip("\n") if isinstance(trading_24_volume, str) else (trading_24_volume if trading_24_volume else "?")
        coin.hours_1_index = hours_1_index.strip("\n") if isinstance(hours_1_index, str) else (hours_1_index if hours_1_index else "?")
        coin.hours_24_index = hours_24_index.strip("\n") if isinstance(hours_24_index, str) else (hours_24_index if hours_24_index else "?")
        coin.day_7_index = day_7_index.strip("\n") if isinstance(day_7_index, str) else (day_7_index if day_7_index else "?")
        coin.price_rate = price_rate.strip("\n") if isinstance(price_rate, str) else price_rate
        coin.pre_price_btc = coin.price_btc
        coin.price_btc = price_btc.strip("\n") if isinstance(price_btc, str) else price_btc
        coin.price_btc_rate = price_btc_rate.strip("\n") if isinstance(price_btc_rate, str) else price_btc_rate
        coin.trading_24_btc_volume = trading_24_btc_volume.strip("\n") if isinstance(trading_24_btc_volume, str) else trading_24_btc_volume
        coin.modify_at = modify_at
        await coin.update()
    else:
        market_cap = market_cap.strip("\n") if isinstance(market_cap, str) else market_cap
        price = price.strip("\n") if isinstance(price, str) else price
        supply_pvolume = supply_pvolume.split("*")[0].strip("\n") if isinstance(supply_pvolume, str) else supply_pvolume
        trading_24_volume = trading_24_volume.strip("\n") if isinstance(trading_24_volume,str) else (trading_24_volume if trading_24_volume else "?")
        hours_1_index = hours_1_index.strip("\n") if isinstance(hours_1_index, str) else (hours_1_index if hours_1_index else "?")
        hours_24_index = hours_24_index.strip("\n") if isinstance(hours_24_index, str) else (hours_24_index if hours_24_index else "?")
        day_7_index = day_7_index.strip("\n") if isinstance(day_7_index, str) else (day_7_index if day_7_index else "?")
        price_rate = price_rate.strip("\n") if isinstance(price_rate, str) and span_price_rates_len != 1 else "0"
        price_btc = price_btc.strip("\n") if isinstance(price_btc, str) else price_btc
        price_btc_rate = price_btc_rate.strip("\n") if price_btc_rate and isinstance(price_btc_rate, str) else "0"
        trading_24_btc_volume = trading_24_btc_volume.strip("\n") if isinstance(trading_24_btc_volume,str) else trading_24_btc_volume
        coin = Coin(name=bitcoin_name, simple_name=simple_name.upper(), market_cap=market_cap, price=price, supply_pvolume=supply_pvolume,
                trading_24_volume=trading_24_volume, hours_1_index=hours_1_index, hours_24_index=hours_24_index, pre_price=price,
                day_7_index=day_7_index, price_rate=price_rate, price_btc=price_btc, pre_price_btc=price_btc, price_btc_rate=price_btc_rate,
                trading_24_btc_volume=trading_24_btc_volume, modify_at = modify_at, create_at=float(time.time()))
        await coin.save()


async def main(loop):

    await orm.create_plug_pool(loop=loop, **configs.db)
    urls = await get_coin_url()
    session = aiohttp.ClientSession()
    data_lists = []
    for num in range(10):
        result_data = await fetch_async(ticker_url%(num*100+1), session)
        if result_data:
            data_list = result_data["data"].values()
            data_lists.extend(data_list)

    data_dicts = {str(val["symbol"]) : val  for val in data_lists}
    for key, value in urls.items():
        simple_name = str(value.get("simple_name",""))
        if simple_name in data_dicts:
            item_dict = data_dicts[simple_name]
        else:
            item_dict = {}
        if not item_dict:
            continue
        await down_paraser_item(item_dict, session)

        usd = item_dict.get("quotes", {}).get("USD", {})
        effective_time = float(item_dict.get("last_updated", time.time()))
        pre_close_value = ""
        close_value = usd.get("price","")
        res_per = await Performance.findAll(where="coin_id = ? and effective_date < ?",
                                                    args=[key, effective_time], orderBy='effective_date desc')
        if res_per:
            res_per = res_per[0]
            pre_close_value = res_per.close_value
        else:
            obj = await Coin.find(key)
            if obj:
                pre_close_value = float(obj.price.replace("$","").replace(",",""))
        if pre_close_value:
            net_return = float(float(close_value) - float(pre_close_value)) / float(pre_close_value)
        else:
            continue
        res = await Performance.findNumber("count(id)", where="coin_id=? and effective_date=?",
                                                args=[key, effective_time])
        if res:
            continue
        perfor = Performance(coin_id=key, close_value=close_value,
                             net_return=net_return, effective_date=effective_time)
        await perfor.save()

    today_date = datetime.datetime.now()
    current = datetime.datetime(today_date.year, today_date.month, today_date.day,
                                today_date.hour, today_date.minute, today_date.second)
    current_date = current.strftime('%Y%m%d_%H')
    fileName = "coin_day_url_" + current_date
    file = open('%s.txt' % fileName, 'w', encoding='utf-8')
    file.write(str(url_list))

def run_coin_day():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

if __name__ == '__main__':
    run_coin_day()

