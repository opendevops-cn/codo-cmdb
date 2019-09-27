#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : asset_idc_handler.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/9/10
# @Role  :  IDC管理


import json
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from models.server import AssetIDC, model_to_dict, AssetOperationalAudit
from websdk.db_context import DBContext
from websdk.tools import is_mail, is_tel
from websdk.web_logs import ins_log


class AssetIDCHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        idc_list = []
        with DBContext('w') as session:
            if key:
                idc_data = session.query(AssetIDC).filter(or_(AssetIDC.name.like('%{}%'.format(key)),
                                                              AssetIDC.contact.like('%{}%'.format(key)),
                                                              AssetIDC.email.like('%{}%'.format(key)),
                                                              AssetIDC.phone.like('%{}%'.format(key)),
                                                              AssetIDC.address.like('%{}%'.format(key)),
                                                              AssetIDC.network.like('%{}%'.format(key)),
                                                              AssetIDC.bandwidth.like('%{}%'.format(key)),
                                                              AssetIDC.ip_range.like('%{}%'.format(key)),
                                                              AssetIDC.remarks.like(
                                                                  '%{}%'.format(key)))).order_by(AssetIDC.id)
            else:
                idc_data = session.query(AssetIDC).order_by(AssetIDC.id).all()

        for data in idc_data:
            data_dict = model_to_dict(data)
            idc_list.append(data_dict)
        return self.write(dict(code=0, msg='获取成功', data=idc_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        nickname = self.get_current_nickname()
        name = data.get('name', None)
        contact = data.get('contact', None)
        email = data.get('email', None)
        phone = data.get('phone', None)
        address = data.get('address', None)
        network = data.get('network', None)
        bandwidth = data.get('bandwidth', None)
        ip_range = data.get('ip_range', None)
        remarks = data.get('remarks', None)

        if not name:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        if email and not is_mail(email):
            return self.write(dict(code=-2, msg='Email格式不正确'))

        if phone and not is_tel(phone):
            return self.write(dict(code=-2, msg='Phone格式不正确'))

        with DBContext('r') as session:
            exist_name = session.query(AssetIDC.id).filter(AssetIDC.name == name).first()
            count = session.query(AssetIDC).count()

        if exist_name:
            return self.write(dict(code=-2, msg='不要重复记录'))

        if count > 50:
            return self.write(dict(code=-2, msg='IDC最大只允许50个'))

        with DBContext('w', None, True) as session:

            new_idc = AssetIDC(name=name, contact=contact, email=email, phone=phone, address=address, network=network,
                               bandwidth=bandwidth, ip_range=ip_range, remarks=remarks)
            session.add(new_idc)

        # 记录,记录错误也不要影响用户正常添加
        try:
            with DBContext('w', None, True) as session:

                new_record = AssetOperationalAudit(username=nickname, request_object='IDC', request_host=name,
                                                   request_method='新增', modify_data=data)
                session.add(new_record)
        except Exception as err:
            ins_log.read_log('error', 'operational_audit error:{err}'.format(err=err))

        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        nickname = self.get_current_nickname()
        id = data.get('id', None)
        name = data.get('name', None)
        contact = data.get('contact', None)
        email = data.get('email', None)
        phone = data.get('phone', None)
        address = data.get('address', None)
        network = data.get('network', None)
        bandwidth = data.get('bandwidth', None)
        ip_range = data.get('ip_range', None)
        remarks = data.get('remarks', None)

        if not id or not name:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        if email and not is_mail(email):
            return self.write(dict(code=-2, msg='Email格式不正确'))

        if phone and not is_tel(phone):
            return self.write(dict(code=-2, msg='Phone格式不正确'))

        with DBContext('r') as session:
            exist_name = session.query(AssetIDC.name).filter(AssetIDC.id == id).first()

        if name != exist_name[0]:
            return self.write(dict(code=-2, msg='名称不能修改'))

        # 记录操作,不成功直接Pass
        try:
            modify_data = data
            with DBContext('w', None, True) as session:
                data_info = session.query(AssetIDC).filter(AssetIDC.id == id).all()
                for data in data_info:
                    origion_data = model_to_dict(data)
                    new_record = AssetOperationalAudit(username=nickname, request_object='IDC', request_host=name,
                                                       request_method='更新', original_data=origion_data,
                                                       modify_data=modify_data)
                    session.add(new_record)
        except Exception as err:
            ins_log.read_log('error', 'operational_audit error:{err}'.format(err=err))

        update_info = {
            "contact": contact,
            "email": email,
            "phone": phone,
            "address": address,
            "network": network,
            "bandwidth": bandwidth,
            "ip_range": ip_range,
            "remarks": remarks,
        }

        with DBContext('w', None, True) as session:
            session.query(AssetIDC).filter(AssetIDC.name == name).update(update_info)

        self.write(dict(code=0, msg='更新成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id')
        nickname = self.get_current_nickname()
        if not id:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        # 记录操作,不成功直接Pass
        try:
            with DBContext('w', None, True) as session:
                data_info = session.query(AssetIDC).filter(AssetIDC.id == id).all()
                for data in data_info:
                    origion_data = model_to_dict(data)
                    new_record = AssetOperationalAudit(username=nickname, request_object='IDC',
                                                       request_host=origion_data.get('name'),
                                                       request_method='删除', original_data=origion_data)
                    session.add(new_record)
        except Exception as err:
            ins_log.read_log('error', 'operational_audit error:{err}'.format(err=err))

        with DBContext('w', None, True) as session:
            session.query(AssetIDC).filter(AssetIDC.id == id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


asset_idc_urls = [
    (r"/v1/cmdb/idc/", AssetIDCHandler)
]
