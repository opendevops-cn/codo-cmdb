#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/21 10:35
# @Author  : Fred Yangxiaofei
# @File    : sync_to_tagtree.py
# @Role    : 将CMDB里面的数据同步到作业配置---标签树下面



from models.server import Server, model_to_dict
from libs.db_context import DBContext
from libs.web_logs import ins_log
from settings import CODO_TASK_DB_INFO
from opssdk.operate.mysql import MysqlBase
import fire


class SyncTagTree():
    def __init__(self, mb):
        self.mb = mb
        self.server_table = 'asset_server'  # codo-task tagtree server表名字，默认无需更改
        self.server_tag_table = 'asset_server_tag'  # codo-tasks'tag tree server和标签的关联表

    def get_asset_server(self):
        """
        获取CMDB里面所有主机
        :return:
        """
        server_list = []
        with DBContext('r') as session:
            server_info = session.query(Server).order_by(Server.id).all()
        for msg in server_info:
            data_dict = model_to_dict(msg)
            data_dict['create_time'] = str(data_dict['create_time'])
            server_list.append(data_dict)

        return server_list

    def server_sync_task(self):
        """
        server信息同步到codo-task里面的tag tree数据库里面
        :return:
        """

        server_list = self.get_asset_server()
        if not server_list:
            print('[Error]: 没有获取到Server信息')
            return False

        cmdb_all_hostname_list = []
        for server in server_list:
            hostname = server.get('hostname')
            ip = server.get('ip')
            idc = server.get('idc')
            region = server.get('region')
            state = server.get('state')
            detail = server.get('detail')
            cmdb_all_hostname_list.append(hostname)

            exist_hostname = "select * from `{table_name}` WHERE `hostname`= '{hostname}';".format(
                table_name=self.server_table,
                hostname=hostname)
            # print(query_sql)
            if self.mb.query(exist_hostname):
                # print('主机名：{}是存在的,直接更新'.format(hostname))
                update_sql = "update `{table_name}` set `ip`='{ip}', `idc`='{idc}', `region`='{region}', `state`='{state}', `detail`='{detail}' where `hostname`='{hostname}';".format(
                    table_name=self.server_table, ip=ip, idc=idc, region=region, state=state, detail=detail,
                    hostname=hostname)
                self.mb.change(update_sql)
                # ins_log.read_log('info', '{}更新成功'.format(hostname))

            else:
                insert_sql = "insert into {table_name} (hostname,ip,idc,region,state,detail) VALUES ('{hostname}','{ip}','{idc}','{region}','{state}','{detail}');".format(
                    table_name=self.server_table, hostname=hostname, ip=ip, idc=idc, region=region, state=state,
                    detail=detail)
                self.mb.change(insert_sql)
                ins_log.read_log('info', '{}同步成功'.format(hostname))

        # 如果CMDB数据库里面删除了主机，标签树也删除 主机和主机关联表
        query_sql = "select hostname, id from {table_name};".format(table_name=self.server_table)

        target_data = self.mb.query(query_sql)
        for i in list(target_data):
            if i[0] not in cmdb_all_hostname_list:
                # print('我要删除这个name{}'.format(hostname[0]))
                delete_hostname_sql = "DELETE FROM {table_name} WHERE `hostname`='{hostname}';".format(
                    table_name=self.server_table, hostname=i[0])
                delete_id_sql = "DELETE FROM {table_name} where `server_id`={server_id};".format(
                    table_name=self.server_tag_table, server_id=i[1])
                self.mb.change(delete_hostname_sql)
                self.mb.change(delete_id_sql)
                ins_log.read_log('info', '{}删除成功'.format(i[0]))  # i[0]:hostname
                ins_log.read_log('info', '{}删除成功'.format(i[1]))  # i[1]: server_id


def main():
    """
    检查用户是否配置了同步codo-task MySQL信息,
    如果检测到配置，初始化MySQL，同步数据
    拿不到ORM直接使用原生SQL语句操作
    :return:
    """
    host = CODO_TASK_DB_INFO.get('host')
    port = CODO_TASK_DB_INFO.get('port')
    user = CODO_TASK_DB_INFO.get('user')
    passwd = CODO_TASK_DB_INFO.get('passwd')
    db = CODO_TASK_DB_INFO.get('db')

    if not host or not port or not user or not passwd or not db:
        print('[Error]: Not fount CODO_TASK_DB_INFO, auto pass...')
        return False

    try:
        mb = MysqlBase(**CODO_TASK_DB_INFO)
        obj = SyncTagTree(mb)
        obj.server_sync_task()

    except Exception as e:
        msg = '[Error]: 请确认下CODO_TASK 数据库配置信息是否正确'
        ins_log.read_log('error', e)
        return msg


if __name__ == '__main__':
    fire.Fire(main)
