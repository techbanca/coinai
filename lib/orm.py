import aiomysql

from decimal import Decimal
from lib.utils import getErrorMsg
from logger.client import info, error

__pool = None

def log(sql, args=()):
    info('SQL: %s' % sql)

async def create_plug_pool(loop, **kw):
	global __pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host', '127.0.0.1'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 5),
		minsize = kw.get('minsize', 1),
		loop = loop
		
		)


async def create_pool(loop, **kw):
	global __pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host', '127.0.0.1'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 300),
		minsize = kw.get('minsize', 50),
		loop = loop
		)


async def select(sql, args, size=None):
	global __pool
	with (await __pool) as conn:
		cur = await conn.cursor(aiomysql.DictCursor)
		await cur.execute(sql.replace('?', '%s'), args)
		if size:
			rs = await cur.fetchmany(size)
		else:
			rs = await cur.fetchall()

		await cur.close()
		return rs

async def execute(sql, args):

	global __pool
	with (await __pool) as conn:
		try:
			cur = await conn.cursor()
			await cur.execute(sql.replace('?', '%s'), args or ())
			affected = cur.rowcount
			await cur.close()
		except BaseException as e:
			error("execute Exception is -------------------> : %s,  sql is %s, args is %s"%(str(e), str(sql), str(args)))
			raise
		return affected

def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ', '.join(L)


class Field(object):

	def __init__(self, name, column_type,  primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
	def __init__(self, name = None, default = False):
		super().__init__(name, 'boolern', False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetalclass(type):
	def __new__(cls, name, bases, attrs):

		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)

		tableName = attrs.get('__table__', None) or name
		mappings = dict()
		fields = []
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				mappings[k] = v
				if v.primary_key:
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field:%s' % k)
					primaryKey = k
				else:
					fields.append(k)

		if not primaryKey:
			raise RuntimeError('Primary key not found')

		for k in mappings.keys():
			attrs.pop(k)

		escaped_fields = list(map(lambda f : '`%s`' % f, fields))
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey
		attrs['__fields__'] = fields
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass = ModelMetalclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value
		
	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				setattr(self, key, value)
		return value

	def json(self):
		d = {}
		for c in self.__fields__:
			d[c] = getattr(self, c)
			if isinstance(d[c],float):
				d[c] = Decimal(d[c]).quantize(Decimal('0.000000000'))
		return d

	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		try:
			sql = [cls.__select__]
			if where:
				sql.append('where')
				sql.append(where)
			if args is None:
				args = []
			orderBy = kw.get('orderBy', None)
			if orderBy:
				sql.append('order by')
				sql.append(orderBy)
			limit = kw.get('limit', None)
			if limit is not None:
				sql.append('limit')
				if isinstance(limit, int):
					sql.append('?')
					args.append(limit)
				elif isinstance(limit, tuple) and len(limit) == 2:
					sql.append('?, ?')
					args.extend(limit)
				else:
					raise ValueError('Invalid limit value: %s' % str(limit))

			rs = await select(' '.join(sql), args)
			return [cls(**r) for r in rs]
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm findAll error is: %s, kw is %s, where is %s, args is %s" % (
					str(errMsg),
					str(kw),
					str(where),
					str(args))
				  )
			return []

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		try:
			sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
			if where:
				sql.append('where')
				sql.append(where)
			rs = await select(' '.join(sql), args, 1)
			if len(rs) == 0:
				return None
			return rs[0]['_num_']
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm findNumber error is: %s, selectField is %s, where is %s, args is %s" % (
					str(errMsg),
					str(selectField),
					str(where),
					str(args))
				  )
			return None


	@classmethod
	async def find(cls, pk):
		'find object by primary key'
		try:
			rs = await select('%s where `%s`= ?' % (cls.__select__, cls.__primary_key__), [pk], 1)
			if len(rs) == 0:
				return None
			return cls(**rs[0])
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm find error is: %s, pk is %s" % (str(errMsg),str(pk)))
			return None


	async def save(self):
		try:
			args = list(map(self.getValueOrDefault, self.__fields__))
			args.append(self.getValueOrDefault(self.__primary_key__))
			rows  = await execute(self.__insert__, args)
			if rows != 1:
				error('failed to insert record: affected rows :%s, args : %s' % (rows, str(args)))
			return rows
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm save error is: %s" % (errMsg))
			return None

	async def update(self):
		try:
			args = list(map(self.getValue, self.__fields__))
			args.append(self.getValue(self.__primary_key__))
			rows = await execute(self.__update__, args)
			if rows != 1:
				error('failed to update by primary key: affected rows: %s, args : %s' % (rows, str(args)))
			return rows
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm update error is: %s" % (errMsg))
			return None


	async def remove(self):
		try:
			args = [self.getValue(self.__primary_key__)]
			rows = await execute(self.__delete__, args)
			if rows != 1:
				error('failed to remove by primary key: affected rows: %s, args : %s' % (rows, str(args)))
			return rows
		except Exception as e:
			errMsg = getErrorMsg()
			error("orm remove error is: %s" % (errMsg))
			return None
