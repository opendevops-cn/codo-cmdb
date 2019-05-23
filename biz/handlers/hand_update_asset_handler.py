#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/15 13:53
# @Author  : Fred Yangxiaofei
# @File    : hand_update_asset_handler.py
# @Role    : 手动更新资产
# 防止由于每个人习惯不同，可能引起未知的异常Bug导致主程序卡死的问题,使用异步方法


import json
from libs.base_handler import BaseHandler
from models.server import Server, AdminUser
from websdk.db_context import DBContext
import tornado.web
from tornado import gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from libs.server.collect_asset_info import get_server_sysinfo
from libs.server.server_common import update_asset, rsync_public_key
from websdk.web_logs import ins_log
import datetime


class HandUpdateAssetHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(6)

    @run_on_executor(executor='_thread_pool')
    def asset_update(self, id_list):
        # time.sleep(20)  #测试下阻塞
        server_list = []
        # 检查下状态，是true的话直接推送资产
        with DBContext('r', None, True) as session:
            for i in id_list:

                server_info = session.query(Server.ip, Server.port, AdminUser.system_user,
                                            AdminUser.user_key, Server.state).outerjoin(AdminUser,
                                                                                        AdminUser.admin_user == Server.admin_user).filter(
                    Server.id == i).all()
                server_list.append(server_info)
                # server_info = [('47.100.231.147', 22, 'root', '-----BEGIN RSA PRIVATE KEYxxxxxEND RSA PRIVATE KEY-----', 'false')]
                server_state = server_info[0][4]
                if server_state == 'true':
                    ins_log.read_log('info', 'update asset info')
                    # 选中的是true，直接更新资产
                    asset_data = get_server_sysinfo(server_list)
                    update_asset(asset_data)

                else:
                    # 选中的是其余的状态，那就先推送key, 拿到推送成功的key，更新资产
                    ins_log.read_log('info', 'rsync public key , update asset info')
                    rsync_sucess_list = rsync_public_key(server_list)
                    if rsync_sucess_list:
                        asset_data = get_server_sysinfo(server_list)
                        update_asset(asset_data)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id_list = data.get('id_list', None)
        if not id_list:
            return self.write(dict(code=1, msg='关键参数不能为空'))

        #yield self.asset_update(id_list)
        try:
            #超过120s 返回Timeout
            yield gen.with_timeout(datetime.timedelta(seconds=120), [self.asset_update(id_list)],
                                                  quiet_exceptions=tornado.gen.TimeoutError)
        except gen.TimeoutError:
            return self.write(dict(code=-2, msg='TimeOut'))
        return self.write(dict(code=0, msg='任务执行完成，提醒： 完成状态为：True, 错误状态：False， False状态下可点击查看日志进行排错'))


asset_hand_server_urls = [
    (r"/v1/cmdb/server/asset_update/", HandUpdateAssetHandler)
]
