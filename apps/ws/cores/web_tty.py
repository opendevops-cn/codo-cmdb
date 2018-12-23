#!/usr/bin/env python
#encoding:utf-8
import os
import django
import paramiko
import pyte
import socket
import re
import time
import json

os.environ['DJANGO_SETTINGS_MODULE'] = 'ops.settings'
django.setup()

from assets.models.server import Server,RecorderLog
from apps.ws.cores.api import get_asset_info
from libs.cores import initOSS_obj

class Tty(object):
    def __init__(self, asset):
        self.ip = None
        self.port = 22
        self.ssh = None
        self.channel = None
        self.asset = asset
        self.vim_flag = False
        self.vim_end_pattern = re.compile(r'\x1b\[\?1049', re.X)
        self.vim_data = ''
        self.stream = None
        self.screen = None
        self.__init_screen_stream()

    def __init_screen_stream(self):
        self.stream = pyte.ByteStream()
        self.screen = pyte.Screen(80, 24)
        self.stream.attach(self.screen)

    def get_connection(self,ele):
        connect_info = get_asset_info(self.asset)   # {'username': u'root', 'ip': u'172.16.0.8', 'password': 'shinezone2015', 'hostname': u'172.16.0.8', 'port': 22}
        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        # ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(connect_info.get('ip'),
                        port=connect_info.get('port'),
                        username=connect_info.get('username'),
                        #password=connect_info.get('password'),
                        look_for_keys=True,   #如果key已打通,则无需密码,True为开启
                        allow_agent=False,
                        timeout=5)

        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException):
            ele.write_message('认证失败 Authentication Error.')
        except socket.error:
            ele.write_message('端口或者IP地址可能不对 Connect SSH Socket Port or IP Error, Please Correct it.')
        else:
            self.ssh = ssh
            return ssh

class TermLogRecorder():
    def __init__(self,log):
        self.log = log
        self.Recorder_log = {}
        self.StartTime = time.time()

    def write(self,msg):
        self.Recorder_log[str(time.time() - self.StartTime)] = msg

    def save(self):
        data = json.dumps(self.Recorder_log)
        oss_obj = initOSS_obj()
        if oss_obj:
            oss_file_name = oss_obj.setObj(data)
            if oss_file_name:   #对象put oss成功
                self.log.record_name = oss_file_name
                self.log.save()
            else:
                RecorderLog(log=self.log,data=data).save()
        else:
            # 回放日志存储到Mysql
            RecorderLog(log=self.log,data=data).save()







