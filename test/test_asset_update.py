#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/26 14:34
# @Author  : Fred Yangxiaofei
# @File    : test_asset_update.py
# @Role    : 自动获取资产信息, 这是基于多进程的，测试用的，暂不使用


from libs.db_context import DBContext
from models.server import Server, ServerDetail, model_to_dict, AdminUser, AssetErrorLog
from test.server_test import start_rsync, get_server_sysinfo, RsyncPublicKey


class AssetServerAUtoUpdate():
    def __init__(self, state):
        self.state = state

    def check_server_state(self):
        '''查询Server状态, 新建的推送Key并更新'''
        new_asset_list = []
        id_list = []
        with DBContext('r') as session:
            # 新加的资产,state:new
            new_asset = session.query(Server).filter(Server.state == self.state).all()
            for msg in new_asset:
                data_dict = model_to_dict(msg)
                data_dict['create_time'] = str(data_dict['create_time'])
                new_asset_list.append(data_dict)

            for i in new_asset_list:
                id_list.append(i.get('id'))

            return id_list

    def rsync_public_key(self):
        '''推送公钥到新加的主机里面'''
        id_list = self.check_server_state()
        if not id_list:
            print('[PASS]: No new server found, automatically skipping push public key')
            return

        # 根据ID列表查询,获取管理权限推送PublicKey到主机
        new_server_list = []
        rsync_sucess_list = []
        rsync_error_list = []
        with DBContext('r') as session:
            for i in id_list:
                connect_info = session.query(Server.ip, Server.port, AdminUser.system_user,
                                             AdminUser.user_key).outerjoin(AdminUser,
                                                                           AdminUser.admin_user == Server.admin_user).filter(
                    Server.id == i).all()
                new_server_list.append(connect_info)
        # 检查密钥
        sync_key_obj = RsyncPublicKey()
        check = sync_key_obj.check_rsa()
        if check:
            print('new_server_list-->',new_server_list)
            res_data = start_rsync(new_server_list)
            # print(res_data)
            for res in res_data:
                if not res.get('status'):
                    rsync_error_list.append(res)
                else:
                    # 只返回密钥推送成功的进行更新资产
                    rsync_sucess_list.append(res)

        if rsync_error_list:
            with DBContext('w') as session:
                for i in rsync_error_list:
                    ip = i.get('ip')
                    msg = i.get('msg')
                    error_log = 'IP:{} 推送公钥失败, 错误信息：{}'.format(ip, msg)
                    session.query(Server).filter(Server.ip == ip).update({Server.state: 'false'})
                    new_error_log = AssetErrorLog(error_log=error_log)
                    session.add(new_error_log)
                session.commit()

        return rsync_sucess_list

    def get_host_info(self):
        id_list = self.check_server_state()
        '''获取主机信息'''
        connect_server_list = []
        with DBContext('r') as session:
            for i in id_list:
                connect_info = session.query(Server.ip, Server.port, AdminUser.system_user).outerjoin(AdminUser,
                                                                                                      AdminUser.admin_user == Server.admin_user).filter(
                    Server.id == i).all()
                connect_server_list.append(connect_info)
        print('connect_server_list--->',connect_server_list)
        res_data = get_server_sysinfo(connect_server_list)
        print(res_data)
        return res_data

    def get_sucess_asset(self, hosts_data):
        """
        获取成功拿到资产信息的主机
        :return:
        """
        sucess_hosts_list = []
        with DBContext('w') as session:
            for hosts in hosts_data:
                if not hosts.get('status'):
                    print(hosts)

                    # 没拿到信息的，更改状态False
                    for k in hosts.get('data'):
                        print(k)
                        # 状态改为Flse->删除主机Detail--记录错误信息
                        # session.query(Server).filter(Server.ip == k).update({Server.state: 'false'})
                        # session.query(ServerDetail).filter(ServerDetail.ip == k).delete(
                        #     synchronize_session=False)
                        # error_log = 'IP:{},错误信息：{}'.format(k, e)
                        # new_error_log = AssetErrorLog(error_log=error_log)
                        # session.add(new_error_log)
                        # session.commit()
                        session.query(Server).filter(Server.ip == k).update({Server.state: 'false'})
                        session.commit()
                else:
                    sucess_hosts_list.append(hosts.get('data'))

        return sucess_hosts_list

    def update_asset(self, sucess_hosts_list):
        """
        更新资产到数据库
        :param host_data: 主机返回的资产采集基础数据
        :return:
        """
        # print(sucess_hosts_list)
        with DBContext('w') as session:
            for hosts in sucess_hosts_list:
                print(hosts)
                for k, v in hosts.items():
                    exist_detail = session.query(ServerDetail).filter(ServerDetail.ip == k).first()
                    try:
                        if not exist_detail:
                            new_server_detail = ServerDetail(ip=k, cpu=v.get('cpu'),
                                                             memory=v.get('memory'), disk=v.get('disk'),
                                                             disk_utilization=v.get('disk_utilization'),
                                                             instance_id=v.get('instance_id'),
                                                             instance_type=v.get('instance_type'),
                                                             os_distribution=v.get('os_distribution'),
                                                             os_version=v.get('os_version'), sn=v.get('sn'))
                            session.add(new_server_detail)
                            session.query(Server).filter(Server.ip == k).update(
                                {Server.hostname: v.get('hostname'), Server.state: 'true'})
                            session.commit()
                        else:
                            session.query(ServerDetail).filter(ServerDetail.ip == k).update({
                                ServerDetail.cpu: v.get('cpu'),
                                ServerDetail.memory: v.get('memory'),
                                ServerDetail.disk: v.get('disk'),
                                ServerDetail.disk_utilization: v.get(
                                    'disk_utilization'),
                                ServerDetail.os_version: v.get('os_version'),
                                ServerDetail.os_distribution: v.get(
                                    'os_distribution'),
                                ServerDetail.sn: v.get('sn'),
                            })

                        session.query(Server).filter(Server.ip == k).update(
                            {Server.hostname: v.get('hostname'), Server.state: 'true'})
                        session.commit()
                        # except sqlalchemy.exc.IntegrityError as e:
                    except Exception as e:
                        # 状态改为Flse->删除主机Detail--记录错误信息
                        session.query(Server).filter(Server.ip == k).update({Server.state: 'false'})
                        session.query(ServerDetail).filter(ServerDetail.ip == k).delete(
                            synchronize_session=False)
                        error_log = 'IP:{},错误信息：{}'.format(k, e)
                        new_error_log = AssetErrorLog(error_log=error_log)
                        session.add(new_error_log)
                        session.commit()
                        return False


def main(state):
    """
    机器状态,分为:new, true, false
    new: 表示新加的机器,更新资产前需要先推送主机密钥
    true: 表示已经可以连通,正常更新资产
    false: 表示主机可能配置有问题,无法正常更新资产
    :param state:
    :return:
    """
    obj = AssetServerAUtoUpdate(state)
    if state == 'new':
        # 1. 推送公钥
        if not obj.rsync_public_key():
            # 如果没有发现有新增的主机,直接PASS
            return

        # 2. 采集主机基本信息
        hosts_data = obj.get_host_info()
        sucess_hosts_list = obj.get_sucess_asset(hosts_data)
        # 将成功拿到数据的主机更新到数据库
        obj.update_asset(sucess_hosts_list)
    elif state == 'true':
        # 1. 直接采集主机信息
        hosts_data = obj.get_host_info()
        # 2. 采集到的信息更新到数据库
        sucess_hosts_list = obj.get_sucess_asset(hosts_data)
        obj.update_asset(sucess_hosts_list)

    else:
        pass


def new_tail_data():
    main('new')


def old_tail_data():
    main('true')


if __name__ == '__main__':
    main('new')
# fire.Fire(main)
