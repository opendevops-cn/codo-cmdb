#!/usr/bin/env python
# -*-coding:utf-8-*-
'''
Author : ss
date   : 2018-3-19
role   : web  log
'''

import logging
import os
import time
from shortuuid import uuid

log_fmt = ''.join(('PROGRESS:%(progress_id) -5s %(levelname) ', '-10s %(asctime)s %(name) -25s %(funcName) '
                                                                '-30s LINE.NO:%(lineno) -5d : %(message)s'))
log_key = 'logger_key'


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


class ProgressLogFilter(logging.Filter):
    def filter(self, record):
        record.progress_id = Logger().progress_id
        return True


@singleton
class Logger(object):
    def __init__(self, progress_id='', log_file='/tmp/xxx.log'):
        self.__log_key = log_key
        self.progress_id = progress_id
        self.log_file = log_file

    def read_log(self, log_level, log_message):
        ###创建一个logger
        if self.progress_id == '':
            Logger().progress_id = str(uuid())
        else:
            Logger().progress_id = self.progress_id
        logger = logging.getLogger(self.__log_key)
        logger.addFilter(ProgressLogFilter())
        logger.setLevel(logging.DEBUG)

        ###创建一个handler用于输出到终端
        th = logging.StreamHandler()
        th.setLevel(logging.DEBUG)

        ###定义handler的输出格式
        formatter = logging.Formatter(log_fmt)
        th.setFormatter(formatter)

        ###给logger添加handler
        logger.addHandler(th)

        ###记录日志
        level_dic = {'debug': logger.debug, 'info': logger.info, 'warning': logger.warning, 'error': logger.error,
                     'critical': logger.critical}
        level_dic[log_level](log_message)

        th.flush()
        logger.removeHandler(th)

    def write_log(self, log_level, log_message):
        ###创建一个logger
        ###创建一个logger
        if self.progress_id == '':
            Logger().progress_id = str(uuid())
        else:
            Logger().progress_id = self.progress_id
        logger = logging.getLogger(self.__log_key)
        logger.addFilter(ProgressLogFilter())
        logger.setLevel(logging.DEBUG)

        ###建立日志目录
        log_dir = os.path.dirname(self.log_file)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        ###创建一个handler用于写入日志文件
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)

        ###定义handler的输出格式
        formatter = logging.Formatter(log_fmt)
        fh.setFormatter(formatter)

        ###给logger添加handler
        logger.addHandler(fh)

        ###记录日志
        level_dic = {'debug': logger.debug, 'info': logger.info, 'warning': logger.warning, 'error': logger.error,
                     'critical': logger.critical}
        level_dic[log_level](log_message)

        ###删除重复记录
        fh.flush()
        logger.removeHandler(fh)


ins_log = Logger()


def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        ins_log.read_log('info', '%s execute duration :%.3f second' % (str(func), duration))
        return result

    return wrapper


# ins_log.write_log('info', 'xxxx')
#ins_log.read_log('info', 'xxxx')