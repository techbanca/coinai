# !/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import logging.handlers

from functools import partial

coinai_trace = 'coin_ai.tracelog'

coinai_log = 'coin_ai.log'

coinai_collect_log = 'coin_ai_collect.log'

coinai_request_log = 'coin_ai_request.log'

coinai_debug_log = 'coin_ai_debug.log'

logging_dir = "/var/log/coin_ai"

class _SysLogger(object):

    __instance = None

    def __init__(self):

        self.coinai_trace_logger = logging.getLogger(coinai_trace)
        self.coinai_trace_logger.setLevel(logging.ERROR)
        self.addHandler(self.coinai_trace_logger,coinai_trace)

        self.coinai_logger = logging.getLogger(coinai_log)
        self.coinai_logger.setLevel(logging.INFO)
        self.addHandler(self.coinai_logger, coinai_log)

        self.coinai_collect_logger = logging.getLogger(coinai_collect_log)
        self.coinai_collect_logger.setLevel(logging.INFO)
        self.addHandler(self.coinai_collect_logger, coinai_collect_log)

        self.coinai_request_logger = logging.getLogger(coinai_request_log)
        self.coinai_request_logger.setLevel(logging.INFO)
        self.addHandler(self.coinai_request_logger, coinai_request_log)

        self.coinai_debug_logger = logging.getLogger(coinai_debug_log)
        self.coinai_debug_logger.setLevel(logging.DEBUG)
        self.addHandler(self.coinai_debug_logger, coinai_debug_log)

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = _SysLogger()
        return cls.__instance

    def addHandler(self, logger, filename):

        formatter = logging.Formatter('%(name)-12s %(asctime)s %(levelname)-8s %(message)s', '%a, %d %b %Y %H:%M:%S', )
        logFile = os.path.join(logging_dir, filename)
        if not os.path.exists(logFile):
            os.system("sudo touch %s"%str(logFile))
        file_handler = logging.FileHandler(logFile)
        file_size_handler = logging.handlers.RotatingFileHandler(logFile, maxBytes=1024 * 1024 * 100, backupCount=10)
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stderr)
        logger.addHandler(file_handler)
        logger.addHandler(file_size_handler)
        logger.addHandler(stream_handler)

    def error(self):
        """
        logging error message
        """

        return partial(self.coinai_trace_logger.error)

    def info(self):
        """
        logging debug message
        """
        return partial(self.coinai_logger.info)

    def request_info(self):
        """
        logging debug message
        """
        return partial(self.coinai_request_logger.info)

    def debug_info(self):
        """
        logging debug message
        """
        return partial(self.coinai_debug_logger.debug)

    def collect_info(self):
        """
        logging collect info message
        """
        return partial(self.coinai_collect_logger.info)


SysLogger = _SysLogger.getInstance()

error = SysLogger.error()

info = SysLogger.info()

request_info = SysLogger.request_info()

debug_info = SysLogger.debug_info()

collect_info = SysLogger.collect_info()
