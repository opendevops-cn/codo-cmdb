#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: startup.py
@time: 18/11/26上午9:44
'''
import tornado.web
import tornado.wsgi
from tornado.options import define
import os
import fire
from apps.ws.handler import ws_urls
from ops.settings import DEBUG
from libs.tornado_libs.application import Application as myapplication
from django.core.wsgi import get_wsgi_application
os.environ['DJANGO_SETTINGS_MODULE'] = 'ops.settings'

class Application(myapplication):
    def __init__(self,**settings):
        wsgi_app = get_wsgi_application()
        container = tornado.wsgi.WSGIContainer(wsgi_app)
        urls = []
        #urls.extend(ws_urls)
        urls.extend([
            ("/static/(.*)", tornado.web.StaticFileHandler,dict(path=os.path.join(os.path.dirname(__file__), "static"))),
            ('.*', tornado.web.FallbackHandler, dict(fallback=container))
        ])
        super(Application,self).__init__(urls,**settings)

class WsApplication(myapplication):
    def __init__(self,**settings):
        urls = []
        urls.extend(ws_urls)
        super(WsApplication,self).__init__(urls,**settings)

define("service", default='api', help="start service flag", type=str)
settings = {'debug' : DEBUG}

class My():
    def __init__(self,service):
        if service == 'cmdb':
            self.app = Application(**settings)
        elif service == 'ws':
            self.app = WsApplication(**settings)
        self.app.start_server()

if __name__ == '__main__':
    fire.Fire(My)