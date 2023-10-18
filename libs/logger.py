#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tornado.log
import logging
import datetime
from tornado.options import options

options.log_file_prefix = os.path.join(os.path.dirname(os.path.dirname(__file__)), f'/tmp/codo.log')


class LogFormatter(tornado.log.LogFormatter):
    default_msec_format = '%s.%03d'

    def __init__(self):
        super(LogFormatter, self).__init__(
            fmt='%(color)s%(asctime)s | %(levelname)s%(end_color)s     | %(filename)s:%(funcName)s:%(lineno)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'
        )

    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.now()
        t = ct.strftime(self.default_time_format)
        s = self.default_msec_format % (t, record.msecs)
        return s


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
