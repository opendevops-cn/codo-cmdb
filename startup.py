#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Date  : 2023/2/25
Desc  : 启动脚本
"""

import fire
from tornado.options import define
from websdk2.program import MainProgram
from settings import settings as app_settings
from cmdb.applications import Application as CmdbApp
from libs.registration import Registration

define("service", default='cmdb', help="start service flag", type=str)


class MyProgram(MainProgram):
    def __init__(self, service='cmdb', progressid=''):
        self.__app = None
        settings = app_settings
        if service == 'cmdb':
            self.__app = CmdbApp(**settings)
        elif service in ['init']:
            self.__app = Registration(**settings)
        super(MyProgram, self).__init__(progressid)
        self.__app.start_server()


if __name__ == '__main__':
    fire.Fire(MyProgram)

# python3 startup.py --service=init
# python3 db_sync.py
# python3 startup.py --service=cmdb --port=8899
