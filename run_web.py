# -*- coding: utf-8 -*-

import asyncio
import json, sys
import os
import uvloop

from aiohttp import web
from lib import orm
from lib.config import configs
from lib.baseweb import add_routes, add_static
from lib.factory import logger_factory, response_factory
from lib.redis import Redis
from logger.client import info
from settings import module_list, host, root_path

async def init_db(loop):
	await orm.create_pool(loop=loop, **configs.db)
	redis_obj = Redis.getInstance()
	data_path = os.path.join(root_path, "data/dbData/data.json")
	
	with open(data_path,"r") as load_f:
		load_data = json.load(load_f)
		hotCoins = load_data.get("hotCoins")
		update_report = load_data.get("update_report")
		
	redis_obj.set("hotCoins", json.dumps(hotCoins))
	redis_obj.set("update_report", json.dumps(update_report))


async def init(loop, init_port=6000):

	await init_db(loop)
	app = web.Application(loop=loop, middlewares=[
		logger_factory, response_factory
	])
	add_routes(app, module_list=module_list)
	add_static(app)
	srv = await loop.create_server(app.make_handler(), host, init_port)
	info('server started at http://%s:%s...'%(host, init_port))
	return srv

if __name__ == '__main__':

	params = sys.argv
	init_port = int(params[1]) if len(params) > 1 else 5000
	asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
	
	loop = asyncio.get_event_loop()
	loop.run_until_complete(init(loop, init_port))
	loop.run_forever()
