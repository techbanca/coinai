# -*- coding:utf-8 -*-
'''

'''

import sys,os
import traceback
import uuid

current_path = os.path.realpath(__file__)
path = current_path.split("tools")[0]
sys.path.append(path)

from time import sleep
from lib.redis import Redis
from tools.plugScript.cron_job import config
from tools.plugScript.init_request_down import run_coin_all
from logger.client import error, info
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

def runCoinHour():

    redis_obj = Redis.getInstance()
    value = str(uuid.uuid4())
    val = redis_obj.cache_without_dogpiling("coin_hour", value=value)
    if value == str(val):
        try:
            run_coin_all(day_num=0)
        except Exception as e:
            error("runCoinHour error is %s" % str(e))
        finally:
            redis_obj.delete("coin_hour")

def runCoinDay():

    redis_obj = Redis.getInstance()
    value = str(uuid.uuid4())
    val = redis_obj.cache_without_dogpiling("coin_day", value=value)
    if value == str(val):
        try:
            run_coin_all(day_num=1)
        except Exception as e:
            error("runCoinDay error is %s" % str(e))
        finally:
            redis_obj.delete("coin_day")

def runCoinMinute():

    redis_obj = Redis.getInstance()
    value = str(uuid.uuid4())
    val = redis_obj.cache_without_dogpiling("coin_minute", value=value)
    if value == str(val):
        try:
            run_coin_all(day_num=-1)
        except Exception as e:
            error("runCoinMinute error is %s"%str(e))
        finally:
            redis_obj.delete("coin_minute")

def cronMain():

    scheduler_hour_time = config.scheduler_hour_time
    scheduler_day_time = config.scheduler_day_time
    scheduler_minute_time = config.scheduler_minute_time
    timezone_local = config.timezone_local
    job_defaults = {    
                    'coalesce': True,
                    'max_instances':2,
                    'misfire_grace_time':3600
                    }

    executors = {
                 'processpool': ThreadPoolExecutor(8),
                 'default': ProcessPoolExecutor(5)
                 }
    scheduler = BlockingScheduler(executors=executors, job_defaults=job_defaults)  ##, timezone=timezone_local

    scheduler.get_job("get_coinHour") or scheduler.add_job(runCoinHour, 'cron',
                                                                   month=scheduler_hour_time["month"],
                                                                   day=scheduler_hour_time["day"],
                                                                   hour=scheduler_hour_time["hour"],
                                                                   minute=scheduler_hour_time["minute"],
                                                                   second=scheduler_hour_time["second"],
                                                                   id="get_coinHour"
                                                                   )

    scheduler.get_job("get_coinDay") or scheduler.add_job(runCoinDay, 'cron',
                                                          month=scheduler_day_time["month"],
                                                          day=scheduler_day_time["day"],
                                                          hour=scheduler_day_time["hour"],
                                                          minute=scheduler_day_time["minute"],
                                                          second=scheduler_day_time["second"],
                                                           id="get_coinDay"
                                                           )

    scheduler.get_job("get_coinMinute") or scheduler.add_job(runCoinMinute, 'cron',
                                                          month=scheduler_minute_time["month"],
                                                          day=scheduler_minute_time["day"],
                                                          hour=scheduler_minute_time["hour"],
                                                          minute=scheduler_minute_time["minute"],
                                                          second=scheduler_minute_time["second"],
                                                          id="get_coinMinute"
                                                          )

    try:
        scheduler.start()
        info("cron coin is starting..")
        sleep(2)
    except Exception as e:
        error("Collecter cronMain exception : {0} ".format(traceback.format_exc()))
        scheduler.shutdown()

if __name__ == '__main__':

    cronMain()
