#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: common.py
@time: 18/12/12下午1:14
'''
import subprocess
import paramiko
import shortuuid

def exec_shell(cmd):
    '''执行shell命令函数'''
    sub2 = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = sub2.communicate()
    ret = sub2.returncode
    return ret,stdout.decode('utf-8').strip()

def getKeyFile(ssh_key):
    '''根据key内容临时生成一个key文件'''
    file_path = '/tmp/%s'%shortuuid.uuid()
    cmd = 'echo "%s" > %s && chmod 600 %s'%(ssh_key,file_path,file_path)
    ret,stdout = exec_shell(cmd)
    if ret == 0:
        return file_path
    else:
        return None



def remoteUpfile_Exec(ip,user,pwd,cmd,local_file,remote_file,port=22):
    '''ssh上传并执行bash for pwd'''
    t = paramiko.Transport((ip,port))
    t.connect(username=user, password=pwd)
    sftp = paramiko.SFTPClient.from_transport(t)
    sftp.put(local_file,remote_file)
    ssh = paramiko.SSHClient()
    ssh._transport = t
    stdin, stdout, stderr = ssh.exec_command(cmd)
    show_log = stdout.read().decode('utf-8').strip()
    t.close()
    return show_log

def remoteUpfile_Exec_KEY(ip,user,ssh_key,cmd,local_file,remote_file,port=22):
    '''ssh上传并执行bash for key'''
    private_key = paramiko.RSAKey.from_private_key_file(ssh_key)
    t = paramiko.Transport((ip,port))
    t.connect(username=user, pkey=private_key )
    sftp = paramiko.SFTPClient.from_transport(t)
    sftp.put(local_file,remote_file)
    ssh = paramiko.SSHClient()
    ssh._transport = t
    stdin, stdout, stderr = ssh.exec_command(cmd)
    show_log = stdout.read().decode('utf-8').strip()
    t.close()
    return show_log
