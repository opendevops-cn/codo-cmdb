#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/12 15:10
Desc    : Server data
"""

import json
import logging
from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.db_context import DBContext
from models.asset import AssetUserFieldModels
from services.asset_server_service import add_server_batch, patch_server_batch, add_server, delete_server, mark_server, \
    get_server_list


class AssetServerHandler(BaseHandler, ABC):
    def get(self):
        res = get_server_list(**self.params)
        self.write(res)

    def post(self):
        """
        添加Server数据，一般都是用自动获取，应对非等待获取，其他云机器
        :return:
        """
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_server(data)
        return self.write(res)

    def patch(self):
        """
        标记上线状态
        :return:
        """
        data = json.loads(self.request.body.decode("utf-8"))
        res = mark_server(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = delete_server(data)
        return self.write(res)


class AssetServerBatchHandler(BaseHandler, ABC):
    def post(self):
        """
        添加Server数据，一般都是用自动获取，应对非等待获取，其他云机器
        :return:
        """
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_server_batch(data)
        return self.write(res)

    def patch(self):
        """
        批量修改数据
        :return:
        """
        data = json.loads(self.request.body.decode("utf-8"))
        res = patch_server_batch(data)
        return self.write(res)


class AssetUserFieldHandler(BaseHandler, ABC):
    def get(self):
        nickname = self.request_fullname()
        user_name = nickname if nickname else 'admin'
        logging.info(f'UserName:{user_name}')
        user_type = self.get_argument('user_type', None)
        if not user_name or not user_type:
            return self.write({"code": 1, "msg": "username/type不能为空"})

        with DBContext('r', None, None) as session:
            __info = session.query(AssetUserFieldModels.user_fields).filter(
                AssetUserFieldModels.user_name == user_name,
                AssetUserFieldModels.user_type == user_type
            ).first()
            user_felids = __info[0] if __info else None

        return self.write({"code": 0, "msg": "success", "data": user_felids})

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        nickname = self.request_fullname()
        user_name = nickname if nickname else 'admin'
        user_type = data.get('user_type', None)
        user_fields = data.get('user_fields', None)
        if not user_name or not user_type or not user_fields:
            return self.write({"code": 1, "msg": "用户收藏字段参数不能为空"})
        logging.info(f'UserName:{user_name}')
        with DBContext('w', None, True) as session:
            exist_id = session.query(AssetUserFieldModels.id).filter(
                AssetUserFieldModels.user_name == user_name,
                AssetUserFieldModels.user_type == user_type
            ).first()
            if not exist_id:
                session.add(AssetUserFieldModels(
                    user_name=user_name, user_type=user_type, user_fields=user_fields
                ))
            else:
                session.query(AssetUserFieldModels).filter(
                    AssetUserFieldModels.user_name == user_name,
                    AssetUserFieldModels.user_type == user_type
                ).update({
                    AssetUserFieldModels.user_fields: user_fields
                })
            session.commit()
        return self.write({"code": 0, "msg": "字段设置成功"})


server_urls = [
    (r"/api/v2/cmdb/server/", AssetServerHandler, {"handle_name": "CMDB-主机管理", "handle_status": "y"}),
    (r"/api/v2/cmdb/server/batch/", AssetServerBatchHandler, {"handle_name": "CMDB-主机管理批量", "handle_status": "y"}),
    (r"/api/v2/cmdb/user_field/", AssetUserFieldHandler, {"handle_name": "CMDB-用户字段配置", "handle_status": "y"}),
]
