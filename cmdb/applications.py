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
from websdk2.application import Application as myApplication
from libs.scheduler import scheduler, init_scheduler
from cmdb.handlers import urls
from domain.handlers import urls as domain_urls
from libs.sync_utils_set import async_biz_info, async_agent
from domain.cloud_domain import async_domain_info
from libs.consul_registry import async_consul_info
from cmp.tasks import async_order_status
from libs.asset_change import init_cmdb_change_tasks
from cmp.handlers import urls as order_urls
from cmdb.subscription import RedisSubscriber as SubApp


class Application(myApplication, ABC):
    def __init__(self, **settings):
        # 同步业务
        biz_callback = PeriodicCallback(async_biz_info, 360000)  # 360000 6分钟
        biz_callback.start()
        # 同步consul 信息
        consul_callback = PeriodicCallback(async_consul_info, 180000)  # 180000 3分钟
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
        # self.settings = settings
        super(Application, self).__init__(urls, **settings)
        self.sub_app = SubApp(**settings)

    def start_server(self):
        """
        继承后新增LogFormat
        :return:
        """
        try:
            init_scheduler()
            # 资产备份同步和变更通知任务
            init_cmdb_change_tasks()
            self.sub_app.start_server()
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


if __name__ == '__main__':
    pass
