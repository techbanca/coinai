
root_path = ""

module_list = ['portfolios', 'users']

windows = {'M': [12, 24, 36, 48, 60],
			'W': [13, 26, 52, 104],
			'D': [20, 60, 90, 182, 365],
			'B': [20, 60, 90, 120, 250]
			}

host = '127.0.0.1'
port = 6000

timezone_local = ""

configs = {
	'debug' : True,
	'db' : {
		'host' : '127.0.0.1',
		'port' : 3306,
		'user' : 'www-data',
		'password' : 'www-data',
		'db' : 'awesome'
	},
	'session' :{
		'secret' : 'Awesome'
	}
}

redis_servers = []

dynamoDB = {
    "region_name":"",
    "aws_access_key_id":"",
    "aws_secret_access_key":""
}
