#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : this module is used for cloud handler use sync task.
"""

import json
from abc import ABC
from typing import *
from shortuuid import uuid
from enum import Enum

from tornado.ioloop import IOLoop
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from apscheduler.schedulers.tornado import TornadoScheduler

from libs.base_handler import BaseHandler
from libs.aliyun.synchronize import mapping as aliyun_mapping
from libs.aliyun.synchronize import main as aliyun_synchronize
from libs.aws.synchronize import mapping as aws_mapping
from libs.aws.synchronize import main as aws_synchronize
from libs.qcloud.synchronize import mapping as qcloud_mapping
from libs.qcloud.synchronize import main as qcloud_synchronize
from libs.cds.synchronize import mapping as cbs_mapping
from libs.cds.synchronize import main as cbs_synchronize
from libs.vmware.synchronize import mapping as vm_mapping
from libs.vmware.synchronize import main as vm_synchronize
from libs.volc.synchronize import mapping as vol_mapping
from libs.volc.synchronize import main as vol_synchronize
from libs.gcp.synchronize import mapping as gcp_mapping
from libs.gcp.synchronize import main as gcp_synchronize
from libs.pve.synchronize import mapping as pve_mapping
from libs.pve.synchronize import main as pve_synchronize
from models.models_utils import get_all_cloud_interval
from services.cloud_service import opt_obj, get_cloud_settings, get_cloud_sync_log, update_cloud_settings
from libs.mycrypt import mc

# 同步关系
mapping = {"aws": aws_synchronize, "aliyun": aliyun_synchronize, "qcloud": qcloud_synchronize,
           "cds": cbs_synchronize, "vmware": vm_synchronize, "volc": vol_synchronize, "gcp": gcp_synchronize,
           "pve": pve_synchronize}
# 定时器
scheduler = TornadoScheduler(timezone="Asia/Shanghai")


# 云厂商枚举
class CloudProvider(Enum):
    AWS = "aws"
    ALIYUN = "aliyun" 
    QCLOUD = "qcloud"
    CDS = "cds"
    VMWARE = "vmware"
    VOLC = "volc"
    GCP = "gcp"
    PVE = "pve"
    
    
class CloudService:
    """云厂商服务类，用于同步云厂商资源
    """
    def __init__(self):
        # 同步关系
        self.sync_mappings = {
            CloudProvider.AWS.value: aws_synchronize,
            CloudProvider.ALIYUN.value: aliyun_synchronize,
            CloudProvider.QCLOUD.value: qcloud_synchronize,
            CloudProvider.CDS.value: cbs_synchronize,
            CloudProvider.VMWARE.value: vm_synchronize,
            CloudProvider.VOLC.value: vol_synchronize,
            CloudProvider.GCP.value: gcp_synchronize,
            CloudProvider.PVE.value: pve_synchronize
        }
        # 资源类型映射
        self.resource_mappings = {
            CloudProvider.AWS.value: aws_mapping,
            CloudProvider.ALIYUN.value: aliyun_mapping,
            CloudProvider.QCLOUD.value: qcloud_mapping,
            CloudProvider.CDS.value: cbs_mapping,
            CloudProvider.VMWARE.value: vm_mapping,
            CloudProvider.VOLC.value: vol_mapping,
            CloudProvider.GCP.value: gcp_mapping,
            CloudProvider.PVE.value: pve_mapping
        }
    
    
    def get_sync_function(self, cloud_name: str) -> Optional[Callable]:
        """获取同步函数"""
        return self.sync_mappings.get(cloud_name)
        
    def get_resource_types(self, cloud_name: str) -> List[str]:
        """获取资源类型列表"""
        mapping = self.resource_mappings.get(cloud_name, {})
        return list(mapping.keys())
    

# 资产自动同步任务
# 2023年5月9日 必须添加到 mapping 才能提供同步功能
def add_cloud_jobs():
    resp: List[Dict[str, Union[str, int]]] = get_all_cloud_interval()
    for item in resp:
        func_name = mapping.get(item['cloud_name'])
        if not func_name: continue
        scheduler.add_job(
            func_name, 'interval', minutes=item.get('interval', 30),
            replace_existing=True, id=item.get('account_id'), name=str(item),
            kwargs=dict(account_id=item['account_id'])
        )  # 默认 30m


class CloudSettingHandler(BaseHandler, ABC):
    def get(self):
        return self.write(get_cloud_settings())

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if data.get('cloud_name') == 'gcp':
            account_file = data.get('account_file')
            if not account_file:
                return self.write(dict(code=-1, msg='谷歌云必须输入密钥文件'))
            data['account_file'] = mc.my_encrypt(account_file)
            data['access_id'] = 'not_need'
            data['access_key'] = 'not_need'
            data['region'] = 'not_need'
        else:
            access_key = data.get('access_key').strip()
            data['access_key'] = mc.my_encrypt(access_key)
        data['account_id'] = uuid(name=data['name'])
        res = opt_obj.handle_add(data)
        add_cloud_jobs()

        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        access_key = data.get('access_key', None).strip()
        res = update_cloud_settings(data)

        add_cloud_jobs()
        if len(access_key) < 110:
            return self.write({"code": 0, "msg": "系统认为当前密钥为原始密钥，如果无法自动发现，则删除重建"})
        return self.write(res)

    def patch(self):
        """开关控制，开启/禁用"""
        data = json.loads(self.request.body.decode("utf-8"))
        cloud_id, is_enable = data.get('cloud_id', None), data.get('is_enable')
        new_data = dict(cloud_id=cloud_id)

        if not (cloud_id and is_enable):
            return self.write({"code": 1, "msg": "参数错误"})

        # bool值取反
        new_data['is_enable'] = not is_enable
        res = opt_obj.handle_update(new_data)

        add_cloud_jobs()
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        add_cloud_jobs()
        return self.write(res)


class SyncLogHandler(BaseHandler, ABC):
    def get(self):
        account_id = self.get_argument('account_id', default=None, strip=True)
        res = get_cloud_sync_log(account_id)

        return self.write(res)


class CloudSyncHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    def __init__(self, *args, **kwargs):
        super(CloudSyncHandler, self).__init__(*args, **kwargs)
        self.cloud_service = CloudService()

    # 前端手动触发
    @run_on_executor(executor='_thread_pool')
    def asset_sync_main(self, cloud_name: Optional[str], account_id: Optional[str], resources: List[str]):
        synchronize = mapping.get(cloud_name)
        synchronize(account_id=account_id, resources=resources)

    def get(self):
        """
        cloud_name: 'aliyun' / 'qcloud' / 'aws' / 'cds' / 'vmware' / 'volc'/ 'gcp'/ 'pve'
        """
        cloud_name: Optional[str] = self.get_argument('cloud_name', None)
        if not cloud_name:
            return self.write({'code': 1, 'msg': 'missing 1 required positional argument: cloud_name'})

        resources = self.cloud_service.get_resource_types(cloud_name)
        return self.write({"code": 0, "msg": "获取成功", "data": resources})

    async def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        cloud_name: Optional[str] = data.get('cloud_name', None)
        account_id: Optional[str] = data.get('account_id', None)
        resources: List[str] = data.get('resources', None)
        if not cloud_name or not resources:
            return self.write({"code": 1, "msg": "缺少账号/资源类型信息"})

        if not self.cloud_service.get_sync_function(cloud_name):
            return self.write({"code": 1, "msg": "不支持的云厂商"})

        IOLoop.current().add_callback(self.asset_sync_main, cloud_name, account_id, resources)

        # await self.asset_sync_main(cloud_name, account_id, resources)

        return self.write({"code": 0, "msg": "导入完成"})


cloud_urls = [
    (r"/api/v2/cmdb/cloud/conf/", CloudSettingHandler, {"handle_name": "配置平台-多云配置", "method": ["ALL"]}),
    (r"/api/v2/cmdb/cloud/sync/log/", SyncLogHandler,
     {"handle_name": "配置平台-多云配置-查看同步日志", "method": ["GET"]}),
    (r"/api/v2/cmdb/cloud/sync/", CloudSyncHandler, {"handle_name": "配置平台-多云配置-资产同步", "method": ["ALL"]}),
]
