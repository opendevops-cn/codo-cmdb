#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/21 8:37
# @Author  : Fred Yangxiaofei
# @File    : asset_db_handler.py
# @Role    : DB

import json
from sqlalchemy import or_
from libs.base_handler import BaseHandler
# from models.server import DB, DBTag, Tag, ServerTag, Server, ProxyInfo, model_to_dict
from models.db import DBTag, DB, model_to_dict
from models.server import Tag
from websdk.db_context import DBContext
import tornado.web


class DBHandler(BaseHandler):
    def get(self, *args, **kwargs):
        nickname = self.get_current_nickname()
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default='888', strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        db_list = []
        with DBContext('r') as session:
            ### 通过TAG搜索
            if key == 'tag_name' and value:
                count = session.query(DB).outerjoin(DBTag, DB.id == DBTag.db_id).outerjoin(Tag, Tag.id ==
                                                                                           DBTag.tag_id).filter(
                    Tag.tag_name == value).count()
                db_info = session.query(DB).outerjoin(DBTag, DB.id == DBTag.db_id).outerjoin(Tag, Tag.id ==
                                                                                             DBTag.tag_id).filter(
                    Tag.tag_name == value).order_by(DB.id).offset(limit_start).limit(int(limit))
                for msg in db_info:
                    tag_list = []
                    data_dict = model_to_dict(msg)
                    data_dict['create_time'] = str(data_dict['create_time'])
                    db_tags = session.query(Tag.tag_name).outerjoin(DBTag, Tag.id == DBTag.tag_id).filter(
                        DBTag.db_id == data_dict['id']).all()
                    for t in db_tags:
                        tag_list.append(t[0])
                    data_dict['tag_list'] = tag_list
                    db_list.append(data_dict)
                return self.write(dict(code=0, msg='获取成功', count=count, data=db_list))

            ### 监听搜索
            if key and key != 'tag_name' and not value:
                # TODO 超管查所有
                if self.is_superuser:

                    count = session.query(DB).filter(or_(DB.db_code.like('%{}%'.format(key)),
                                                         DB.db_host.like('%{}%'.format(key)),
                                                         DB.db_user.like('%{}%'.format(key)),
                                                         DB.db_pwd.like('%{}%'.format(key)),
                                                         DB.proxy_host.like('%{}%'.format(key)),
                                                         DB.db_type.like('%{}%'.format(key)),
                                                         DB.db_version.like('%{}%'.format(key)),
                                                         DB.db_mark.like('%{}%'.format(key)),
                                                         DB.state.like('%{}%'.format(key)),
                                                         DB.db_env.like('%{}%'.format(key)))).count()

                    db_info = session.query(DB).filter(or_(DB.db_code.like('%{}%'.format(key)),
                                                           DB.db_host.like('%{}%'.format(key)),
                                                           DB.db_user.like('%{}%'.format(key)),
                                                           DB.db_pwd.like('%{}%'.format(key)),
                                                           DB.proxy_host.like('%{}%'.format(key)),
                                                           DB.db_type.like('%{}%'.format(key)),
                                                           DB.db_version.like('%{}%'.format(key)),
                                                           DB.db_mark.like('%{}%'.format(key)),
                                                           DB.state.like('%{}%'.format(key)),
                                                           DB.db_env.like('%{}%'.format(key)))).order_by(DB.id).offset(
                        limit_start).limit(int(limit))

                else:
                    # TODO 普通用户只能看到有权限的
                    db_id_list = []
                    with DBContext('r') as session:
                        the_dbs = session.query(DBTag.db_id).filter(DBTag.tag_id.in_(
                            session.query(Tag.id).filter(or_(Tag.users.like('%{}%'.format(nickname))))))
                        for s in the_dbs:
                            db_id_list.append(s[0])
                        # 去重下列表,万一有重复的呢
                        set_db_id_list = set(db_id_list)
                        count = session.query(DB).filter(DB.id.in_(set_db_id_list)).filter(
                            or_(DB.db_code.like('%{}%'.format(key)),
                                DB.db_host.like('%{}%'.format(key)),
                                DB.db_user.like('%{}%'.format(key)),
                                DB.db_pwd.like('%{}%'.format(key)),
                                DB.proxy_host.like('%{}%'.format(key)),
                                DB.db_type.like('%{}%'.format(key)),
                                DB.db_version.like('%{}%'.format(key)),
                                DB.db_mark.like('%{}%'.format(key)),
                                DB.state.like('%{}%'.format(key)),
                                DB.db_env.like('%{}%'.format(key)))).count()

                        db_info = session.query(DB).filter(DB.id.in_(set_db_id_list)).filter(
                            or_(DB.db_code.like('%{}%'.format(key)),
                                DB.db_host.like('%{}%'.format(key)),
                                DB.db_user.like('%{}%'.format(key)),
                                DB.db_pwd.like('%{}%'.format(key)),
                                DB.proxy_host.like('%{}%'.format(key)),
                                DB.db_type.like('%{}%'.format(key)),
                                DB.db_version.like('%{}%'.format(key)),
                                DB.db_mark.like('%{}%'.format(key)),
                                DB.state.like('%{}%'.format(key)),
                                DB.db_env.like('%{}%'.format(key)))).order_by(DB.id).offset(
                            limit_start).limit(int(limit))

                for msg in db_info:
                    tag_list = []
                    data_dict = model_to_dict(msg)
                    data_dict['create_time'] = str(data_dict['create_time'])
                    db_tags = session.query(Tag.tag_name).outerjoin(DBTag, Tag.id == DBTag.tag_id).filter(
                        DBTag.db_id == data_dict['id']).all()
                    for t in db_tags:
                        tag_list.append(t[0])
                    data_dict['tag_list'] = tag_list
                    db_list.append(data_dict)

                return self.write(dict(code=0, msg='获取成功', count=count, data=db_list))

            ### 888查看所有的数据库
            if limit == '888':
                count = session.query(DB).count()
                db_info = session.query(DB).order_by(DB.id).all()
            else:
                # TODO 超管查所有
                if self.is_superuser:
                    if key and value:
                        count = session.query(DB).filter_by(**{key: value}).count()
                        db_info = session.query(DB).filter_by(**{key: value}).order_by(DB.id).offset(limit_start).limit(
                            int(limit))
                    else:
                        count = session.query(DB).count()
                        db_info = session.query(DB).order_by(DB.id).offset(limit_start).limit(int(limit))
                else:
                    # TODO 普通用户只给有权限的DB,根据用户查Tagid, 根据Tagid查询出来关联的DBID，根据DBID返回主机详情
                    db_id_list = []
                    with DBContext('r') as session:
                        # 子查询查出来server_id
                        the_dbs = session.query(DBTag.db_id).filter(DBTag.tag_id.in_(
                            session.query(Tag.id).filter(or_(Tag.users.like('%{}%'.format(nickname))))))
                        for d in the_dbs:
                            db_id_list.append(d[0])
                        # 去重下列表,万一有重复的呢
                        set_db_id_list = set(db_id_list)
                    if key and value:
                        # 根据Keyvalue获取
                        count = session.query(DB).filter(DB.id.in_(set_db_id_list)).filter_by(
                            **{key: value}).count()
                        db_info = session.query(DB).filter(DB.id.in_(set_db_id_list)).filter_by(
                            **{key: value}).order_by(DB.id).offset(
                            limit_start).limit(int(limit))
                    else:
                        # 获取主机详情
                        count = session.query(DB).filter(DB.id.in_(set_db_id_list)).count()
                        db_info = session.query(DB).filter(DB.id.in_(set_db_id_list)).offset(
                            limit_start).limit(int(limit))

            for msg in db_info:
                tag_list = []
                data_dict = model_to_dict(msg)
                db_tags = session.query(Tag.tag_name).outerjoin(DBTag, Tag.id == DBTag.tag_id).filter(
                    DBTag.db_id == data_dict['id']).all()
                for t in db_tags:
                    tag_list.append(t[0])
                data_dict['create_time'] = str(data_dict['create_time'])
                data_dict['tag_list'] = tag_list
                db_list.append(data_dict)

        self.write(dict(code=0, msg='获取成功', count=count, data=db_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        db_code = data.get('db_code', None)
        db_host = data.get('db_host', None)
        db_port = data.get('db_port', 3306)
        db_user = data.get('db_user', None)
        db_pwd = data.get('db_pwd', None)
        db_env = data.get('db_env', None)
        proxy_host = data.get('proxy_host', None)
        db_type = data.get('db_type', 'mysql')
        db_version = data.get('db_version', None)
        db_mark = data.get('db_mark', '写')
        tag_list = data.get('tag_list', [])
        db_detail = data.get('db_detail', None)
        if not db_code or not db_host or not db_port or not db_user or not db_pwd or not db_env or not db_detail:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        with DBContext('r') as session:
            exist_id = session.query(DB.id).filter(DB.db_code == db_code, DB.db_host == db_host, DB.db_port == db_port,
                                                   DB.db_user == db_user, DB.db_env == db_env,
                                                   DB.proxy_host == proxy_host, DB.db_type == db_type,
                                                   db_version == db_version,
                                                   DB.db_mark == db_mark).first()
        if exist_id:
            return self.write(dict(code=-2, msg='不要重复记录'))

        with DBContext('w', None, True) as session:
            new_db = DB(db_code=db_code, db_host=db_host, db_port=db_port, db_user=db_user, db_pwd=db_pwd,
                        db_env=db_env, proxy_host=proxy_host, db_type=db_type, db_version=db_version, db_mark=db_mark,
                        db_detail=db_detail)
            session.add(new_db)

            all_tags = session.query(Tag.id).filter(Tag.tag_name.in_(tag_list)).order_by(Tag.id).all()
            if all_tags:
                for tag_id in all_tags:
                    session.add(DBTag(db_id=new_db.id, tag_id=tag_id[0]))

        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        db_id = data.get('id', None)
        db_code = data.get('db_code', None)
        db_host = data.get('db_host', None)
        db_port = data.get('db_port', 3306)
        db_user = data.get('db_user', None)
        db_pwd = data.get('db_pwd', None)
        db_env = data.get('db_env', None)
        proxy_host = data.get('proxy_host', None)
        db_type = data.get('db_type', 'mysql')
        db_version = data.get('db_version', None)
        db_mark = data.get('db_mark', '写')
        tag_list = data.get('tag_list', [])
        db_detail = data.get('db_detail', None)
        if not db_id or not db_code or not db_host or not db_port or not db_user or not db_pwd or not db_env or not db_detail:
            return self.write(dict(code=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            all_tags = session.query(Tag.id).filter(Tag.tag_name.in_(tag_list)).order_by(Tag.id).all()
            session.query(DBTag).filter(DBTag.db_id == db_id).delete(synchronize_session=False)
            if all_tags:
                for tag_id in all_tags:
                    session.add(DBTag(db_id=int(db_id), tag_id=tag_id[0]))

            session.query(DB).filter(DB.id == int(db_id)).update({DB.db_code: db_code, DB.db_host: db_host,
                                                                  DB.db_port: db_port, DB.db_user: db_user,
                                                                  DB.db_pwd: db_pwd, DB.db_env: db_env,
                                                                  DB.proxy_host: proxy_host, DB.db_type: db_type,
                                                                  DB.db_version: db_version,
                                                                  DB.db_mark: db_mark, DB.db_detail: db_detail})

        return self.write(dict(code=0, msg='编辑成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        db_id = data.get('db_id', None)
        id_list = data.get('id_list', None)

        with DBContext('w', None, True) as session:
            if db_id:
                session.query(DB).filter(DB.id == int(db_id)).delete(synchronize_session=False)
                session.query(DBTag).filter(DBTag.db_id == int(db_id)).delete(synchronize_session=False)
            elif id_list:
                for i in id_list:
                    session.query(DB).filter(DB.id == i).delete(synchronize_session=False)
                    session.query(DBTag).filter(DBTag.db_id == i).delete(synchronize_session=False)
            else:
                return self.write(dict(code=1, msg='关键参数不能为空'))
        return self.write(dict(code=0, msg='删除成功'))


asset_db_urls = [
    (r"/v1/cmdb/db/", DBHandler)
]
if __name__ == "__main__":
    pass
