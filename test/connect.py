#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/3 10:24
# @Author  : Fred Yangxiaofei
# @File    : connect.py
# @Role    : 基于paramiko实现机器跳板+审计，这是CMDB第二版，现在不可用


import operator
import re
import textwrap
from libs.common import color_print, exec_shell
from models.server import Server, SystemUser, model_to_dict
from sqlalchemy import or_
from libs.db_context import DBContext
from sqlalchemy.sql import func
import os
import socket
import sys
from paramiko.py3compat import input
import paramiko
import termios
import tty
import fcntl
import signal
import struct
from paramiko.py3compat import u
from opssdk.operate import MyCryptV2

# Python3里面终端不能使用Delete退格，需要导入这个模块

BASE_DIR = os.path.abspath((os.path.dirname(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
print(LOG_DIR)


try:
    from test import interactive
except ImportError:
    from . import interactive

"""
1. 获取ssh， 获取channel

"""


class Nav():
    def __init__(self):
        self.channel = None
        self.ssh = None
        self.key_file_name = '/root/.ssh/id_rsa'
        self.vim_data = ''
        self.vim_flag = False
        self.stream = None
        self.screen = None
        self.vim_end_pattern = re.compile(r'\x1b\[\?1049', re.X)

    @staticmethod
    def print_nav():
        """
        Print prompt
        打印提示导航
        """
        msg = """\n\033[1;32m###    欢迎使用CloudOpenDevOps资产管理系统   ### \033[0m
        \n\033[1;32m###    注意：只显示状态为True的机器  ### \033[0m
        
        1) 输入 \033[32mID / 关键字\033[0m 进行登录.
        2) 输入 \033[32mP/p\033[0m 显示您有权限的主机.
        3) 输入 \033[32mG/g\033[0m 显示您有权限的标签.
        4) 输入 \033[32mH/h\033[0m 帮助.
        0) 输入 \033[32mQ/q\033[0m 退出.
        """
        print(textwrap.dedent(msg))

    def get_asset_info(self):
        '''获取资产信息'''
        server_list = []
        with DBContext('r') as session:
            server_data = session.query(Server).filter(
                Server.state == 'true').all()
            for data in server_data:
                data_dict = model_to_dict(data)
                data_dict['create_time'] = str(data_dict['create_time'])
                server_list.append(data_dict)

        return server_list

    @staticmethod
    def is_output(strings):
        newline_char = ['\n', '\r', '\r\n']
        for char in newline_char:
            if char in strings:
                return True
        return False
        # with DBContext('r') as session:
        #     server_info_list = session.query(Server.id, Server.ip, Server.port, Server.hostname, Server.admin_user,
        #                                      Server.detail).all()
        #
        #     return server_info_list

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
        """
        处理截获的命令
        :param data: 要处理的命令
        :return:返回最后的处理结果
        """
        command = ''
        try:
            self.stream.feed(data)
            # 从虚拟屏幕中获取处理后的数据
            for line in reversed(self.screen.buffer):
                line_data = "".join(
                    map(operator.attrgetter("data"), line)).strip()
                if len(line_data) > 0:
                    parser_result = self.command_parser(line_data)
                    if parser_result is not None:
                        # 2个条件写一起会有错误的数据
                        if len(parser_result) > 0:
                            command = parser_result
                    else:
                        command = line_data
                    break
        except Exception:
            pass
        # 虚拟屏幕清空
        self.screen.reset()
        return command

    def search(self, input_str=''):
        # 根据搜索内容进行判断连接什么主机
        with DBContext('r') as session:
            if input_str:
                try:
                    id_ = int(input_str)
                    print('根据ID进行连接, ID：{}'.format(id_))
                    server_info = session.query(Server.ip, Server.port).filter(
                        Server.id == id_).first()
                    if not server_info:
                        color_print('没有匹配到任何主机', color='red')
                        return None
                    else:
                        self.start_connect(id_)

                except (ValueError, TypeError):
                    # print('根据关键字进行匹配连接')
                    server_info_list = session.query(Server).filter(or_(
                        Server.ip.like('%{}%'.format(input_str)),
                        Server.hostname.like('%{}%'.format(input_str)),
                        Server.port.like('%{}%'.format(input_str)),
                        Server.admin_user.like('%{}%'.format(input_str)),
                        Server.detail.like('%{}%'.format(input_str)))).order_by(
                        Server.id).all()
                    server_info_count = session.query(Server).filter(or_(
                        Server.ip.like('%{}%'.format(input_str)),
                        Server.hostname.like('%{}%'.format(input_str)),
                        Server.port.like('%{}%'.format(input_str)),
                        Server.admin_user.like('%{}%'.format(input_str)),
                        Server.detail.like('%{}%'.format(input_str)))).order_by(
                        Server.id).count()

                    if server_info_count == 0:
                        color_print('没有匹配到任何主机', color='red')
                        return

                    if server_info_count == 1:
                        print('直接连接，不让用户再次选择了')
                        for msg in server_info_list:
                            print('连接主机IP：{}'.format(msg.ip))
                            self.start_connect(msg.id)

                    else:
                        # 让用户再次选择匹配出来的数据
                        line = '[%-3s] %-16s %-5s  %-' + str(30) + 's %-10s %s'
                        color_print(
                            line % ('ID', 'IP', 'Port', 'Hostname', 'AdminUser', 'Comment'), 'title')
                        for msg in server_info_list:
                            _id = msg.id
                            _ip = msg.ip
                            _port = msg.port
                            _hostname = msg.hostname
                            _admin_user = msg.admin_user
                            _detail = msg.detail
                            print(line % (_id, _ip, _port,
                                          _hostname, _admin_user, _detail))
                        print()

            else:
                # 如果没有输入就展现所有
                self.print_all_hosts()

    @staticmethod
    def get_win_size():
        """
        This function use to get the size of the windows!
        获得terminal窗口大小
        """
        if 'TIOCGWINSZ' in dir(termios):
            TIOCGWINSZ = termios.TIOCGWINSZ
        else:
            TIOCGWINSZ = '1074295912L'
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s)
        return struct.unpack('HHHH', x)[0:2]

    def set_win_size(self):
        """
        This function use to set the window size of the terminal!
        设置terminal窗口大小
        """
        try:
            win_size = self.get_win_size()
            self.channel.resize_pty(height=win_size[0], width=win_size[1])
        except Exception:
            pass

    # def get_log(self):
    #     """
    #     Logging user command and output.
    #     记录用户的日志
    #     """
    #     tty_log_dir = os.path.join(LOG_DIR, 'tty')
    #     date_today = datetime.datetime.now()
    #     date_start = date_today.strftime('%Y%m%d')
    #     time_start = date_today.strftime('%H%M%S')
    #     today_connect_log_dir = os.path.join(tty_log_dir, date_start)
    #     log_file_path = os.path.join(today_connect_log_dir, '{}_{}_{}' .format('sudo_test','assetname', time_start)
    #
    #     try:
    #         mkdir(os.path.dirname(today_connect_log_dir), mode=777)
    #         mkdir(today_connect_log_dir, mode=777)
    #     except Exception as e:
    #         print(e)
    #         print('创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))
    #         # raise ServerError('创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))
    #
    #     try:
    #         log_file_f = open(log_file_path + '.log', 'a')
    #         log_time_f = open(log_file_path + '.time', 'a')
    #     except IOError:
    #         print('创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)
    #         # raise ServerError('创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)
    #     pid = os.getpid()
    #     # if self.login_type == 'ssh':  # 如果是ssh连接过来，记录connect.py的pid，web terminal记录为日志的id
    #     #     pid = os.getpid()
    #     #     self.remote_ip = remote_ip  # 获取远端IP
    #     # else:
    #     #     pid = 0
    #
    #     # log = Log(user=self.username, host=self.asset_name, remote_ip=self.remote_ip, login_type=self.login_type,
    #     #           log_path=log_file_path, start_time=date_today, pid=pid)
    #     # log.save()
    #     # # if self.login_type == 'web':
    #     # #     log.pid = log.id  # 设置log id为websocket的id, 然后kill时干掉websocket
    #     # #     log.save()
    #     #
    #     # log_file_f.write('Start at %s\r\n' % datetime.datetime.now())
    #     # return log_file_f, log_time_f, log

    def get_system_user(self):
        """
        获取系统用户，若查询到2个，就只return一个优先级高的
        :return:
        """
        system_user_list = []
        with DBContext('r') as session:
            system_user_cont = session.query(SystemUser).count()
            if system_user_cont == 1:
                # 只有一个用户，直接返回，用这个作为跳板的用户
                system_user_data = session.query(SystemUser).all()
                for data in system_user_data:
                    data_dict = model_to_dict(data)
                    data_dict['create_time'] = str(data_dict['create_time'])
                    data_dict['update_time'] = str(data_dict['update_time'])
                    if data_dict['platform_users']:
                        data_dict['platform_users'] = data_dict.get(
                            'platform_users', '').split(',')
                    system_user_list.append(data_dict)

            else:
                priority_max_info = session.query(
                    func.max(SystemUser.priority)).all()
                # return is list[tuple]
                priority_max_num = priority_max_info[0][0]
                system_user_data = session.query(SystemUser).filter(
                    SystemUser.priority == priority_max_num).first()
                data_dict = model_to_dict(system_user_data)
                data_dict['create_time'] = str(data_dict['create_time'])
                data_dict['update_time'] = str(data_dict['update_time'])
                if data_dict['platform_users']:
                    data_dict['platform_users'] = data_dict.get(
                        'platform_users', '').split(',')
                system_user_list.append(data_dict)

        # print(system_user_list)
        return system_user_list

        # for i in system_user_list:
        #     system_user_priority = i.get('priority')

    def get_connect_info(self, asset_id):
        """
        获取连接主机的信息，如:IP , Port , User
        使用推送过去的系统用户+密钥进行链接
        :return:
        """

        system_user_list = self.get_system_user()
        for i in system_user_list:
            system_user = i.get('system_user')
            mc = MyCryptV2()
            _private_key_txt = mc.my_decrypt(i.get('id_rsa'))
            # 这里需要写到本地文件

        with DBContext('r') as session:
            server_info = session.query(Server.ip, Server.port, Server.detail).filter(
                Server.id == asset_id).first()
            ip = server_info[0]
            port = server_info[1]
            detail = server_info[2]

        connect_info = {
            'ip': ip,
            'port': port,
            'system_user': system_user,
            'private_key_txt': _private_key_txt,
            'detail': detail
        }
        return connect_info

        # with DBContext('r') as session:
        #     connect_info = session.query(Server.ip, Server.port, AdminUser.system_user,
        #                                  ).outerjoin(AdminUser,
        #                                              AdminUser.admin_user == Server.admin_user).filter(Server.id == asset_id).first()
        #     # print(connect_info)
        #     if not connect_info:
        #         # color_print('没有匹配到任何主机', color='red')
        #         return False
        #
        #     return connect_info

    def get_connection(self, asset_id):
        """
        获取连接成功后的SSH
        :return:
        """
        connect_info = self.get_connect_info(asset_id)
        if not connect_info:
            # color_print('没有匹配到任何主机', color='red')
            return False
#        connect_info = [('172.16.0.120', 22, 'root')]
        ip = connect_info.get('ip')
        port = connect_info.get('port')
        user = connect_info.get('system_user')
        _private_key_txt = connect_info.get('private_key_txt')
        # 将Key写文件
        file_path = '/tmp/{}_private_key'.format(user)
        cmd = 'echo "{}" > {} && chmod 600 {}'.format(
            _private_key_txt, file_path, file_path)
        ret, stdout = exec_shell(cmd)
        if ret != 0:
            print('[ERROR]: PrivateKey文件写文件失败')
            return False

        private_key = paramiko.RSAKey.from_private_key_file(file_path)
        try:
            ssh = paramiko.Transport(ip, port)
            ssh.connect(username=user, pkey=private_key)

            return ssh

        except Exception as e:
            print(e)

    def start_connect(self, asset_id):
        """
        开始连接服务器
        :return:
        """
        ssh = self.get_connection(asset_id)

        if not ssh:
            # color_print('创建SSH连接失败',color='red')
            return False
        win_size = self.get_win_size()
        self.channel = channel = ssh.open_session()
        channel.get_pty(term='xterm', height=win_size[0], width=win_size[1])
        channel.invoke_shell()
        try:
            signal.signal(signal.SIGWINCH, self.set_win_size)
        except Exception as e:
            print(e)

        # 这是官方的写法 和下面posix对应，但是没有日志记录
        # self.posix_shell(channel)
        self.posix_shell()

        # Shutdown channel socket
        channel.close()
        ssh.close()

    # 这是官方的写法，还没想好日志记录怎么做
    # def posix_shell(self):
    #     import select
    #
    #     oldtty = termios.tcgetattr(sys.stdin)
    #     try:
    #         tty.setraw(sys.stdin.fileno())
    #         tty.setcbreak(sys.stdin.fileno())
    #         self.channel.settimeout(0.0)
    #         f = open('handle.log', 'a+')
    #         tab_flag = False
    #         temp_list = []
    #         while True:
    #             r, w, e = select.select([self.channel, sys.stdin], [], [])
    #             if self.channel in r:
    #                 try:
    #                     x = self.channel.recv(1024)
    #                     if len(x) == 0:
    #                         sys.stdout.write('\r\n*** EOF\r\n')
    #                         break
    #                     if tab_flag:
    #                         if x.startswith('\r\n'):
    #                             pass
    #                         else:
    #                             f.write(x)
    #                             f.flush()
    #                         tab_flag = False
    #                     sys.stdout.write(x)
    #                     sys.stdout.flush()
    #                 except socket.timeout:
    #                     pass
    #             if sys.stdin in r:
    #                 x = sys.stdin.read(1)
    #                 if len(x) == 0:
    #                     break
    #                 if x == '\t':
    #                     tab_flag = True
    #                 else:
    #                     f.write(x)
    #                     f.flush()
    #                     self.channel.send(x)
    #
    #     finally:
    #         termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
    #     """
    #     Use paramiko channel connect server interactive.
    #     使用paramiko模块的channel，连接后端，进入交互式
    #     """
        # log_file_f, log_time_f, log = self.get_log()
        # termlog = TermLogRecorder(User.objects.get(id=self.user.id))
        # termlog.setid(log.id)
        # old_tty = termios.tcgetattr(sys.stdin)
        # pre_timestamp = time.time()
        # data = ''
        # input_mode = False
        # f = open('handle.log', 'a+')
        # tty_log = open('tty.log', 'a+')
        # try:
        #     tty.setraw(sys.stdin.fileno())
        #     tty.setcbreak(sys.stdin.fileno())
        #     self.channel.settimeout(0.0)
        #
        #     while True:
        #         try:
        #             r, w, e = select.select([self.channel, sys.stdin], [], [])
        #             flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL, 0)
        #             fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flag|os.O_NONBLOCK)
        #         except Exception:
        #             pass
        #
        #         if self.channel in r:
        #             try:
        #                 x = self.channel.recv(10240)
        #                 if len(x) == 0:
        #                     break
        #
        #                 index = 0
        #                 len_x = len(x)
        #                 while index < len_x:
        #                     try:
        #                         n = os.write(sys.stdout.fileno(), x[index:])
        #                         sys.stdout.flush()
        #                         index += n
        #                     except OSError as msg:
        #                         if msg.errno == errno.EAGAIN:
        #                             continue
        #                 now_timestamp = time.time()
        #                 sys.stdout.write(x)
        #                 sys.stdout.flush()
        #                 # termlog.write(x)
        #                 # termlog.recoder = False
        #                 # log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(x)))
        #                 # log_time_f.flush()
        #                 # log_file_f.write(x)
        #                 # log_file_f.flush()
        #                 # pre_timestamp = now_timestamp
        #                 # log_file_f.flush()
        #
        #                 self.vim_data += str(x)
        #                 if input_mode:
        #                     data += str(x)
        #
        #             except socket.timeout:
        #                 pass
        #
        #         if sys.stdin in r:
        #             try:
        #                 x = os.read(sys.stdin.fileno(), 4096)
        #             except OSError:
        #                 pass
        #             # termlog.recoder = True
        #             input_mode = True
        #             if self.is_output(str(x)):
        #                 # 如果len(str(x)) > 1 说明是复制输入的
        #                 if len(str(x)) > 1:
        #                     data = x
        #                 match = self.vim_end_pattern.findall(self.vim_data)
        #                 if match:
        #                     if self.vim_flag or len(match) == 2:
        #                         self.vim_flag = False
        #                     else:
        #                         self.vim_flag = True
        #                 elif not self.vim_flag:
        #                     self.vim_flag = False
        #                     data = self.deal_command(data)[0:200]
        #                     if data is not None:
        #                         print(data)
        #                         tty_log.write(str(x))
        #                         #TtyLog(log=log, datetime=datetime.datetime.now(), cmd=data).save()
        #                 data = ''
        #                 self.vim_data = ''
        #                 input_mode = False
        #
        #             if len(x) == 0:
        #                 break
        #             self.channel.send(x)
        #
        # finally:
        #     termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        #     print('End time is %s' % datetime.datetime.now())
        # log_file_f.close()
        # log_time_f.close()
        # termlog.save()
        # log.filename = termlog.filename
        # log.is_finished = True
        # log.end_time = datetime.datetime.now()
        # log.save()
    # def posix_shell(self):
    #     import select
    #
    #     oldtty = termios.tcgetattr(sys.stdin)
    #     data = ''
    #     input_mode = False
    #     try:
    #         tty.setraw(sys.stdin.fileno())
    #         tty.setcbreak(sys.stdin.fileno())
    #         self.channel.settimeout(0.0)
    #         f = open('handle.log', 'a+')
    #         tty_log = open('tty.log', 'a+')
    #
    #         while True:
    #             try:
    #                 r, w, e = select.select([self.channel, sys.stdin], [], [])
    #                 flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL, 0)
    #                 fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flag | os.O_NONBLOCK)
    #             except Exception as e:
    #                 pass
    #
    #             if self.channel in r:
    #
    #                 try:
    #                     x = u(self.channel.recv(1024))
    #                     if len(x) == 0:
    #                         #sys.stdout.write("\r\n*** EOF\r\n")
    #                         break
    #                     # index = 0
    #                     # len_x = len(x)
    #                     # while index < len_x:
    #                     #     print('x ---->',x)
    #                     #     print('x---type--->',x)
    #                     #
    #                     #     try:
    #                     #         n = os.write(sys.stdout.fileno(), x[index:])
    #                     #         print('n-->',n)
    #                     #         print(type(n))
    #                     #         sys.stdout.flush()
    #                     #         index += n
    #                     #     except OSError as msg:
    #                     #         if msg.errno == errno.EAGAIN:
    #                     #             continue
    #                     f.write(x)
    #                     f.flush()
    #                     # sys.stdout.write(x)
    #                     # sys.stdout.flush()
    #                     self.vim_data += x
    #                     if input_mode:
    #                         data += x
    #
    #                 except socket.timeout:
    #                     pass
    #             if sys.stdin in r:
    #                 x = sys.stdin.read(1)
    #                 if len(x) == 0:
    #                     break
    #                 self.channel.send(x)
    #                 # print('sys....')
    #                 # try:
    #                 #     x = os.read(sys.stdin.fileno(), 4096)
    #                 # except OSError:
    #                 #     pass
    #                 # # termlog.recoder = True
    #                 # input_mode = True
    #                 # if self.is_output(str(x)):
    #                 #
    #                 #     # 如果len(str(x)) > 1 说明是复制输入的
    #                 #     if len(str(x)) > 1:
    #                 #         data = x
    #                 #     match = self.vim_end_pattern.findall(self.vim_data)
    #                 #     if match:
    #                 #         if self.vim_flag or len(match) == 2:
    #                 #             self.vim_flag = False
    #                 #         else:
    #                 #             self.vim_flag = True
    #                 #     elif not self.vim_flag:
    #                 #         self.vim_flag = False
    #                 #         data = self.deal_command(data)[0:200]
    #                 #         if data is not None:
    #                 #             tty_log.write(data)
    #                 #             # TtyLog(log=log, datetime=datetime.datetime.now(), cmd=data).save()
    #                 #     data = ''
    #                 #     self.vim_data = ''
    #                 #     input_mode = False
    #                 #
    #                 # if len(x) == 0:
    #                 #     break
    #                 # self.channel.send(x)
    #                 # if sys.stdin in r:
    #                 #     x = sys.stdin.read(1)
    #                 #     if len(x) == 0:
    #                 #         break
    #                 #     self.channel.send(x)
    #
    #     finally:
    #         termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
    #         # f.write('End time is %s' % datetime.datetime.now())
    #         # f.close()
    #         # tty_log.write(x)

    def posix_shell(self):
        import select
        tty_log = open('tty.log', 'a+')
        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            self.channel.settimeout(0.0)

            while True:
                r, w, e = select.select([self.channel, sys.stdin], [], [])
                if self.channel in r:
                    try:
                        x = u(self.channel.recv(1024))
                        if len(x) == 0:
                            sys.stdout.write("\r\n*** EOF\r\n")
                            break
                        sys.stdout.write(x)
                        tty_log.write(x)
                        tty_log.flush()
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    self.channel.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    # def connect_test(self):
    #     connect_info = {
    #         'ip': '172.16.0.101',
    #         'port': 22,
    #         'username': 'root',
    #         'key_file_name': '/root/.ssh/id_rsa'
    #     }
    #
    #     private_key = paramiko.RSAKey.from_private_key_file(connect_info.get('key_file_name'))
    #     t = paramiko.Transport(connect_info.get('ip'), connect_info.get('port'))
    #     t.connect(username=connect_info.get('username'), pkey=private_key)
    #     chan = t.open_session()
    #     # 获取一个终端
    #     chan.get_pty()
    #     # 激活器
    #     chan.invoke_shell()
    #
    #     # 获取原tty属性
    #     oldtty = termios.tcgetattr(sys.stdin)
    #     try:
    #         # 为tty设置新属性
    #         # 默认当前tty设备属性：
    #         #   输入一行回车，执行
    #         #   CTRL+C 进程退出，遇到特殊字符，特殊处理。
    #
    #         # 这是为原始模式，不认识所有特殊符号
    #         # 放置特殊字符应用在当前终端，如此设置，将所有的用户输入均发送到远程服务器
    #         tty.setraw(sys.stdin.fileno())
    #         chan.settimeout(0.0)
    #
    #         while True:
    #             # 监视 用户输入 和 远程服务器返回数据（socket）
    #             # 阻塞，直到句柄可读
    #             r, w, e = select.select([chan, sys.stdin], [], [], 1)
    #             if chan in r:
    #                 try:
    #                     x = u(chan.recv(1024))
    #                     if len(x) == 0:
    #                         print('\r\n*** EOF\r\n')
    #                         break
    #                     sys.stdout.write(x)
    #                     sys.stdout.flush()
    #                 except socket.timeout:
    #                     pass
    #             if sys.stdin in r:
    #                 x = sys.stdin.read(1)
    #                 if len(x) == 0:
    #                     break
    #                 chan.send(x)
    #
    #     finally:
    #
    #         # 重新设置终端属性,必须设置,否则再次登录后无法使用
    #         termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
    #
    #     chan.close()
    #     t.close()

    def print_all_hosts(self):
        system_user_list = self.get_system_user()
        for i in system_user_list:
            system_user = i.get('system_user')

        line = '[%-3s] %-16s %-5s  %-' + str(30) + 's %-10s %s'
        color_print(line % ('ID', 'IP', 'Port', 'Hostname',
                            'SystemUser', 'Comment'), 'title')
        server_list = self.get_asset_info()
        for host in server_list:
            _id = host.get('id')
            _ip = host.get('ip')
            _port = host.get('port')
            _hostname = host.get('hostname')
            _system_user = system_user
            _detail = host.get('detail')
            # print(line %(_id, _hostname, _port, _admin_user, _detail))
            print(line % (_id, _ip, _port, _hostname, _system_user, _detail))
        print()

    def try_connect(self):
        pass


def main():
    nav = Nav()
    # 这里需要加一个登陆判断
    nav.print_nav()

    try:
        while True:
            try:
                option = input("\033[1;32mOpt or ID>:\033[0m ").strip()
            except EOFError:
                nav.print_nav()
                continue
            except KeyboardInterrupt:
                sys.exit(0)
            if option in ['P', 'p', '\n', '']:
                nav.search()
                # nav.print_search_result()
                continue
            # if option.startswith('/'):
            #     nav.search(option.lstrip('/'))
            #     nav.print_all_hosts()
            # elif gid_pattern.match(option):
            #     nav.get_asset_group_member(str_r=option)
            #     nav.print_search_result()
            # elif option in ['G', 'g']:
            #     nav.print_asset_group()
            #     continue
            # elif option in ['E', 'e']:
            #     nav.exec_cmd()
            #     continue
            # elif option in ['U', 'u']:
            #     nav.upload()
            # elif option in ['D', 'd']:
            #     nav.download()
            elif option in ['H', 'h']:
                nav.print_nav()
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                nav.search(option)

                # if len(nav.search_result) == 1:
                #     print('Only match Host:  %s ' % nav.search_result[0].hostname)
                #     nav.try_connect()
                # else:
                #     nav.print_search_result()

    except IndexError as e:
        color_print(e)
        # time.sleep(5)


if __name__ == '__main__':
    main()
#      obj = Nav()
#      obj.get_asset_info()
