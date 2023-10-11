#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2017-01-01
role   : Application
"""

import logging
from abc import ABC
from tornado.options import options
from tornado.ioloop import PeriodicCallback
from concurrent.futures import ThreadPoolExecutor
from websdk2.application import Application as myApplication
from libs.logger import init_logging
from libs.scheduler import scheduler, init_scheduler
from cmdb.handlers import urls
from domain.handlers import urls as domain_urls
from libs.sync_utils_set import async_biz_info, async_agent
from domain.cloud_domain import all_domain_sync_index
from libs.consul_registry import async_consul_info
from cmp.tasks import async_order_status
from cmp.handlers import urls as order_urls


class Application(myApplication, ABC):
    def __init__(self, **settings):
        # 同步业务
        biz_callback = PeriodicCallback(async_biz_info, 360000)  # 360000 6分钟
        biz_callback.start()
        # 同步consul 信息
        consul_callback = PeriodicCallback(async_consul_info, 120000)  # 120000 2分钟
        consul_callback.start()
        # 同步agent 状态信息
        agent_callback = PeriodicCallback(async_agent, 180000)  # 180000 3分钟
        agent_callback.start()
        # 同步域名信息
        program_callback = PeriodicCallback(async_domain_info, 300000)  # 5分钟
        program_callback.start()
        # 资源订单状态
        biz_callback = PeriodicCallback(async_order_status, 20000)  # 20秒
        biz_callback.start()

        urls.extend(domain_urls)
        urls.extend(order_urls)
        super(Application, self).__init__(urls, **settings)

    def start_server(self):
        """
        继承后新增LogFormat
        :return:
        """
        try:
            init_logging()  # LOG
            init_scheduler()
            logging.info('[App Init] progressid: %(progid)s' % dict(progid=options.progid))
            logging.info('[App Init] server address: %(addr)s:%(port)d' % dict(addr=options.addr, port=options.port))
            logging.info('[App Init] web server start sucessfuled.')
            self.io_loop.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=True)
            self.io_loop.stop()
        except:
            import traceback
            logging.error('traceback %(tra)s' % dict(tra=traceback.format_exc()))


def async_domain_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(all_domain_sync_index)


if __name__ == '__main__':
    pass
