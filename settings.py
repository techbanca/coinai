import os

root_path = os.path.dirname(os.path.abspath(__file__))

img_path = ""

module_list = ['portfolios', 'users', 'coins', "reports"]

timezone_local = ""

windows = {'M': [6, 12, 24, 36, 48, 60],
		   'W': [7, 14, 28, 56, 112, 224],
		   'D': [7, 30, 60, 90, 182, 365],
		   'B': [20, 30, 60, 90, 120, 250],
		   'H': [6, 12, 24, 48, 72, 144],
			'h': [6, 12, 24, 48, 72, 144]
		   }


choices = {
	"option_one": {0:1,1:2,2:3,3:4,4:5,5:4},
	"option_two":{0:1,1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9},
	"option_three":{0:1,1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9,9:11}
}

regime_val = {
	"Regime 0":"Bull/High Vol",
	"Regime 1":"Bull/Low Vol",
	"Regime 2":"Bear/High Vol",
	"Regime 3":"Bear/Low Vol",
	"Regime 4":"Concussion Market",
	"0":"Bull/High Vol",
	"1":"Bull/Low Vol",
	"2":"Bear/High Vol",
	"3":"Bear/Low Vol",
	"4":"Concussion Market"
}

hotCoins = ["Bitcoin", "Ethereum", "EOS", "XRP", "Banca"]

host = '0.0.0.0'
port = 6000

configs = {
	'debug' : True,
	'db' : {
		'host' : '',
		'port' : 3306,
		'user' : 'root',
		'password' : '',
		'db' : ''
	},
	'session' :{
		'secret' : 'Awesome'
	}
}


redis_conf = {"redis_servers":[('', 1396),
				 ],
			  "group":"",
			  "password":""
			  }

dynamoDB = {
    "region_name":"",
    "aws_access_key_id":"",
    "aws_secret_access_key":""
}
