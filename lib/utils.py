import datetime, time
import uuid
import traceback
import pytz,json
import hashlib

from io import StringIO
from aiohttp import web
from decimal import Decimal

from lib.language import message
from settings import timezone_local, hotCoins
from lib.redis import Redis
from logger.client import error, info, request_info


def _(key="", lang="en"):

    msg = message.get(lang,{}).get(key,"")
    return msg

def toExistLanguage(lang="en"):

    if lang in message:
        return lang
    else:
        return "en"

def request_uuid():
	return '%015d_request_uuid_%s' % (int(time.time() * 1000), uuid.uuid4().hex)

def getPerformanceList(perfor_data={}):

    if not isinstance(perfor_data, dict):
        return []

    perf_point = lambda d, p: {
                    'EffectiveDate': int(d),
                    'NetReturn': float(p)
                }
    dates = perfor_data.keys()
    rets = perfor_data.values()
    performance = [perf_point(d, p) for d, p in zip(dates, rets)]
    performance = sorted(performance, key=lambda x: x["EffectiveDate"], reverse=False)
    return performance

def hasVip(vipEndDate=""):
    if vipEndDate:
        nowDate = getUTCDate(False)
        isVip = True if int(vipEndDate) >= int(nowDate) else False
        return isVip
    return False

def getHexStrMode( hex_str, mode_num=2):

    result_mod = 0
    for idx, ch in enumerate(hex_str):
        result_mod = (result_mod*16 + int(ch, 16)) % mode_num
    return result_mod

def getIdMode(id_str="", mode_num=4):

    str_md5 = hashlib.md5(id_str.encode()).hexdigest()[0:16]
    md5_int = getHexStrMode(str_md5, mode_num=mode_num)
    return md5_int


def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

def getErrorMsg():
    fp = StringIO()
    traceback.print_exc(file=fp)
    message = fp.getvalue()
    today_date_str = str(datetime.datetime.now())
    msg = "time :%s , error : %s"%(today_date_str, str(message))
    return msg


async def token2user(token):
	if not token:
		return None
	try:
		redis_obj = Redis.getInstance()
		user = redis_obj.get(token)
		if user is None:
			return None
		user = json.loads(user.decode()) if not isinstance(user, dict) else user
		redis_obj.set_expire(token, 3600*24)
		return user
	except Exception as e:
		error("token2user exception is: %s"%str(e))
		return None


async def frequency(remote_ip, path_url):
    try:
        fast_rep = 0
        redis_obj = Redis.getInstance()
        data_val = redis_obj.getHash(remote_ip, path_url)
        try:
            data_val = json.loads(data_val.decode())
            val = data_val.get("now_time", "") if isinstance(data_val, dict) else data_val
            num = data_val.get("num", "") if isinstance(data_val, dict) else 1
            now_time = int(time.time() * 1000)
            pre_time = data_val.get("pre_time", "") if isinstance(data_val, dict) else now_time
        except:
            now_time = int(time.time() * 1000)
            pre_time = now_time
            val = ""
            num = 1

        request_info("frequency val:%s"%str(val))
        if not val:
            data = {"now_time": now_time, "num":1, "pre_time":now_time}
            redis_obj.setHash(remote_ip, path_url, json.dumps(data))
            redis_obj.setHashExpire(remote_ip, 3600)
        else:
            if now_time - int(val) < 200:
                fast_rep = 1
            if num >= 60 and now_time - pre_time <= 60000:
                fast_rep = 1
                num += 1
            elif now_time - pre_time > 60000:
                pre_time = now_time
                num = 1
            else:
                num += 1

            data = {"now_time": now_time, "num": num, "pre_time": pre_time}
            redis_obj.setHash(remote_ip, path_url, json.dumps(data))
            redis_obj.setHashExpire(remote_ip, 3600)
        return fast_rep
    except Exception as e:
        error("frequency exception is: %s"%str(e))
        return None

def __default(obj):

    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        raise TypeError('%r is not JSON serializable' % obj)

def to_response(r, m="", method="GET"):

    if isinstance(r, dict):
        resp = web.Response(
            body=json.dumps(r, ensure_ascii=False, default=__default).encode('utf-8'))
        content_type = "application/json;charset=utf-8"
    elif isinstance(r, bytes):
        resp = web.Response(body=r)
        content_type = 'application/octet-stream'
    else:
        if m:
            resp = web.Response(status=r, text=str(m))
        else:
            resp = web.Response(body=str(r).encode('utf-8'))
        content_type = 'text/html;charset=utf-8'
    info("to_response data is: %s"%str(r))
    resp.content_type = content_type
    resp.headers["X-Custom-Server-Header"] = "Custom data"
    resp.headers["ACCESS-CONTROL-ALLOW-ORIGIN"] = "*"
    resp.headers["ACCESS-CONTROL-ALLOW-METHODS"] = method
    resp.headers["ACCESS-CONTROL-MAX-AGE"] = "3600"
    resp.headers["ACCESS-CONTROL-ALLOW-HEADERS"] = "X-Client-Header, Referer, Accept, Origin, User-Agent, X-Requested-With, Content-Type, token"
    return resp


def toDecimal(b, style="0.00000"):

    return Decimal(b).quantize(Decimal(style))

def toPercent(value):

    return '%.3f%%' % (float(value) * 100)

def toRound(value, rate=8):
    if not value:
        return ""
    format = "%-."+str(rate)+"f"
    return format%float(value.replace("$",""))


def get_hotCoins():
    hotCoinList = hotCoins
    return hotCoinList


def toPreTimestamp(time_stamp, day_num=30, hour_num=0):

    if time_stamp:
        styleTime = datetime.datetime.utcfromtimestamp(int(time_stamp))
        if hour_num:
            preTime = styleTime - datetime.timedelta(hours=hour_num)
        else:
            preTime = styleTime - datetime.timedelta(days = day_num)
        time_stamp = int(time.mktime(preTime.timetuple()))
    return time_stamp


def toList(dataItems):
    data = []
    for item in dataItems:
        item = list(item)
        item[0] = item[0] if isinstance(item[0],list) else item[0].tolist()
        data.append(item)
    return data


def getUTCDate(toHour=True):
    today_date = datetime.datetime.now()
    current = datetime.datetime(today_date.year, today_date.month, today_date.day,
                                today_date.hour, today_date.minute, today_date.second)
    if timezone_local:
        tz = pytz.timezone(timezone_local)
        utc = pytz.utc
        current = tz.localize(current)
        if toHour:
            current_date = current.astimezone(utc).strftime('%Y%m%d%H')
        else:
            current_date = current.astimezone(utc).strftime('%Y%m%d')
    else:
        if toHour:
            current_date = current.strftime('%Y%m%d%H')
        else:
            current_date = current.strftime('%Y%m%d')

    return current_date
