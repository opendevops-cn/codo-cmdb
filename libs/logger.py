#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : logger.py
# @Author: 
# @Date  : 2022/3/28
# @Role  :


import os
import sys
import tornado.log
import logging
from tornado.options import options

options.log_file_prefix = os.path.join(os.path.dirname(os.path.dirname(__file__)), f'log/cmdb.log')


class LogFormatter(tornado.log.LogFormatter):
    def __init__(self):
        super(LogFormatter, self).__init__(
            fmt=f'LOG_%(levelname)s %(asctime)s %(filename)s:%(funcName)s %(lineno)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )


def init_logging():
    # write file
    [
        i.setFormatter(LogFormatter())
        for i in logging.getLogger().handlers
    ]
    logging.getLogger().setLevel(logging.INFO)
    # write stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(LogFormatter())
    logging.getLogger().addHandler(stdout_handler)
    logging.info('[Logging Init] logging has been started')
