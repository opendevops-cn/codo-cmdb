#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/15 14:44
# @Author  : Fred Yangxiaofei
# @File    : server_common.py
# @Role    : server公用方法，记录日志，更新资产,推送密钥，主要给手动更新资产使用

from models.server import Server, AssetErrorLog, ServerDetail
from libs.db_context import DBContext
from libs.web_logs import ins_log
from libs.server.sync_public_key import RsyncPublicKey, start_rsync
import sqlalchemy


def write_error_log(error_list):
    with DBContext('w') as session:
        for i in error_list:
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


def update_asset(asset_data):
    """
    更新资产到数据库
    :param host_data: 主机返回的资产采集基础数据
    :return:
    """
    with DBContext('w') as session:
        for host in asset_data:
            for k, v in host.items():
                try:
                    if host[k].get('status'):
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


def rsync_public_key(server_list):
    """
    推送PublicKey
    :return:
    """
    # server_info = [('47.100.231.147', 22, 'root', '-----BEGIN RSA PRIVATE KEYxxxxxEND RSA PRIVATE KEY-----', 'false')]
    ins_log.read_log('info', 'first, rsync public key to server')
    rsync_error_list = []
    rsync_sucess_list = []
    sync_key_obj = RsyncPublicKey()
    check = sync_key_obj.check_rsa()
    if check:
        res_data = start_rsync(server_list)
        for res in res_data:
            if not res.get('status'):
                rsync_error_list.append(res)
            else:
                rsync_sucess_list.append(res)

    if rsync_error_list:
        write_error_log(rsync_error_list)

    return rsync_sucess_list


def test():
    # 日志：
    # error_list = [{'status': False, 'ip': 'xxxxxxx', 'msg': '认证失败，请检查管理用户Key是否正确'}, {'status': False, 'ip': 'xxxxxxx', 'msg': '认证失败，请检查管理用户Key是否正确'}]
    # 资产更新
    # ass_data =[{'xxxxxxx': {'status': False, 'msg': 'Failed to connect to the host via ssh: Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password).'}}, {'47.101.50.185': {'status': False, 'msg': 'Failed to connect to the host via ssh: Permission denied (publickey,password).'}}, {'119.28.103.104': {'status': True, 'msg': '获取资产成功', 'sn': 'ad5d1ce7-8a14-47ce-8f10-8f3af3506721', 'host_name': 'OPS-SG_TX-01-salt-master01', 'cpu': 'Intel(R) Xeon(R) CPU E5-26xx v4', 'cpu_cores': 2, 'memory': '3.7G', 'disk': 150.0, 'os_type': 'CentOS 7.5.1804', 'os_kernel': '3.10.0-693.el7.x86_64'}}]
    pass


if __name__ == '__main__':
    pass
