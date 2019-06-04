#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/26 14:34
# @Author  : Fred Yangxiaofei
# @File    : test_asset_update.py
# @Role    : 自动获取资产信息


from libs.db_context import DBContext
from models.server import Server, ServerDetail, model_to_dict, AdminUser, AssetErrorLog
from libs.server.sync_public_key import RsyncPublicKey, start_rsync
from libs.server.collect_asset_info import get_server_sysinfo
from libs.web_logs import ins_log
import sqlalchemy
import fire


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
            ins_log.read_log('info', '[PASS]: No new server found, automatically skipping push public key')
            #  print('[PASS]: No new server found, automatically skipping push public key')

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
            # print('new_server_list-->', new_server_list)
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
                    error_log = '推送公钥失败, 错误信息：{}'.format(msg)
                    ins_log.read_log('error', error_log)
                    session.query(Server).filter(Server.ip == ip).update({Server.state: 'false'})
                    exist_ip = session.query(AssetErrorLog).filter(AssetErrorLog.ip == ip).first()
                    if exist_ip:
                        session.query(AssetErrorLog).filter(AssetErrorLog.ip == ip).update(
                            {AssetErrorLog.error_log: error_log})
                    else:
                        new_error_log = AssetErrorLog(ip=ip, error_log=error_log)
                        session.add(new_error_log)
                session.commit()

        return rsync_sucess_list

    def update_asset(self, host_info):
        """
        更新资产到数据库
        :param host_data: 主机返回的资产采集基础数据
        :return:
        """
        with DBContext('w') as session:
            for k, v in host_info.items():
                try:
                    if host_info[k].get('status'):
                        _sn = v.get('sn', None)
                        _hostname = v.get('host_name', None)
                        _cpu = v.get('cpu', None)
                        _cpu_cores = v.get('cpu_cores', None)
                        _memory = v.get('memory', None)
                        _disk = v.get('disk', None)
                        _os_type = v.get('os_type', None)
                        _os_kernel = v.get('os_kernel', None)
                        # _instance_id = v.get('instance_id', None)
                        # _instance_type = v.get('instance_type', None)
                        # _instance_state = v.get('instance_state', None)

                        exist_detail = session.query(ServerDetail).filter(ServerDetail.ip == k).first()
                        if not exist_detail:
                            # 不存在就新建
                            new_server_detail = ServerDetail(ip=k, sn=_sn, cpu=_cpu, cpu_cores=_cpu_cores,
                                                             memory=_memory, disk=_disk,
                                                             os_type=_os_type, os_kernel=_os_kernel)
                            session.add(new_server_detail)
                            session.commit()
                            session.query(Server).filter(Server.ip == k).update(
                                {Server.hostname: _hostname, Server.state: 'true'})
                            session.commit()
                        else:
                            # 存在就更新
                            session.query(ServerDetail).filter(ServerDetail.ip == k).update({
                                ServerDetail.sn: _sn, ServerDetail.ip: k,
                                ServerDetail.cpu: _cpu, ServerDetail.cpu_cores: _cpu_cores,
                                ServerDetail.disk: _disk, ServerDetail.memory: _memory,
                                ServerDetail.os_type: _os_type, ServerDetail.os_kernel: _os_kernel,
                            })

                            session.query(Server).filter(Server.ip == k).update(
                                {Server.hostname: _hostname, Server.state: 'true'})
                            session.commit()
                except sqlalchemy.exc.IntegrityError as e:
                    ins_log.read_log('error', e)
                    # 状态改为Flse->删除主机Detail--记录错误信息
                    session.query(Server).filter(Server.ip == k).update({Server.state: 'false'})
                    session.query(ServerDetail).filter(ServerDetail.ip == k).delete(
                        synchronize_session=False)

                    exist_ip = session.query(AssetErrorLog).filter(AssetErrorLog.ip == k).first()
                    error_log = str(e)
                    if exist_ip:
                        session.query(AssetErrorLog).filter(AssetErrorLog.ip == k).update(
                            {AssetErrorLog.error_log: error_log})
                    else:
                        new_error_log = AssetErrorLog(ip=k, error_log=error_log)
                        session.add(new_error_log)

                    session.commit()
                    return False

    def get_host_info(self):
        '''获取主机信息，并写入数据库'''
        id_list = self.check_server_state()
        with DBContext('r') as session:
            for i in id_list:
                server_list = session.query(Server.ip, Server.port, AdminUser.system_user).outerjoin(AdminUser,
                                                                                                     AdminUser.admin_user == Server.admin_user).filter(
                    Server.id == i).all()
                asset_data = get_server_sysinfo(server_list)
                ins_log.read_log('info', '资产信息：{}'.format(asset_data))
                self.update_asset(asset_data)


def main(state):
    """
    机器状态,分为:new, true, false
    new: 表示新加的机器
        1. 先推送密钥
        2. 多进程使用absible获取主机资产信息
        3. 将资产信息写入/更新到数据库

    true: 表示已经可以正常免密钥登陆
        1. 多进程使用absible获取主机资产信息
        2. 将资产信息写入/更新到数据库

    false: 表示主机可能配置有问题,无法正常更新资产
        1. 将错误信息记录数据库
    :param state:  机器的状态
    :return:
    """

    obj = AssetServerAUtoUpdate(state)
    if state == 'new':
        if not obj.rsync_public_key():
            # 如果没有发现有新增的主机,直接PASS
            return
        obj.get_host_info()
    elif state == 'true':
        obj.get_host_info()


def new_tail_data():
    main('new')


def true_tail_data():
    main('true')


if __name__ == '__main__':
    fire.Fire(main)
