#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/17 16:09
# @Author  : Fred Yangxiaofei
# @File    : asset_server_handler.py
# @Role    : 主机管理


import json
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from models.server import Tag, ServerTag, Server, ServerDetail, AssetErrorLog, model_to_dict
from websdk.db_context import DBContext
import tornado.web
from tornado import gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from libs.common import check_ip
from libs.server.sync_to_tagtree import main as sync_tag_tree
import datetime
from websdk.base_handler import LivenessProbe


class ServerHandler(BaseHandler):
    def get(self, *args, **kwargs):
        nickname = self.get_current_nickname()
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default="888", strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        server_list = []
        with DBContext('r') as session:
            ### 通过TAG搜索
            if key == 'tag_name' and value:
                count = session.query(Server).outerjoin(ServerTag, Server.id == ServerTag.server_id
                                                        ).outerjoin(Tag, Tag.id == ServerTag.tag_id).filter(
                    Tag.tag_name == value).count()
                server_info = session.query(Server).outerjoin(ServerTag, Server.id == ServerTag.server_id
                                                              ).outerjoin(Tag, Tag.id == ServerTag.tag_id).filter(
                    Tag.tag_name == value).order_by(Server.id).offset(limit_start).limit(int(limit))

                for msg in server_info:
                    tag_list = []
                    data_dict = model_to_dict(msg)
                    data_dict['create_time'] = str(data_dict['create_time'])
                    data_dict['update_time'] = str(data_dict['update_time'])
                    server_tags = session.query(Tag.tag_name).outerjoin(ServerTag, Tag.id == ServerTag.tag_id).filter(
                        ServerTag.server_id == data_dict['id']).all()
                    for t in server_tags:
                        tag_list.append(t[0])
                    data_dict['tag_list'] = tag_list
                    server_list.append(data_dict)
                return self.write(dict(code=0, msg='获取成功', count=count, data=server_list))

            ### 监听搜索
            if key and key != 'tag_name' and not value:
                if self.is_superuser:
                    # TODO 超管做全局搜索
                    count = session.query(Server).filter(or_(Server.hostname.like('%{}%'.format(key)),
                                                             Server.ip.like('%{}%'.format(key)),
                                                             Server.public_ip.like('%{}%'.format(key)),
                                                             Server.admin_user.like('%{}%'.format(key)),
                                                             Server.port.like('%{}%'.format(key)),
                                                             Server.idc.like('%{}%'.format(key)),
                                                             Server.region.like('%{}%'.format(key)),
                                                             Server.state.like('%{}%'.format(key)))).count()
                    server_info = session.query(Server).filter(or_(Server.hostname.like('%{}%'.format(key)),
                                                                   Server.ip.like('%{}%'.format(key)),
                                                                   Server.public_ip.like('%{}%'.format(key)),
                                                                   Server.admin_user.like('%{}%'.format(key)),
                                                                   Server.port.like('%{}%'.format(key)),
                                                                   Server.idc.like('%{}%'.format(key)),
                                                                   Server.region.like('%{}%'.format(key)),
                                                                   Server.state.like('%{}%'.format(key)))).order_by(
                        Server.id)
                else:
                    # TODO 普通用户做搜索
                    server_id_list = []
                    with DBContext('r') as session:
                        the_servers = session.query(ServerTag.server_id).filter(ServerTag.tag_id.in_(
                            session.query(Tag.id).filter(or_(Tag.users.like('%{}%'.format(nickname))))))
                        for s in the_servers:
                            server_id_list.append(s[0])
                        # 去重下列表,万一有重复的呢
                        set_server_id_list = set(server_id_list)
                        # 获取主机详情
                        count = session.query(Server).filter(Server.id.in_(set_server_id_list)).filter(
                            or_(Server.hostname.like('%{}%'.format(key)),
                                Server.ip.like('%{}%'.format(key)),
                                Server.public_ip.like('%{}%'.format(key)),
                                Server.admin_user.like('%{}%'.format(key)),
                                Server.port.like('%{}%'.format(key)),
                                Server.idc.like('%{}%'.format(key)),
                                Server.region.like('%{}%'.format(key)),
                                Server.state.like('%{}%'.format(key)))).count()
                        server_info = session.query(Server).filter(Server.id.in_(set_server_id_list)).filter(
                            or_(Server.hostname.like('%{}%'.format(key)),
                                Server.ip.like('%{}%'.format(key)),
                                Server.public_ip.like('%{}%'.format(key)),
                                Server.admin_user.like('%{}%'.format(key)),
                                Server.port.like('%{}%'.format(key)),
                                Server.idc.like('%{}%'.format(key)),
                                Server.region.like('%{}%'.format(key)),
                                Server.state.like('%{}%'.format(key)))).order_by(
                            Server.id)

                # .offset(limit_start).limit(int(limit)) #这里加上分页的话，有时候有时候在别的页面进行全局搜可能会有点小问题
                for msg in server_info:
                    tag_list = []
                    data_dict = model_to_dict(msg)
                    data_dict['create_time'] = str(data_dict['create_time'])
                    data_dict['update_time'] = str(data_dict['update_time'])
                    db_tags = session.query(Tag.tag_name).outerjoin(ServerTag, Tag.id == ServerTag.tag_id).filter(
                        ServerTag.server_id == data_dict['id']).all()
                    for t in db_tags:
                        tag_list.append(t[0])

                    data_dict['tag_list'] = tag_list
                    server_list.append(data_dict)

                return self.write(dict(code=0, msg='获取成功', count=count, data=server_list))

            if limit == "888":
                ### 888查看所有
                count = session.query(Server).count()
                server_info = session.query(Server).order_by(Server.id).all()
            else:
                ## 正常分页搜索
                # TODO 超级管理员查询所有
                if self.is_superuser:
                    if key and value:
                        count = session.query(Server).filter_by(**{key: value}).count()
                        server_info = session.query(Server).filter_by(**{key: value}).order_by(Server.id).offset(
                            limit_start).limit(int(limit))
                    else:
                        count = session.query(Server).count()
                        server_info = session.query(Server).order_by(Server.id).offset(limit_start).limit(int(limit))
                else:
                    # TODO 普通用户只给有权限的主机,根据用户查Tagid, 根据Tagid查询出来关联的ServerID，根据ServerID返回主机详情
                    server_id_list = []
                    with DBContext('r') as session:
                        # 子查询查出来server_id
                        the_servers = session.query(ServerTag.server_id).filter(ServerTag.tag_id.in_(
                            session.query(Tag.id).filter(or_(Tag.users.like('%{}%'.format(nickname))))))
                        for s in the_servers:
                            server_id_list.append(s[0])
                        # 去重下列表,万一有重复的呢
                        set_server_id_list = set(server_id_list)
                    if key and value:
                        # 根据Keyvalue获取
                        count = session.query(Server).filter(Server.id.in_(set_server_id_list)).filter_by(
                            **{key: value}).count()
                        server_info = session.query(Server).filter(Server.id.in_(set_server_id_list)).filter_by(
                            **{key: value}).order_by(Server.id).offset(
                            limit_start).limit(int(limit))
                    else:
                        # 获取主机详情
                        count = session.query(Server).filter(Server.id.in_(set_server_id_list)).count()
                        server_info = session.query(Server).filter(Server.id.in_(set_server_id_list)).offset(
                            limit_start).limit(int(limit))

            for msg in server_info:
                tag_list = []
                data_dict = model_to_dict(msg)
                server_tags = session.query(Tag.tag_name).outerjoin(ServerTag, Tag.id == ServerTag.tag_id).filter(
                    ServerTag.server_id == data_dict['id']).all()
                for t in server_tags:
                    tag_list.append(t[0])
                data_dict['create_time'] = str(data_dict['create_time'])
                data_dict['update_time'] = str(data_dict['update_time'])
                data_dict['tag_list'] = tag_list
                server_list.append(data_dict)

        self.write(dict(code=0, msg='获取成功', count=count, data=server_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        hostname = data.get('hostname', None)
        ip = data.get('ip', None)
        port = data.get('port', 22)
        public_ip = data.get('public_ip', None)
        idc = data.get('idc', None)
        admin_user = data.get('admin_user', None)
        region = data.get('region', None)
        state = data.get('state', 'new')
        tag_list = data.get('tag_list', [])
        detail = data.get('detail', None)

        if not hostname or not ip or not port:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        if not admin_user:
            return self.write(dict(code=-1, msg='管理用户不能为空'))

        if not check_ip(ip):
            return self.write(dict(code=-1, msg="IP格式不正确"))

        if not type(port) is int and int(port) >= 65535:
            return self.write(dict(code=-1, msg="端口格式不正确"))

        with DBContext('r') as session:
            exist_id = session.query(Server.id).filter(Server.hostname == hostname).first()
            exist_ip = session.query(Server.id).filter(Server.ip == ip).first()
        if exist_id or exist_ip:
            return self.write(dict(code=-2, msg='不要重复记录'))

        with DBContext('w', None, True) as session:
            new_server = Server(hostname=hostname, ip=ip, public_ip=public_ip, port=int(port), idc=idc,
                                admin_user=admin_user, region=region, state=state, detail=detail)
            session.add(new_server)

            all_tags = session.query(Tag.id).filter(Tag.tag_name.in_(tag_list)).order_by(Tag.id).all()
            # print('all_tags', all_tags)
            if all_tags:
                for tag_id in all_tags:
                    session.add(ServerTag(server_id=new_server.id, tag_id=tag_id[0]))

        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        server_id = data.get('id', None)
        hostname = data.get('hostname', None)
        ip = data.get('ip', None)
        public_ip = data.get('public_ip', None)
        port = data.get('port', None)
        idc = data.get('idc', None)
        admin_user = data.get('admin_user', None)
        region = data.get('region', None)
        tag_list = data.get('tag_list', [])
        detail = data.get('detail', None)

        if not hostname or not ip or not port:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        if not admin_user:
            return self.write(dict(code=-1, msg='管理用户不能为空'))

        if not check_ip(ip):
            return self.write(dict(code=-1, msg="IP格式不正确"))

        if not type(port) is int and int(port) >= 65535:
            return self.write(dict(code=-1, msg="端口格式不正确"))

        with DBContext('w', None, True) as session:
            exist_hostname = session.query(Server.hostname).filter(Server.id == server_id).first()
            if exist_hostname[0] != hostname:
                return self.write(dict(code=-2, msg='主机名不能修改'))

            session.query(ServerTag).filter(ServerTag.server_id == server_id).delete(synchronize_session=False)
            all_tags = session.query(Tag.id).filter(Tag.tag_name.in_(tag_list)).order_by(Tag.id).all()
            if all_tags:
                for tag_id in all_tags:
                    session.add(ServerTag(server_id=server_id, tag_id=tag_id[0]))

            session.query(Server).filter(Server.id == server_id).update({Server.hostname: hostname, Server.ip: ip,
                                                                         Server.port: int(port),
                                                                         Server.public_ip: public_ip,
                                                                         Server.idc: idc,
                                                                         Server.admin_user: admin_user,
                                                                         Server.region: region, Server.detail: detail
                                                                         })  # Server.state: 'new'

        return self.write(dict(code=0, msg='编辑成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        server_id = data.get('server_id', None)
        id_list = data.get('id_list', None)
        with DBContext('w', None, True) as session:
            if server_id:
                server_info = session.query(Server).filter(Server.id == int(server_id)).first()
                session.query(ServerDetail).filter(ServerDetail.ip == server_info.ip).delete(synchronize_session=False)
                session.query(Server).filter(Server.id == int(server_id)).delete(synchronize_session=False)
                session.query(ServerTag).filter(ServerTag.server_id == int(server_id)).delete(synchronize_session=False)


            elif id_list:
                for i in id_list:
                    server_info = session.query(Server).filter(Server.id == i).first()
                    session.query(ServerDetail).filter(ServerDetail.ip == server_info.ip).delete(
                        synchronize_session=False)
                    session.query(Server).filter(Server.id == i).delete(synchronize_session=False)
                    session.query(ServerTag).filter(ServerTag.server_id == i).delete(synchronize_session=False)
            else:
                return self.write(dict(code=1, msg='关键参数不能为空'))
        return self.write(dict(code=0, msg='删除成功'))


class ServerDetailHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=10, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        server_detail_list = []
        with DBContext('w', None, True) as session:
            if key and value:
                count = session.query(ServerDetail).filter_by(**{key: value}).count()
                server_detail_info = session.query(ServerDetail).filter_by(**{key: value}).order_by(
                    ServerDetail.id)
                # .offset(limit_start).limit(int(limit))   #这里加上分页的话，有时候有时候在别的页面进行全局搜可能会有点小问题
            else:
                count = session.query(ServerDetail).count()
                server_detail_info = session.query(ServerDetail).order_by(ServerDetail.id)
                # .offset(limit_start).limit(int(limit))   #这里加上分页的话，有时候有时候在别的页面进行全局搜可能会有点小问题

        for data in server_detail_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            server_detail_list.append(data_dict)

        if not server_detail_list:
            return self.write(dict(code=-1, msg='获取失败'))
        return self.write(dict(code=0, msg='获取成功', count=count, data=server_detail_list))


class TreeHandler(BaseHandler):
    def get(self, *args, **kwargs):
        nickname = self.get_current_nickname()
        _tree = [{
            "expand": True,
            "title": 'root',
            "children": [
            ]
        }]

        with DBContext('r', None, True) as session:
            if self.is_superuser:
                # TODO 超管看所有Tag Tree
                db_tags = session.query(Tag).order_by(Tag.id).all()
            else:
                # TODO 普通用户看有权限的TAG Tree
                db_tags = session.query(Tag).order_by(Tag.id).filter(Tag.users.like('%{}%'.format(nickname)))
            for msg in db_tags:
                server_dict = {}
                data_dict = model_to_dict(msg)
                server_tags = session.query(ServerTag.id).outerjoin(Server, Server.id == ServerTag.server_id
                                                                    ).filter(ServerTag.tag_id == msg.id).all()
                server_dict['the_len'] = len(server_tags)
                server_dict['title'] = data_dict['tag_name'] + ' ({})'.format(len(server_tags))
                # print(server_dict['title'])
                server_dict['tag_name'] = data_dict['tag_name']
                # print(server_dict['tag_name'])
                server_dict['node'] = 'root'
                _tree[0]["children"].append(server_dict)

        self.write(dict(code=0, msg='获取成功', data=_tree))


class AssetErrorLogHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=10, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        with DBContext('r', None, True) as session:
            log_list = []
            if key and value:
                log_info = session.query(AssetErrorLog).filter_by(**{key: value}).order_by(
                    AssetErrorLog.id).offset(limit_start).limit(int(limit))
            else:
                log_info = session.query(AssetErrorLog).order_by(AssetErrorLog.id).all()
            for msg in log_info:
                data_dict = model_to_dict(msg)
                data_dict['create_time'] = str(data_dict['create_time'])
                log_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=log_list))


class SyncServerTagTree(BaseHandler):
    '''CMDB Server信息同步到TagTree，使用异步方法'''
    _thread_pool = ThreadPoolExecutor(2)

    @run_on_executor(executor='_thread_pool')
    def sync_task(self):
        msg = sync_tag_tree()
        return msg

    @gen.coroutine
    def get(self, *args, **kwargs):
        try:
            # 超过120s 返回Timeout
            msg = yield gen.with_timeout(datetime.timedelta(seconds=120), self.sync_task(),
                                         quiet_exceptions=tornado.gen.TimeoutError)
            if msg:
                return self.write(dict(code=-1, msg=msg))
        except gen.TimeoutError:
            return self.write(dict(code=-2, msg='TimeOut'))
        return self.write(dict(code=0, msg='同步TagTree完成, 详细的机器同步信息可查看后端日志'))


asset_server_urls = [
    (r"/v1/cmdb/server/", ServerHandler),
    (r"/v1/cmdb/server_detail/", ServerDetailHandler),
    (r"/v1/cmdb/tree/", TreeHandler),
    (r"/v1/cmdb/error_log/", AssetErrorLogHandler),
    (r"/v1/cmdb/server/sync_tagtree/", SyncServerTagTree),
    (r"/are_you_ok/", LivenessProbe),
]

if __name__ == "__main__":
    pass
