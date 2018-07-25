import asyncio
import functools
import inspect
import os
import aiohttp_cors

from urllib import parse
from lib.utils import to_response, token2user, getErrorMsg, frequency, hasVip, request_uuid, _, toExistLanguage
from logger.client import error, request_info
from settings import root_path

def get(path, auth=True):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			try:
				return func(*args, **kw)
			except Exception as e:
				errMsg = getErrorMsg()
				error("get api error is: %s" % str(errMsg))
				result = {"error": 500, "data": "", "message": _("500_SERVER_ERROR", kw.get("language","en"))}
				return result
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		wrapper.__auth__ = auth
		return wrapper
	return decorator


def post(path, auth=True):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			try:
				return func(*args, **kw)
			except Exception as e:
				errMsg = getErrorMsg()
				error("post api error is: %s" % str(errMsg))
				result = {"error": 500, "data": "", "message": _("500_SERVER_ERROR", kw.get("language","en"))}
				return result
		wrapper.__method__ = 'POST'
		
		wrapper.__route__ = path
		wrapper.__auth__ = auth
		return wrapper
	return decorator


def options(path, auth=True):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			try:
				return func(*args, **kw)
			except Exception as e:
				errMsg = getErrorMsg()
				error("options api error is: %s"%str(errMsg))
				result = {"error": 500, "data": "", "message": _("500_SERVER_ERROR", kw.get("language","en"))}
				return result
		wrapper.__method__ = 'OPTIONS'
		wrapper.__route__ = path
		wrapper.__auth__ = auth
		return wrapper
	return decorator

def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)	
	return tuple(args)

def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	args.extend(["token", "language"])
	return tuple(args)

def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

def has_request_arg(fn):
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
	return found

class RequestHandler(object):
	"""docstring for RequestHandler"""

	def __init__(self, app, fn, auth=False):
		self._app = app
		self._func = fn
		self._auth = auth
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_arg = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	async def getToken(self, request, kw):
		token = kw.get("token", "")
		language = toExistLanguage(kw.get("language", "en"))
		if token:
			user = await token2user(token)
			if user:
				request.__user__ = user
				vipEndDate = user.get("vipEndDate", "")
				read = hasVip(vipEndDate)
				request.__user__["read"] = read
				request.__user__["request_uuid"] = request_uuid()
				request.__user__["language"] = language
			else:
				if self._auth:
					r = {"error": 403, "data": {}, "message": _("403_LOGIN",language)}
					resp = to_response(r)
					return resp
				else:
					request.__user__ = {}
					request.__user__["language"] = language
		else:
			if self._auth:
				r = {"error": 403, "data": {}, "message": _("403_LOGIN",language)}
				resp = to_response(r)
				return resp
			else:
				request.__user__ = {}
				request.__user__["language"] = language

		return True


	async def request_frequency(self, request, kw):
		remote_ip = request.remote
		path_url = request.path
		language = toExistLanguage(kw.get("language", "en"))
		res = await frequency(remote_ip, path_url)
		if res:
			r = {"error": 416, "data": {}, "message": _("416_REQ_FREQUENT", language)}
			resp = to_response(r)
			return resp
		else:
			return True

	@asyncio.coroutine
	def  __call__(self, request):

		kw = None
		if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args or self._named_kw_args:
			if request.method in ('POST',"OPTIONS"):
				if not request.content_type:
					r = {"error": 404, "data": {}, "message": 'Missing Content-Type'}
					resp = to_response(r, method=request.method)
					return resp

				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						r = {"error": 404, "data": {}, "message": 'JSON Body must be object'}
						resp = to_response(r, method=request.method)
						return resp
					kw = params

				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = yield from request.post()
					kw = dict(**params)
				else:
					r = {"error": 404, "data": {}, "message": 'Unsupported Content-Type:%s' % request.content_type}
					resp = to_response(r, method=request.method)
					return resp

			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]

		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				copy =  dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			for k, v in request.match_info.items():
				if k in kw:
					error('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v

		if self._has_request_arg:
			kw['request'] = request

		language = toExistLanguage(kw.get("language", "en"))
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					r = {"error": 500, "data": {}, "message": _("500_SERVER_ERROR", language)}
					resp = to_response(r, method=request.method)
					return resp

		request_info('call with args: %s' % str(kw))
		try:
			res = yield from self.request_frequency(request, kw)
			if res == True:
				resp = yield from self.getToken(request, kw)
				if resp == True:
					if "token" in kw:
						del kw["token"]
					if "language" in kw:
						del kw["language"]
					r = yield from self._func(**kw)
					return r
				else:
					return resp
			else:
				return res
		except Exception as e:
			errMsg = getErrorMsg()
			error("__call__ api error is: %s"%str(errMsg))
			r = {"error": 500, "data": {}, "message": _("500_SERVER_ERROR", language)}
			resp = to_response(r, method=request.method)
			return resp

def add_static(app):
	path = os.path.join(root_path, 'static')
	app.router.add_static('/static/', path)

def add_route(app, fn, cors):
	method = getattr(fn, '__method__', None)
	_auth = getattr(fn, '__auth__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))

	if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)

	# Enable CORS on routes.
	handler = RequestHandler(app, fn, auth=_auth)
	app.router.add_route(method, path, handler)

def add_routes(app, module_list=[]):

	cors = aiohttp_cors.setup(app, defaults={
		"*": aiohttp_cors.ResourceOptions(allow_credentials=True,
										  expose_headers="*",
										  allow_headers="*",
										  max_age=3600,
										  allow_methods=("GET","POST")),
	})

	for module in module_list:
		mod = __import__("coin_application.%s.handlers"%module, globals(), locals(), fromlist = (module,))
		for attr in dir(mod):
			if attr.startswith('_'):
				continue
			fn = getattr(mod, attr)
			if callable(fn):
				method = getattr(fn, '__method__', None)
				path = getattr(fn, '__route__', None)
				if method and path:
					add_route(app, fn, cors)
