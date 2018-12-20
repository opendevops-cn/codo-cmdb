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
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志，基类
    """
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
        """
        初始化虚拟屏幕和字符流
        """
        self.stream = pyte.ByteStream()
        self.screen = pyte.Screen(80, 24)
        self.stream.attach(self.screen)
        #self.stream.feed('Hello')
    @staticmethod
    def command_parser(command):
        """
        处理命令中如果有ps1或者mysql的特殊情况,极端情况下会有ps1和mysql
        :param command:要处理的字符传
        :return:返回去除PS1或者mysql字符串的结果
        """
        result = None
        match = re.compile('\[?.*@.*\]?[\$#]\s').split(command)
        if match:
            # 只需要最后的一个PS1后面的字符串
            result = match[-1].strip()
        else:
            # PS1没找到,查找mysql
            match = re.split('mysql>\s', command)
            if match:
                # 只需要最后一个mysql后面的字符串
                result = match[-1].strip()
        return result

    def deal_command(self, data):
        """ 有问题
        处理截获的命令
        :param data: 要处理的命令
        :return:返回最后的处理结果
        """
        command = ''
        try:
            print('1111')
            print(data)
            self.stream.feed(data)
            print(2222)
            # # 从虚拟屏幕中获取处理后的数据
            command = self.command_parser(data)
            #for line in reversed(self.screen.buffer):
                #print(line)
            #     line_data = "".join(map(operator.attrgetter("data"), line)).strip()
            #     if len(line_data) > 0:
            #         parser_result = self.command_parser(line_data)
            #         if parser_result is not None:
            #             # 2个条件写一起会有错误的数据
            #             if len(parser_result) > 0:
            #                 command = parser_result
            #         else:
            #             command = line_data
            #         break
        except Exception as e:
            print(e)
        # 虚拟屏幕清空
        self.screen.reset()
        return command

    def get_connection(self,ele):
        """
        获取连接成功后的ssh
        """
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







