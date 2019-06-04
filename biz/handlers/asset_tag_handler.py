#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/19 9:28
# @Author  : Fred Yangxiaofei
# @File    : asset_tag_handler.py
# @Role    : Tag


import json
from libs.base_handler import BaseHandler
from models.server import Tag, Server, ServerTag, model_to_dict
from models.db import DB, DBTag
from websdk.db_context import DBContext


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
            db_list, new_db_list, del_db_list = [], [], []
            in_db_tags = session.query(DB.id).outerjoin(DBTag, DBTag.db_id == DB.id).filter(
                DBTag.tag_id == tag_id).all()
            for i in in_db_tags:
                i = i[0]
                db_list.append(i)
                if i not in db_id_list:
                    del_db_list.append(i)
                    session.query(DBTag).filter(DBTag.db_id == i).delete(synchronize_session=False)

            for i in db_id_list:
                if i not in db_list:
                    session.add(DBTag(db_id=int(i), tag_id=tag_id))
                    new_db_list.append(i)

            # if server_id_list:
            server_list, new_server_list, del_server_list = [], [], []
            in_server_tags = session.query(Server.id).outerjoin(ServerTag, ServerTag.server_id == Server.id).filter(
                ServerTag.tag_id == tag_id).all()

            for i in in_server_tags:
                i = i[0]
                server_list.append(i)
                if i not in server_id_list:
                    del_server_list.append(i)

                    session.query(ServerTag).filter(ServerTag.server_id == i).delete(synchronize_session=False)

            for i in server_id_list:
                if i not in server_list:
                    session.add(ServerTag(server_id=int(i), tag_id=tag_id))
                    new_server_list.append(i)
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


tag_urls = [
    (r"/v1/cmdb/tag/", TAGHandler),
    (r"/v1/cmdb/tag_auth/", TagAuthority),
]
