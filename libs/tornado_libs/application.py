#!/usr/bin/env python
#encoding:utf-8
'''
Author : ming
date   : 2018年1月12日13:43:27
role   : 定制 Application
'''
from shortuuid import uuid
from tornado import httpserver, ioloop
from tornado import options as tnd_options
from tornado.options import options, define
from tornado.web import Application as tornado_app
from libs.tornado_libs.web_logs import Logger, ins_log
from ops.settings import IP, PORT

define("port", default=PORT, help="run on the given port", type=int)
define("host", default=IP, help="run port on given host", type=str)
define("progid", default=str(uuid()), help="tornado progress id", type=str)

class Application(tornado_app):
    """ 定制 Tornado Application 集成日志 功能 """
    def __init__(self, handlers=None, default_host="",
                 transforms=None, **settings):
        tnd_options.parse_command_line()    #打印infor日志
        Logger(options.progid)
        super(Application, self).__init__(handlers, default_host,transforms, **settings)
        http_server = httpserver.HTTPServer(self)
        http_server.listen(options.port, address=options.host)
        self.io_loop = ioloop.IOLoop.instance()
    def start_server(self):
        """
        启动 tornado 服务
        :return:
        """
        try:
            ins_log.read_log('info', 'progressid: %(progid)s' % dict(progid=options.progid))
            ins_log.read_log('info', 'server address: %(addr)s:%(port)s' % dict(addr=options.host, port=options.port))
            ins_log.read_log('info', 'web server start sucessfuled.')
            self.io_loop.start()
        except KeyboardInterrupt:
            self.io_loop.stop()
        except:
            import traceback
            ins_log.read_log('error', '%(tra)s'% dict(tra=traceback.format_exc()))
            #Logger.error(traceback.format_exc())

if __name__ == '__main__':
    pass