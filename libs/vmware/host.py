#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Author: shenshuo
Date  : 2023/2/25
Desc  : VMware
"""

import logging
from models.models_utils import server_task, mark_expired
from typing import *
from pyVmomi import vim
from pyVim import connect


def check_os_type(os_name):
    os_name = os_name.lower()
    types = ('centos', 'coreos', 'debian', 'suse', 'ubuntu', 'windows', 'freebsd', 'tencent', 'alibaba', 'rockylinux')
    for t in types:
        if t in os_name:
            return t
    return 'unknown'


def check_instance_status(value):
    running_list = ["POWEREDON", "RUNNING"]
    stop_list = ["POWEREDOFF", "STOPPED", "STOP"]
    if value.upper() in running_list:
        return "运行中"
    if value.upper() in stop_list:
        return "关机"
    else:
        return value


class VMWareHostAPI(object):
    def __init__(self, access_id: str, access_key: str, account_id: str, server_addr: str):
        self.__user = access_id
        self.__password = access_key
        self._account_id = account_id
        self.__scheme = None
        self.__server = server_addr.split(':')[0]
        self.__port = server_addr.split(':')[1]

        if len(server_addr.split(':')) == 3:
            self.__scheme = server_addr.split(':')[2]

        try:
            self.client = self._init_conn_client()
        except Exception as err:
            logging.error(err)

    def _init_conn_client(self):
        if self.__scheme and self.__scheme == 'ssl':
            vc_ins = connect.SmartConnect(host=self.__server, user=self.__user, pwd=self.__password, port=self.__port)
        else:
            vc_ins = connect.SmartConnectNoSSL(host=self.__server, user=self.__user, pwd=self.__password,
                                               port=self.__port)
        content = vc_ins.RetrieveContent()
        container = content.rootFolder
        viewType = [vim.VirtualMachine]
        recursive = True
        return content.viewManager.CreateContainerView(container, viewType, recursive)

    def get_all_vm(self):
        """
        https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/getallvms.py
        Print information for a particular virtual machine or recurse into a
        folder with depth protection
        """

        return [self.format_data(info) for info in self.client.view]

    def format_data(self, data) -> Dict[str, Any]:
        summary = data.summary

        # # 定义返回
        res: Dict[str, Any] = dict()
        res['instance_id'] = summary.config.instanceUuid
        try:
            res['name'] = summary.config.name
            res['account_id'] = self._account_id
            res['state'] = check_instance_status(summary.runtime.powerState)
            # res['instance_type'] = data.get('InstanceType')
            res['inner_ip'] = summary.guest.ipAddress
            res['cpu'] = summary.config.numCpu
            res['memory'] = round(summary.config.memorySizeMB / 1024, 0)
            res['region'] = self.__server
            res['zone'] = ''
            res['os_type'] = check_os_type(summary.config.guestFullName)
            res['os_name'] = summary.config.guestFullName
        except Exception as e:
            logging.error(f'同步开始, 信息：「format_data」-「{e}」.')
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'vmware', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 机器比较少 根本用不上迭代器
        logging.info(f'同步开始, 信息：「{cloud_name}」-「{resource_type}」.')
        all_server_list: List[dict] = self.get_all_vm()
        if not all_server_list: return False, "主机列表为空"
        # # 更新资源
        ret_state, ret_msg = server_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_server_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)
        #
        return ret_state, ret_msg
