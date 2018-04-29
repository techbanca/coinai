# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import multiprocessing

debug = True
loglevel = 'debug'
bind = '0.0.0.0:1974'
pidfile = 'logfiles/gunicorn.pid'
logfile = 'logfiles/debug.log'

#start process number
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gunicorn.workers.ggevent.GeventWorker'

x_forwarded_for_header = 'X-FORWARDED-FOR'