#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/24 10:50
# @Author  : Fred Yangxiaofei
# @File    : sysinfo.py
# @Role    : 收集Linux基础信息
# @备注:不用Python收集是因为不想给客户机器装模块，影响用户机器环境等，直接用Linux Bash取值
# 二更：现在用的是Ansible获取，此脚本可用暂且不用
import subprocess
import json


def exec_shell(cmd):
    '''执行shell命令函数'''
    sub2 = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = sub2.communicate()
    ret = sub2.returncode
    if ret == 0:
        return stdout.decode('utf-8').strip()
    else:
        return None


def yum_check():
    yum_list = ['redhat-lsb', 'dmidecode']
    for i in yum_list:
        cmd = "rpm -qa | grep %s ; [ $? -ne '0' ] &&  yum install -y %s && echo '%s install ok'" % (i, i, i)
        exec_shell(cmd)


def collect():
    """
    收集资产基础信息
    :return:
    """
    data = {}
    data['sn'] = get_sn()  # SN
    data['hostname'] = exec_shell("hostname")  # 主机名
    data['os_distribution'] = get_os_distributor()  # OS版本，如:Centos Ubuntu
    data['os_version'] = get_os_version()  # 系统版本
    data['cpu'] = exec_shell("cat /proc/cpuinfo | grep 'cpu cores' | uniq | awk {'print $4'}") + 'Core'  # CPU核心数
    data['memory'] = get_memory()
    data['disk'] = exec_shell("df --total -h | grep total | awk {'print $2'}")  # 总空间
    data['disk_utilization'] = exec_shell("df --total -h | grep total | awk {'print $5'}")  # 总使用百分比
    return json.dumps(data)


def get_sn():
    '''获取SN'''
    cmd_res = exec_shell("dmidecode -t system|grep 'Serial Number'")
    cmd_res = cmd_res.strip()
    res_to_list = cmd_res.split(':')
    if len(res_to_list) > 1:  # the second one is wanted string
        return res_to_list[1].strip()
    else:
        return ''

# def get_cpu():
#     '''获取CPU信息'''
#     status, output = exec_shell()

def get_memory():
    '''获取内存信息'''
    distributor = exec_shell("free | grep Mem | grep -v total  | awk {'print $2'}")
    return (int(distributor) / 1024 / 1024)

def get_os_distributor():
    '''获取OS类型'''
    distributor = exec_shell("lsb_release -a|grep 'Distributor ID'").split(":")
    return distributor[1].strip() if len(distributor) > 1 else None


def get_os_version():
    '''获取系统版本'''
    version = exec_shell("lsb_release -a | grep 'Release'").split(":")
    return version[1].strip() if len(version) > 1 else None


if __name__ == "__main__":
    yum_check()
    print(collect())
