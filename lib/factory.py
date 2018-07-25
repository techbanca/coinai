import os
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from lib.utils import to_response
from logger.client import request_info
from settings import root_path

def init_jinja2(app, **kw):

	options = dict(
		autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string', '}}'),
		auto_reload = kw.get('auto_reload', True)
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(root_path, 'templates')
	env = Environment(loader=FileSystemLoader(path), **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env


async def logger_factory(app, handler):

	async def logger(request):
		request_info('Requst-------> remote: %s,  method:%s,  path: %s' % (str(request.remote), request.method, request.path))
		return (await handler(request))
	return logger


async def data_factory(app, handler):

	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
		return (await handler(request))
	return parse_data

async def response_factory(app, handler):

	async def response(request):
		request.__user__ = {}
		r = await handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		
		if isinstance(r, bytes):
			return to_response(r)
		if isinstance(r, str):
			return to_response(r)
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				return to_response(r)
			else:
				r['__user__'] = request.__user__
				body=app['__templating__'].get_template(template).render(**r)
				return to_response(body, content_type = 'text/html;charset=utf-8')
		if isinstance(r, int) and r >= 100 and r < 600:
			return to_response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return to_response(t, m)
			return to_response(r)
	return response
