#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/22 18:53
# @Author  : Fred Yangxiaofei
# @File    : common.py
# @Role    : 公用方法

import sys
import time
import subprocess
import paramiko
import concurrent.futures
import re
from  libs.ansibleAPI.runner import Runner


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False

def color_print(msg, color='red', exits=False):
    '''颜色选择， 判断退出'''
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'yellow': '\033[1;33m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m',
                 'title': '\033[30;42m%s\033[0m',
                 'info': '\033[32m%s\033[0m'}
    msg = color_msg.get(color, 'red') % msg
    print(msg)
    if exits:
        time.sleep(2)
        sys.exit()
    return msg



def M2human(n):
    symbols = ('G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return '%sM' % n

def exec_setup(user, host):
    '''获取主机详情'''
    runner = Runner(
        module_name="setup",
        module_args="",
        remote_user=user,
        pattern="all",
        hosts=host
    )

    result = runner.run()
    print(result)
    if result['dark']:
        return False
    else:
        return result


def exec_shell(cmd):
    '''执行shell命令函数'''
    sub2 = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = sub2.communicate()
    ret = sub2.returncode
    return ret,stdout.decode('utf-8').strip()


def exec_thread(func, iterable1):
    ### 取所有主机 最多启动100个进程
    pool_num = 10
    with concurrent.futures.ProcessPoolExecutor(pool_num) as executor:
        results = executor.map(func, iterable1)
    return results


def get_key_file(ssh_key):
    '''根据key内容临时生成一个key文件'''
    #file_path = '/tmp/%s'%shortuuid.uuid()
    file_path = '/tmp/codo_cmdb_id_rsa'
    cmd = 'echo "{}" > {} && chmod 600 {}'.format(ssh_key,file_path,file_path)
    ret,stdout = exec_shell(cmd)
    if ret == 0:
        return file_path
    else:
        return None


# def remote_upload_file(ip,user,pwd,cmd,local_file,remote_file,port=22):
#     '''ssh上传并执行bash for pwd'''
#     t = paramiko.Transport((ip,port))
#     t.connect(username=user, password=pwd)
#     sftp = paramiko.SFTPClient.from_transport(t)
#     sftp.put(local_file,remote_file)
#     ssh = paramiko.SSHClient()
#     ssh._transport = t
#     stdin, stdout, stderr = ssh.exec_command(cmd)
#     show_log = stdout.read().decode('utf-8').strip()
#     t.close()
#     return show_log

def remote_upload_file(ip,user,ssh_key,cmd,local_file,remote_file,port=22):
    '''ssh上传并执行bash for key'''
    private_key = paramiko.RSAKey.from_private_key_file(ssh_key)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip,port=port,username=user, pkey=private_key, timeout=10)
    sftp = ssh.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command(cmd)
    show_log = stdout.read().decode('utf-8').strip()
    err_log = stderr.read().decode('utf-8').strip()
    #print(show_log,err_log)
    ssh.close()
    return show_log, err_log



def remote_exec_cmd(ip,user,ssh_key,cmd,port=22):
    '''ssh上传并执行bash for key'''
    private_key = paramiko.RSAKey.from_private_key_file(ssh_key)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip,port=port,username=user, pkey=private_key, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    show_log = stdout.read().decode('utf-8').strip()
    err_log = stderr.read().decode('utf-8').strip()
    #print(show_log,err_log)
    ssh.close()
    return show_log, err_log


def check_ip(ip_address):
    compile_ip=re.compile('^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
    if compile_ip.match(ip_address):
        return True
    else:
        return False