#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/19 9:28
# @Author  : Fred Yangxiaofei
# @File    : asset_tag_handler.py
# @Role    : Tag


import json
from libs.base_handler import BaseHandler
from sqlalchemy import or_
from models.server import Tag, TagRule, Server, ServerTag, model_to_dict
from models.db import DB, DBTag
from websdk.db_context import DBContext
from websdk.web_logs import ins_log
import tornado.web
from tornado import gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor


class TagAuthority(BaseHandler):
    def get(self, *args, **kwargs):
        nickname = self.get_current_nickname()
        tag_list = []

        with DBContext('r') as session:
            if self.is_superuser:
                # TODO 超管看所有
                the_tags = session.query(Tag).order_by(Tag.id).all()
            else:
                # TODO 普通用户看有权限的TAG
                the_tags = session.query(Tag).order_by(Tag.id).filter(Tag.users.like('%{}%'.format(nickname)))

        for msg in the_tags:
            data_dict = model_to_dict(msg)
            data_dict.pop('create_time')
            if self.is_superuser:
                tag_list.append(data_dict)
            elif data_dict['users'] and nickname in data_dict['users'].split(','):
                tag_list.append(data_dict)
        return self.write(dict(code=0, msg='获取成功', data=tag_list))


class TAGHandler(BaseHandler):
    def get(self, *args, **kwargs):
        nickname = self.get_current_nickname()
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default="888", strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        tag_list = []

        with DBContext('r') as session:
            if key == 'tag_name' and value:
                count = session.query(Tag).filter(Tag.tag_name.like('%{}%'.format(value))).count()
                all_tags = session.query(Tag).filter(Tag.tag_name.like('%{}%'.format(value))).order_by(Tag.id).offset(
                    limit_start).limit(int(limit))
            elif limit == '888':
                count = session.query(Tag).count()
                all_tags = session.query(Tag).order_by(Tag.id).all()
            elif key and key != 'tag_name' and value:
                count = session.query(Tag).filter_by(**{key: value}).count()
                all_tags = session.query(Tag).order_by(Tag.id).filter_by(**{key: value}).order_by(Tag.id).offset(
                    limit_start).limit(int(limit))
            else:
                count = session.query(Tag).count()
                all_tags = session.query(Tag).order_by(Tag.id).offset(limit_start).limit(int(limit))

            for msg in all_tags:
                db_list = []
                server_list = []
                data_dict = model_to_dict(msg)
                data_dict['create_time'] = str(data_dict['create_time'])
                if data_dict['users']:
                    data_dict['users'] = data_dict.get('users', '').split(',')
                else:
                    data_dict['users'] = []
                server_tags = session.query(ServerTag.id, Server.id).outerjoin(Server, Server.id == ServerTag.server_id
                                                                               ).filter(
                    ServerTag.tag_id == msg.id).all()
                for i in server_tags:
                    server_list.append(i[1])
                data_dict['servers'] = server_list
                data_dict['server_len'] = len(server_tags)

                db_tags = session.query(DBTag.id, DB.id, DB.db_code).outerjoin(DB, DB.id == DBTag.db_id).filter(
                    DBTag.tag_id == msg.id).all()
                for i in db_tags:
                    db_list.append(i[1])
                data_dict['db_len'] = len(db_tags)
                data_dict['dbs'] = db_list
                tag_list.append(data_dict)

        self.write(dict(code=0, msg='获取成功', count=count, data=tag_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        tag_name = data.get('tag_name')
        users = data.get('users')
        dbs = data.get('dbs')  ### ID列表
        servers = data.get('servers')  ### ID列表
        proxy_host = data.get('proxy_host', None)

        if not tag_name or not users:
            return self.write(dict(code=-1, msg='标签名称不能为空'))

        with DBContext('r') as session:
            exist_id = session.query(Tag.id).filter(Tag.tag_name == tag_name).first()

        if exist_id:
            return self.write(dict(code=-2, msg='标签名称重复'))

        ### 判断是否存在
        with DBContext('w', None, True) as session:
            if users:
                users = ','.join(users)
            new_tag = Tag(tag_name=tag_name, users=users, proxy_host=proxy_host)
            session.add(new_tag)
            session.commit()
            if dbs:
                for db in dbs:
                    session.add(DBTag(db_id=int(db), tag_id=new_tag.id))
            if servers:
                for server in servers:
                    session.add(ServerTag(server_id=int(server), tag_id=new_tag.id))

        self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        tag_id = data.get('id')
        users = data.get('users')
        db_id_list = data.get('dbs')  ### ID列表
        server_id_list = data.get('servers')  ### ID列表
        proxy_host = data.get('proxy_host', None)

        if not users:
            return self.write(dict(code=-1, msg='授权用户不能为空'))

        with DBContext('w', None, True) as session:
            # if db_id_list:
            # db_list, new_db_list, del_db_list = [], [], []
            # in_db_tags = session.query(DB.id).outerjoin(DBTag, DBTag.db_id == DB.id).filter(
            #     DBTag.tag_id == tag_id).all()
            # for i in in_db_tags:
            #     i = i[0]
            #     db_list.append(i)
            #     if i not in db_id_list:
            #         del_db_list.append(i)
            #         session.query(DBTag).filter(DBTag.db_id == i).delete(synchronize_session=False)
            #
            # for i in db_id_list:
            #     if i not in db_list:
            #         session.add(DBTag(db_id=int(i), tag_id=tag_id))
            #         new_db_list.append(i)

            # if server_id_list:
            # server_list, new_server_list, del_server_list = [], [], []
            # in_server_tags = session.query(Server.id).outerjoin(ServerTag, ServerTag.server_id == Server.id).filter(
            #     ServerTag.tag_id == tag_id).all()
            #
            # for i in in_server_tags:
            #     i = i[0]
            #     server_list.append(i)
            #     if i not in server_id_list:
            #         del_server_list.append(i)
            #
            #         session.query(ServerTag).filter(ServerTag.server_id == i).delete(synchronize_session=False)
            #
            # for i in server_id_list:
            #     if i not in server_list:
            #         session.add(ServerTag(server_id=int(i), tag_id=tag_id))
            #         new_server_list.append(i)
            session.query(DBTag).filter(DBTag.tag_id == int(tag_id)).delete(synchronize_session=False)
            session.add_all([
                DBTag(db_id=i, tag_id=tag_id) for i in db_id_list
            ])

            session.query(ServerTag).filter(ServerTag.tag_id == int(tag_id)).delete(synchronize_session=False)
            session.add_all([
                ServerTag(server_id=i, tag_id=tag_id) for i in server_id_list
            ])
            if users:
                users = ','.join(users)
            session.query(Tag).filter(Tag.id == int(tag_id)).update({Tag.users: users, Tag.proxy_host: proxy_host})
            session.commit()

        self.write(dict(code=0, msg='修改成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        tag_id = data.get('tag_id')
        id_list = data.get('id_list')

        with DBContext('w', None, True) as session:
            if tag_id:
                exist_server_count = session.query(ServerTag).filter(ServerTag.tag_id == tag_id).count()
                exist_db_count = session.query(DBTag).filter(DBTag.tag_id == tag_id).count()
                if exist_server_count != 0 or exist_db_count != 0:
                    return self.write(dict(code=1, msg='标签里面存在已关联的Server/DB，请先取消关联才能继续删除标签'))
                else:
                    session.query(Tag).filter(Tag.id == tag_id).delete(synchronize_session=False)

            elif id_list:
                for i in id_list:
                    exist_server_count = session.query(ServerTag).filter(ServerTag.tag_id == i).count()
                    exist_db_count = session.query(DBTag).filter(DBTag.tag_id == i).count()
                    if exist_server_count != 0 or exist_db_count != 0:
                        return self.write(dict(code=1, msg='标签里面存在已关联的Server/DB，请先取消关联才能继续删除标签'))
                    else:
                        session.query(Tag).filter(Tag.id == i).delete(synchronize_session=False)
            else:
                return self.write(dict(code=1, msg='关键参数不能为空'))
        self.write(dict(code=0, msg='删除成功'))


class TagRuleHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        tag_rule_list = []
        with DBContext('r') as session:
            if key and value:
                tag_rule_data = session.query(TagRule).filter_by(**{key: value}).all()
            else:
                tag_rule_data = session.query(TagRule).all()

        for data in tag_rule_data:
            data_dict = model_to_dict(data)
            tag_rule_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=tag_rule_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        name = data.get('name', None)
        tag_name = data.get('tag_name', None)
        idc_rule = data.get('idc_rule', None)
        hostname_rule = data.get('hostname_rule', None)

        if not name or not tag_name:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        if not idc_rule and not hostname_rule:
            return self.write(dict(code=-1, msg='一个规则条件都没创建个锤子呀'))

        with DBContext('r') as session:
            exist_name = session.query(TagRule.id).filter(TagRule.name == name).first()

        if exist_name:
            return self.write(dict(code=-2, msg='规则名称重复'))

        with DBContext('w', None, True) as session:
            new_tag_rule = TagRule(name=name, tag_name=tag_name, idc_rule=idc_rule, hostname_rule=hostname_rule)
            session.add(new_tag_rule)
        session.commit()

        self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id', None)
        name = data.get('name', None)
        tag_name = data.get('tag_name', None)
        idc_rule = data.get('idc_rule', None)
        hostname_rule = data.get('hostname_rule', None)

        if not name or not tag_name:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        if not idc_rule and not hostname_rule:
            return self.write(dict(code=-1, msg='一个规则条件都没创建个锤子呀'))

        with DBContext('w', None, True) as session:
            exist_name = session.query(TagRule.name).filter(TagRule.id == id).first()
            if exist_name[0] != name:
                return self.write(dict(code=-2, msg='规则名称不能修改'))

            exist_tag_name = session.query(TagRule.tag_name).filter(TagRule.id == id).first()
            if exist_tag_name[0] != tag_name:
                return self.write(dict(code=-2, msg='关联Tag不能修改'))

            session.query(TagRule).filter(TagRule.id == id).update(
                {TagRule.idc_rule: idc_rule, TagRule.hostname_rule: hostname_rule})  # Server.state: 'new'

        return self.write(dict(code=0, msg='编辑成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        rule_id = data.get('id', None)

        if not rule_id:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            if rule_id:
                session.query(TagRule).filter(TagRule.id == int(rule_id)).delete(synchronize_session=False)

        return self.write(dict(code=0, msg='删除成功'))


class HandUpdateTagrule(tornado.web.RequestHandler):
    '''手动触发自动规则加入tag'''
    _thread_pool = ThreadPoolExecutor(2)

    @run_on_executor(executor='_thread_pool')
    def hand_update_rule(self, rule_name):
        with DBContext('w') as session:
            tag_rule = session.query(TagRule).filter(TagRule.name == rule_name).first()
            tag_rule_data = model_to_dict(tag_rule)
            tag_name = tag_rule_data.get('tag_name')
            idc_rule = tag_rule_data.get('idc_rule')
            hostname_rule = tag_rule_data.get('hostname_rule')

            # 查到这个tag_name的tag_id
            tag_id = session.query(Tag.id).filter(or_(Tag.tag_name == tag_name)).first()
            tag_id = int(tag_id[0])

            # 子查询此Tag现有的主机,肯定不能删除用户手动加的主机，不然会被打死
            tag_exist_serverid_list = session.query(ServerTag.server_id).filter(ServerTag.tag_id.in_(
                session.query(Tag.id).filter(or_(Tag.tag_name == tag_name)))).all()

            tag_exist_serverid_list = [s_id[0] for s_id in tag_exist_serverid_list]
            ins_log.read_log('info', '{} already exists server id list: {}'.format(tag_name, tag_exist_serverid_list))

            if idc_rule and not hostname_rule:
                # 根据idc自动匹配到的主机
                idc_matching_serverid_list = session.query(Server.id).filter(Server.idc == idc_rule).all()
                idc_matching_serverid_list = [s_id[0] for s_id in idc_matching_serverid_list]
                # print('根据IDC匹配到的主机列表:{}'.format(idc_matching_serverid_list))
                ins_log.read_log('info', 'IDC:{} Matching server id list: {}'.format(idc_rule, idc_matching_serverid_list))

                # list合并 集合去重
                tocal_server_id_list = []
                tocal_server_id_list.extend(tag_exist_serverid_list)
                tocal_server_id_list.extend(idc_matching_serverid_list)
                tocal_server_id_list = list(set(tocal_server_id_list))
                # print('Tocal:{}'.format(tocal_server_id_list))
                ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))

                session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete()
                session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])


            elif hostname_rule or not idc_rule:
                # 根据hostname自动匹配到的主机
                hostname_matching_serverid_list = session.query(Server.id).filter(
                    or_(Server.hostname.like('%{}%'.format(hostname_rule)))).all()
                hostname_matching_serverid_list = [s_id[0] for s_id in hostname_matching_serverid_list]
                ins_log.read_log('info',
                    'hostname:{} Matching server id list: {}'.format(hostname_rule, hostname_matching_serverid_list))
                # list合并 集合去重
                tocal_server_id_list = []
                tocal_server_id_list.extend(tag_exist_serverid_list)
                tocal_server_id_list.extend(hostname_matching_serverid_list)
                tocal_server_id_list = list(set(tocal_server_id_list))
                ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))

                # 先删除、后添加
                session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete(synchronize_session=False)
                session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])

            elif idc_rule and hostname_rule:
                # 根据IDC+hostname同时匹配到的主机
                idc_matching_serverid_list = session.query(Server.id).filter(Server.idc == idc_rule).all()
                idc_matching_serverid_list = [s_id[0] for s_id in idc_matching_serverid_list]
                hostname_matching_serverid_list = session.query(Server.id).filter(
                    or_(Server.hostname.like('%{}%'.format(hostname_rule)))).all()
                hostname_matching_serverid_list = [s_id[0] for s_id in hostname_matching_serverid_list]

                # list合并、集合去重
                tocal_server_id_list = []
                tocal_server_id_list.extend(idc_matching_serverid_list)
                tocal_server_id_list.extend(hostname_matching_serverid_list)
                tocal_server_id_list.extend(tag_exist_serverid_list)
                tocal_server_id_list = list(set(tocal_server_id_list))
                ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))
                # 先删除、后添加
                session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete(synchronize_session=False)
                session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])

            session.commit()

    @run_on_executor(executor='_thread_pool')
    def hand_update_all_rule(self):
        '''更新所有规则'''
        with DBContext('w') as session:
            tag_rule_list = []
            tag_rule = session.query(TagRule).all()
            for r in tag_rule:
                tag_rule_data = model_to_dict(r)
                tag_rule_list.append(tag_rule_data)

            for rule in tag_rule_list:
                tag_name = rule.get('tag_name')
                idc_rule = rule.get('idc_rule')
                hostname_rule = rule.get('hostname_rule')

                # 查到这个tag_name的tag_id
                tag_id = session.query(Tag.id).filter(or_(Tag.tag_name == tag_name)).first()
                tag_id = int(tag_id[0])

                # 子查询此Tag现有的主机,肯定不能删除用户手动加的主机，不然会被打死
                tag_exist_serverid_list = session.query(ServerTag.server_id).filter(ServerTag.tag_id.in_(
                    session.query(Tag.id).filter(or_(Tag.tag_name == tag_name)))).all()

                tag_exist_serverid_list = [s_id[0] for s_id in tag_exist_serverid_list]
                # print('User already exists server id list-->', tag_exist_serverid_list)
                ins_log.read_log('info',
                                 '{},already exists server id list: {}'.format(tag_name, tag_exist_serverid_list))
                if idc_rule and not hostname_rule:
                    # 根据idc自动匹配到的主机
                    idc_matching_serverid_list = session.query(Server.id).filter(Server.idc == idc_rule).all()
                    idc_matching_serverid_list = [s_id[0] for s_id in idc_matching_serverid_list]
                    # print('根据IDC匹配到的主机列表:{}'.format(idc_matching_serverid_list))
                    ins_log.read_log('info','IDC:{} Matching server id list: {}'.format(idc_rule, idc_matching_serverid_list))

                    # list合并 集合去重
                    tocal_server_id_list = []
                    tocal_server_id_list.extend(tag_exist_serverid_list)
                    tocal_server_id_list.extend(idc_matching_serverid_list)
                    tocal_server_id_list = list(set(tocal_server_id_list))
                    # print('Tocal:{}'.format(tocal_server_id_list))
                    ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))
                    session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete()
                    session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])


                elif hostname_rule or not idc_rule:
                    # 根据hostname自动匹配到的主机
                    hostname_matching_serverid_list = session.query(Server.id).filter(
                        or_(Server.hostname.like('%{}%'.format(hostname_rule)))).all()
                    hostname_matching_serverid_list = [s_id[0] for s_id in hostname_matching_serverid_list]
                    ins_log.read_log('info',
                        'hostname:{} Matching server id list: {}'.format(hostname_rule,
                                                                         hostname_matching_serverid_list))

                    # list合并 集合去重
                    tocal_server_id_list = []
                    tocal_server_id_list.extend(tag_exist_serverid_list)
                    tocal_server_id_list.extend(hostname_matching_serverid_list)
                    tocal_server_id_list = list(set(tocal_server_id_list))
                    # print('Tocal:{}'.format(tocal_server_id_list))
                    ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))

                    # 先删除、后添加
                    session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete(synchronize_session=False)
                    session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])

                elif idc_rule and hostname_rule:
                    # 根据IDC+hostname同时匹配到的主机
                    idc_matching_serverid_list = session.query(Server.id).filter(Server.idc == idc_rule).all()
                    idc_matching_serverid_list = [s_id[0] for s_id in idc_matching_serverid_list]
                    hostname_matching_serverid_list = session.query(Server.id).filter(
                        or_(Server.hostname.like('%{}%'.format(hostname_rule)))).all()
                    hostname_matching_serverid_list = [s_id[0] for s_id in hostname_matching_serverid_list]

                    # list合并、集合去重
                    tocal_server_id_list = []
                    tocal_server_id_list.extend(idc_matching_serverid_list)
                    tocal_server_id_list.extend(hostname_matching_serverid_list)
                    tocal_server_id_list.extend(tag_exist_serverid_list)
                    tocal_server_id_list = list(set(tocal_server_id_list))
                    # print('Tocal：{}'.format(tocal_server_id_list))
                    ins_log.read_log('info', 'Tocal:{}'.format(tocal_server_id_list))
                    # 先删除、后添加
                    session.query(ServerTag).filter(ServerTag.tag_id == tag_id).delete(synchronize_session=False)
                    session.add_all([ServerTag(server_id=int(i), tag_id=tag_id) for i in tocal_server_id_list])

                session.commit()

    @gen.coroutine
    def get(self, *args, **kwargs):
        """刷新所有规则"""
        yield self.hand_update_all_rule()
        return self.write(dict(code=0, msg='Successful'))

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        rule_name = data.get('name', None)  # 规则名称

        if not rule_name:
            return self.write(dict(code=-1, msg='关键参数不能为空'))
        # print('手动触发规则:{name}'.format(name=rule_name))

        yield self.hand_update_rule(rule_name)
        # if err_msg:
        #     return self.write(dict(code=-1, msg=err_msg))

        return self.write(dict(code=0, msg='Successful'))


tag_urls = [
    (r"/v1/cmdb/tag/", TAGHandler),
    (r"/v1/cmdb/tag_auth/", TagAuthority),
    (r"/v1/cmdb/tag_rule/", TagRuleHandler),
    (r"/v1/cmdb/tag_rule/hand_update/", HandUpdateTagrule),
]
