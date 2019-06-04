#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/18 10:12
# @Author  : Fred Yangxiaofei
# @File    : admin_user_handler.py
# @Role    : 管理用户


import json
from libs.base_handler import BaseHandler
from models.server import AdminUser, model_to_dict
from websdk.db_context import DBContext


class AdminUserHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=15, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        admin_user_list = []
        with DBContext('w') as session:
            if key and value:
                count = session.query(AdminUser).filter_by(**{key: value}).count()
                admin_user_data = session.query(AdminUser).filter_by(**{key: value}).order_by(
                    AdminUser.id).offset(limit_start).limit(int(limit))
            else:
                count = session.query(AdminUser).count()
                admin_user_data = session.query(AdminUser).order_by(AdminUser.id).offset(
                    limit_start).limit(int(limit))

        for data in admin_user_data:
            data_dict = model_to_dict(data)
            data_dict['update_time'] = str(data_dict['update_time'])
            admin_user_list.append(data_dict)
        return self.write(dict(code=0, msg='获取成功', count=count, data=admin_user_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        admin_user = data.get('admin_user', None)
        system_user = data.get('system_user', None)
        # password = data.get('password', None)
        user_key = data.get('user_key', None)
        remarks = data.get('remarks', None)

        if not admin_user or not system_user or not user_key:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('r') as session:
            exist_id = session.query(AdminUser.id).filter(AdminUser.admin_user == admin_user).first()
            count = session.query(AdminUser).count()
            print(count)
        if exist_id:
            return self.write(dict(code=-2, msg='不要重复记录'))

        if count > 15:
            return self.write(dict(code=-2, msg='管理用户最大只允许15个'))

        with DBContext('w', None, True) as session:
            new_admin_user = AdminUser(admin_user=admin_user, system_user=system_user, user_key=user_key, remarks=remarks)
            session.add(new_admin_user)
        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        admin_user_id = data.get('id')
        admin_user = data.get('admin_user', None)
        system_user = data.get('system_user', None)
        # password = data.get('password', None)
        user_key = data.get('user_key', None)
        remarks = data.get('remarks', None)

        if not admin_user or not system_user or not user_key:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        update_info = {
            "admin_user": admin_user,
            "system_user": system_user,
            "user_key": user_key,
            "remarks": remarks,
        }

        with DBContext('w', None, True) as session:
            session.query(AdminUser).filter(AdminUser.id == admin_user_id).update(update_info)
        self.write(dict(code=0, msg='更新成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id')
        if not id:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(AdminUser).filter(AdminUser.id == id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


admin_user_urls = [
    (r"/v1/cmdb/admin_user/", AdminUserHandler)
]
