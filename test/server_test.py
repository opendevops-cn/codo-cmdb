#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/22 18:51
# @Author  : Fred Yangxiaofei
# @File    : server_test.py
# @Role    : 推送公钥、采集主机信息, 这个是使用多进程推送脚本文件获取的，暂不使用，目前改成了Ansible


import os
import json
import paramiko
from settings import PUBLIC_KEY
from models.server import SSHConfigs, Server
from libs.db_context import DBContext
# from websdk.db_context import DBContext
from libs.common import remote_upload_file, get_key_file, exec_shell, exec_thread

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RsyncPublicKey():
    def __init__(self):
        self.msg = ""

    def init_rsa(self):
        '''Server端生成秘钥对'''
        cmd = 'ssh-keygen -t rsa -P "" -f {}/id_rsa'.format(os.path.dirname(PUBLIC_KEY))
        code, ret = exec_shell(cmd)
        if code == 0:
            return True
        else:
            return False

    def save_of(self):
        '''把读取或者生成的秘钥信息保存到SQL'''
        with open('%s/id_rsa' % os.path.dirname(PUBLIC_KEY), 'r') as id_rsa, open(
                '%s/id_rsa.pub' % os.path.dirname(PUBLIC_KEY), 'r') as id_rsa_pub:
            with DBContext('w') as session:
                new_config = SSHConfigs(name='cmdb', id_rsa=id_rsa.read(), id_rsa_pub=id_rsa_pub.read())
                session.add(new_config)
                session.commit()

    def check_rsa(self):
        """
        检查CMDB 密钥配置,没有则创建新的写入数据库
        :return:
        """
        with DBContext('r') as session:
            # 这张表里面直有一条信息，名字：cmdb， 一对密钥
            exist_rsa = session.query(SSHConfigs.id).filter(SSHConfigs.name == 'cmdb').first()
            if not exist_rsa:
                # 检查本地是否存在
                local_id_rsa_exist = os.path.exists('{}/id_rsa'.format(os.path.dirname(PUBLIC_KEY)))
                if not local_id_rsa_exist:
                    check_rsa = self.init_rsa()
                    if not check_rsa:
                        return False
                self.save_of()
                return True
            else:
                return True

    def sync_key(self, host):
        """
        批量下发server端公钥到client端
        :param host: 主机信息，IP端口用户密码
        :return:
        """
        if not isinstance(host, list):
            raise ValueError()

        ip = host[0][0]
        port = host[0][1]
        user = host[0][2]
        user_key = host[0][3]
        cmd = '[ ! -d /root/.ssh ] && mkdir /root/.ssh ; ' \
              '[ ! -f /root/.ssh/authorized_keys ] && touch /root/.ssh/authorized_keys;  ' \
              'grep -c "`cat /tmp/id_rsa.pub`" ~/.ssh/authorized_keys >> /dev/null;' \
              '[ $? == 0 ] || cat /tmp/id_rsa.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo ok'
        # 将key写到本地
        ssh_key_file = get_key_file(user_key)
        if ssh_key_file:
            try:
                # print('CMD-->',cmd)
                res = remote_upload_file(ip, user, ssh_key_file, cmd, PUBLIC_KEY, '/tmp/id_rsa.pub', port)
                # print('res--->',res)
                if res[0] == 'ok':
                    # self.msg = True, '{}, 推送完成'.format(ip)
                    self.msg = {
                        'status': True,
                        'ip': ip,
                        'msg': '推送成功'
                    }
                else:
                    # 状态改为False
                    # self.msg = False, '{}, 推送失败'.format(ip)
                    self.msg = {
                        'status': False,
                        'ip': ip,
                        'msg': '推送失败'
                    }
            except paramiko.ssh_exception.AuthenticationException:
                # self.msg = False, '{}, 认证失败，请检查管理用户Key是否正确'.format(ip)
                self.msg = {
                    'status': False,
                    'ip': ip,
                    'msg': '认证失败，请检查管理用户Key是否正确'
                }

            except Exception as e:
                # self.msg = False, '{}, {}'.format(ip,e)
                self.msg = {
                    'status': False,
                    'ip': ip,
                    'msg': '{}'.format(e)
                }

        # print(self.msg)
        return self.msg


class GetServerData():
    def __init__(self):
        self.file_name = 'sysinfo.py'
        self.file_path = '{}/libs/script/{}'.format(BASE_DIR, self.file_name)
        # self.msg = ""
        self.msg = dict()

    def check_file(self):
        is_exist = os.path.exists(self.file_path)
        if not is_exist:
            return False
        return True

    def copy_file_and_exec(self, host):
        if not self.check_file():
            self.msg = '{} Not Fount'.format(self.file_name)
            return False

        if not isinstance(host, list):
            raise ValueError()

        ip = host[0][0]
        port = host[0][1]
        user = host[0][2]
        # 这里已经推送玩publick key后就不再使用管理用户了，直接使用本机的Key登陆
        with DBContext('r') as session:
            cmdb_key = session.query(SSHConfigs.id_rsa).filter(SSHConfigs.name == 'cmdb').first()
        if not cmdb_key:
            return False, '{}, 认证失败，cmdb key不存在'.format(ip)
        else:
            cmdb_key = cmdb_key[0]
        cmd = 'python /tmp/sysinfo.py'

        ssh_key_file = get_key_file(cmdb_key)
        if ssh_key_file:
            try:
                # res_info，获取到的资产信息， error_info
                res_info, error_info = remote_upload_file(ip, user, ssh_key_file, cmd, self.file_path,
                                                          '/tmp/sysinfo.py',
                                                          port)
                if res_info:
                    self.msg = {
                        'status': True,
                        'data': {
                            ip: json.loads(res_info)
                        }
                    }
                    return self.msg
                else:

                    # self.msg = '{}获取资产信息失败，错误信息：{}'.format(ip, error_info)
                    self.msg = {
                        'status': False,
                        'data': {
                            ip: error_info
                        }
                    }
                    return self.msg
            except paramiko.ssh_exception.AuthenticationException:
                # self.msg = False, '{}, 认证失败，请检查Key是否正确'.format(ip)
                self.msg = {
                    'status': False,
                    'data': {
                        ip: '认证失败，请检查Key是否正确'
                    }
                }
            except Exception as e:
                print(e)

        return self.msg


def start_rsync(server_list):
    """
    多进程推送CMDB公钥
    :param server_list: CMDB主机列表
    :return:
    """
    sync_key_obj = RsyncPublicKey()
    return list(exec_thread(func=sync_key_obj.sync_key, iterable1=server_list))


def get_server_sysinfo(server_list):
    """
    多进程采集机器信息
    :param server_list: 主机列表
    :return:
    """
    server_sysinfo_obj = GetServerData()
    return list(exec_thread(func=server_sysinfo_obj.copy_file_and_exec, iterable1=server_list))


if __name__ == '__main__':
    pass
