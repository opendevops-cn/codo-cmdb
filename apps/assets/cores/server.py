#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: server.py
@time: 18/12/11下午1:56
'''
from libs.ansibleAPI.runner import Runner
from ops.settings import BASE_DIR
from assets.models import server as models
from apps.ws.cores.api import get_asset_info
from libs.common import remoteUpfile_Exec,remoteUpfile_Exec_KEY,getKeyFile
from ops.settings import PUBLIC_KEY
import json
import os
import threading
from django.core import exceptions

def rsyncHostData(data):
    '''更新获取到的资产信息入库CMDB'''
    try:
        for k,v in data.items():
            models.Server.objects.filter(ip=k).update(
                hostname=v.get('hostname'),
                os_version=v.get('os_version'),
                os_distribution=v.get('os_distribution'),
                sn=v.get('sn'),
                cpu=v.get('cpu'),
                memory=v.get('memory'),
                disk=v.get('disk')
            )
        return None
    except Exception as e:
        return e

class rsyncPublicKey():
    '''推送公钥到主机,实现免秘钥'''
    def __init__(self,hosts):
        self.hosts = hosts
        self.lock = threading.Lock()
        self.Error = {}

    def start(self):
        threads = [threading.Thread(target=self.exec, args=(host,)) for host in self.hosts]
        for start_t in threads:
            start_t.start()
        for join_t in threads:
            join_t.join()
        print('Error----->',self.Error)
        return self.Error

    def exec(self,host):
        try:
            connect_info = get_asset_info(host)
            if connect_info:
                cmd = '[ ! -d /root/.ssh ] && mkdir /root/.ssh ; ' \
                      '[ ! -f /root/.ssh/authorized_keys ] && touch /root/.ssh/authorized_keys;  ' \
                      'cat /tmp/id_rsa.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo ok'
                print(cmd)
                ssh_key = connect_info.get('ssh_key')
                if ssh_key:
                    ssh_key_file = getKeyFile(ssh_key)
                    if ssh_key_file:
                        res = remoteUpfile_Exec_KEY(connect_info.get('ip'),connect_info.get('username'),ssh_key_file,
                                       cmd,PUBLIC_KEY,'/tmp/id_rsa.pub',connect_info.get('port'))
                    else:
                        self.lock.acquire()
                        self.Error[connect_info.get('hostname')] = '秘钥文件生成失败'
                        self.lock.release()
                else:
                    res = remoteUpfile_Exec(connect_info.get('ip'),connect_info.get('username'),connect_info.get('password'),
                                   cmd,PUBLIC_KEY,'/tmp/id_rsa.pub',connect_info.get('port'))
                print(res)
                if res != 'ok':
                    self.lock.acquire()
                    self.Error[connect_info.get('hostname')] = '公钥推送失败'
                    self.lock.release()
            else:
                self.lock.acquire()
                self.Error[host.hostname] = str('该主机未绑定管理用户')
                self.lock.release()

        except Exception as e:
            print(e)
            self.lock.acquire()
            self.Error[host.hostname] = str(e)
            self.lock.release()


class getHostData_SSH():
    '''通过paramiko+多线程 批量获取主机资产'''
    pass

class getHostData():
    '''通过AnsibleAPI 批量获取主机资产信息'''
    def __init__(self,hosts):
        self.host_list = hosts
        self.Error_host = []
        self.file_name = 'sysinfo.py'
        self.status = True
        self.msg = None
        self.data = {}

    @property
    def check_file(self):
        '''检查资产获取脚本是否存在'''
        flag = False
        self.file_path = '%s/libs/script/%s'%(BASE_DIR,self.file_name)
        is_exit = os.path.exists(self.file_path)
        if is_exit: flag = True
        return flag

    def get_host_data(self):
        '''获取主机资产信息'''
        self.copy_file()
        if self.status:
            self.exec_file()
        return self.status,self.msg

    def copy_file(self):
        '''复制脚本到主机'''
        runner = Runner(
            module_name="copy",
            module_args="src=%s dest=/tmp/ backup=yes"%self.file_path,
            remote_user="root",
            pattern="all",
            hosts=self.host_list
        )
        result = runner.run()
        if result['dark']:
            for err_host in result['dark']:
                self.Error_host.append(err_host)
            self.msg = '[Error] copy file faild => %s'%self.Error_host
            self.status = False

    def exec_file(self):
        '''执行脚本并接收结果'''
        runner = Runner(
            module_name="shell",
            module_args="/usr/bin/python /tmp/%s"%self.file_name,
            remote_user="root",
            pattern="all",
            hosts=self.host_list
        )
        result = runner.run()
        if result['dark']:
            for err_host in result['dark']:
                self.Error_host.append(err_host)
            self.msg = '[Error] exec sysinfo faild => %s'%self.Error_host
            self.status = False
        else:
            for k,v in result['contacted'].items():
                self.data[k] = json.loads(v['stdout'])




class multiAddServer():
    def __init__(self,data):
        self.data = data
        self.Error_list = {}
    def start(self):
        for line in self.data:
            data = line.strip().split(' ')
            print(data)
            if len(data) == 4:
                print('关联管理用户')
                try:
                    models.Server.objects.create(hostname=data[0],ip=data[1],port=data[2],admin_user=models.AdminUser.objects.get(name=data[3]))
                except Exception as e:
                    print(e)
                    self.Error_list[data[0]] = str(e)
            elif len(data) == 5:
                print('不关联管理用户')
                try:
                    models.Server.objects.create(hostname=data[0],ip=data[1],port=data[2],username=data[3],password=data[4])
                except Exception as e:
                    print(e)
                    self.Error_list[data[0]] = str(e)
            else:
                self.Error_list[data[0]] = '提交的格式不正确'
        print('err->',self.Error_list)