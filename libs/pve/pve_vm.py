#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   pve_vm.py
# @Time    :   2024/11/11 10:34:24
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   Proxmox VE 虚拟机实例
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import logging
from functools import wraps
import urllib3

import requests

from models.models_utils import server_task, mark_expired


# 解决自签名 CA 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PVERequestError(Exception):
    """PVE请求异常"""
    pass


def handle_pve_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logging.error(f"PVE API 请求错误: {str}")
            raise PVERequestError(f"PVE API请求错误: {str(e)}")
        except Exception as e:
            logging.error(f"PVE API调用异常: {str(e)}")
            raise PVERequestError(f"PVE API调用失败: {str(e)}")

    return wrapper


def convert_bytes_to_gb(bytes_value: Optional[int]) -> float:
    """将字节转换为GB

    Args:
        bytes_value: 字节大小

    Returns:
        float: GB大小,保留2位小数
    """
    if not bytes_value:
        return 0.0

    BYTES_IN_GB = 1024 * 1024 * 1024  # 1GB = 1024^3 bytes
    return round(bytes_value / BYTES_IN_GB, 2)


class PveVM(object):
    DEFAULT_TIMEOUT = 10
    VERIFY_SSL = False
    API_PATH = "api2/json"

    def __init__(self, access_id: str, access_key: str, account_id: str, server_addr: str) -> None:
        """初始化参数

        Args:
            access_id (str): pve用户名
            access_key (str): pve密码
            account_id (str): pve账户ID
            server_addr (str): pve server地址
        Returns:
            None
        """
        self.username = access_id
        self.password = access_key
        self.account_id = account_id
        self.server_addr = server_addr
        self.base_url = f"https://{self.server_addr}/{self.API_PATH}"
        self.__ticket: Optional[Dict[str, str]] = None

    def _make_request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None,  **kwargs) -> requests.Response:
        """构建请求

        Args:
            method (str): 请求方法
            url (str): 请求路径
            data (dict): 请求数据
            kwargs (dict): 其他请求参数
        Returns:
            requests.Response: 请求响应
        """
        url = f"{self.base_url}{path}"
        headers = kwargs.pop('headers', {})
        if self.__ticket:
            headers.update({
                'CSRFPreventionToken': self.__ticket['CSRFPreventionToken'],
                'Cookie': f"PVEAuthCookie={self.__ticket['ticket']}"
            })
        kwargs.update({
            'headers': headers,
            'verify': self.VERIFY_SSL,
            'timeout': self.DEFAULT_TIMEOUT
        })
        response = requests.request(method, url, data=data, **kwargs)
        return response

    @handle_pve_exceptions
    def get_ticket(self) -> bool:
        """认证获取PVE API票据

        Returns:
            bool: 认证是否成功
        """
        response = self._make_request(
            'POST', '/access/ticket', data={'username': self.username, 'password': self.password})
        data = response.json()
        if 'data' not in data:
            logging.error("获取票据响应格式错误")
            return False
        self.__ticket = data['data']
        return True

    @handle_pve_exceptions
    def get_node_list(self) -> Dict[str, Any]:
        """获取节点列表

        Returns:
            dict: 节点列表
        """
        if not self.__ticket:
            raise PVERequestError("未获取认证票据")

        response = self._make_request('GET', '/nodes')
        return response.json()

    @handle_pve_exceptions
    def get_vm_list(self, node: str) -> Dict[str, Any]:
        """获取虚拟机实例列表

        Args:
            node (str): 节点名称

        Returns:
            dict: 虚拟机实例列表
        """
        if not self.__ticket:
            raise PVERequestError("未获取认证票据")
        response = self._make_request('GET', f'/nodes/{node}/qemu')
        return response.json()

    @handle_pve_exceptions
    def get_vm_interfaces(self, node: str, vmid: str) -> Dict[str, Any]:
        """获取虚拟机网络接口信息

        Args:
            node (str): 节点名称
            vmid (str): 虚拟机ID

        Returns:
            str: 网络接口信息
        """
        if not self.__ticket:
            raise PVERequestError("未获取认证票据")
        response = self._make_request(
            'GET', f'/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces')
        return response.json()

    @handle_pve_exceptions
    def get_ipv4_from_interfaces(self, interfaces_data: Dict[str, Any]) -> str:
        """获取IPV4地址

        Args:
            interfaces_data (dict): 网络接口信息

        Returns:
            str: IPV4地址
        """
        if not interfaces_data:
            return ""

        data = interfaces_data.get('data', {})
        if not data:
            return ""

        interfaces = data.get('result', [])
        if not interfaces:
            return ""

        for interface in interfaces:
            if interface.get("name").lower() == "lo":
                continue
            ip_addresses = interface.get('ip-addresses', [])
            for ip_address in ip_addresses:
                if ip_address.get('ip-address-type').lower() == 'ipv4':
                    return ip_address.get('ip-address')
        else:
            return ""

    def get_all_vm_list(self) -> List[Dict]:
        """获取所有虚拟机实例

        Returns:
            dict: 虚拟机实例列表
        """
        all_vms = []
        if not self.get_ticket():
            return []
        nodes = self.get_node_list()

        for node in nodes['data']:
            vms = self.get_vm_list(node['node'])
            if not vms:
                continue

            # 处理节点下的所有虚拟机
            all_vms.extend([
                self.process_data({
                    **vm,
                    'ipv4': self.get_ipv4_from_interfaces(
                        self.get_vm_interfaces(node['node'], vm['vmid'])
                    )
                })
                for vm in vms['data']
            ])
        return all_vms

    def process_data(self, data: Dict[str, Any]) -> Dict:
        """处理数据

        Args:
            data (Dict[str, Any]): 原始虚拟机数据

        Returns:
            Dict: 处理后的虚拟机数据
        """
        item = {}
        item['account_id'] = self.account_id
        item['state'] = "运行中" if data.get('status') == 'running' else "关机"
        item['inner_ip'] = data.get('ipv4')
        item['name'] = data.get('name')
        item['instance_id'] = str(data.get('vmid', 0))
        item['region'] = self.server_addr
        item['cpu'] = data.get('cpus')
        item['memory'] = convert_bytes_to_gb(data.get('maxmem', 0))
        item['disk'] = convert_bytes_to_gb(data.get('maxdisk', 0))
        item['zone'] = ""
        return item

    def sync_cmdb(self, cloud_name: Optional[str] = 'pve', resource_type: Optional[str] = 'server') -> Tuple[bool, str]:
        """同步CMDB

        Args:
            cloud_name (str): 云平台名称
            resource_type (str): 资源类型

        Returns:
            tuple: 同步结果
        """
        all_vm_list = self.get_all_vm_list()
        if not all_vm_list:
            return False, "主机列表为空"
        # 更新资源
        ret_state, ret_msg = server_task(
            account_id=self.account_id, cloud_name=cloud_name, rows=all_vm_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self.account_id)
        return ret_state, ret_msg


if __name__ == '__main__':
    pass
