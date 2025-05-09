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
from importlib import import_module

from tornado.ioloop import IOLoop
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from apscheduler.schedulers.tornado import TornadoScheduler

from libs.base_handler import BaseHandler
from models.models_utils import get_all_cloud_interval
from services.cloud_service import opt_obj, get_cloud_settings, get_cloud_sync_log, update_cloud_settings
from libs.mycrypt import mc
from libs.thread_pool import global_executors



scheduler = TornadoScheduler(timezone="Asia/Shanghai")


# 云厂商模块懒加载器
class CloudModuleLoader:
    """云厂商模块懒加载器，仅在需要时才导入相应模块，减少内存占用"""

    def __init__(self):
        # 模块缓存
        self.modules_cache = {}
        # 云厂商对应模块路径
        self.provider_paths = {
            "aws": "libs.aws.synchronize",
            "aliyun": "libs.aliyun.synchronize",
            "qcloud": "libs.qcloud.synchronize",
            "cds": "libs.cds.synchronize",
            "vmware": "libs.vmware.synchronize",
            "volc": "libs.volc.synchronize",
            "gcp": "libs.gcp.synchronize",
            "pve": "libs.pve.synchronize",
        }

    def get_module(self, provider: str) -> Optional[Dict[str, Any]]:
        """获取指定云厂商的模块，如果还未加载则动态导入"""
        if provider not in self.provider_paths:
            return None

        if provider not in self.modules_cache:
            try:
                module_path = self.provider_paths[provider]
                module = import_module(module_path)
                self.modules_cache[provider] = {"mapping": getattr(module, "mapping"), "main": getattr(module, "main")}
            except (ImportError, AttributeError) as e:
                print(f"导入{provider}模块时出错: {e}")
                return None

        return self.modules_cache.get(provider)

    def get_sync_function(self, provider: str) -> Optional[Callable]:
        """获取指定云厂商的同步函数"""
        module = self.get_module(provider)
        return module["main"] if module else None

    def get_resource_mapping(self, provider: str) -> Dict:
        """获取指定云厂商的资源映射"""
        module = self.get_module(provider)
        return module["mapping"] if module else {}


cloud_loader = CloudModuleLoader()


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
    """云厂商服务类，用于同步云厂商资源"""

    def get_sync_function(self, cloud_name: str) -> Optional[Callable]:
        """获取同步函数"""
        return cloud_loader.get_sync_function(cloud_name)

    def get_resource_types(self, cloud_name: str) -> List[str]:
        """获取资源类型列表"""
        mapping = cloud_loader.get_resource_mapping(cloud_name)
        return list(mapping.keys())


def get_job_func(cloud_name, account_id, _executors):
    def job_func():
        sync_func = cloud_loader.get_sync_function(cloud_name)
        if sync_func:
            try:
                sync_func(account_id=account_id, executors=_executors)
            except Exception as e:
                print(f"执行{cloud_name}同步任务出错: {e}")

    return job_func


# 资产自动同步任务
# 2023年5月9日 必须添加到 mapping 才能提供同步功能
def add_cloud_jobs():
    resp: List[Dict[str, Union[str, int]]] = get_all_cloud_interval()
    for item in resp:
        cloud_name = item.get("cloud_name")
        account_id = item.get("account_id")
        job_func = get_job_func(cloud_name, account_id, global_executors.cloud_executor)
        if not job_func:
            continue
        scheduler.add_job(
            job_func,
            "interval",
            minutes=item.get("interval", 30),
            replace_existing=True,
            id=item.get("account_id"),
            name=str(item),
            # kwargs=dict(account_id=item['account_id'])
        )  # 默认 30m


class CloudSettingHandler(BaseHandler, ABC):
    def get(self):
        return self.write(get_cloud_settings())

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if data.get("cloud_name") == "gcp":
            account_file = data.get("account_file")
            if not account_file:
                return self.write(dict(code=-1, msg="谷歌云必须输入密钥文件"))
            data["account_file"] = mc.my_encrypt(account_file)
            data["access_id"] = "not_need"
            data["access_key"] = "not_need"
            data["region"] = "not_need"
        else:
            access_key = data.get("access_key").strip()
            data["access_key"] = mc.my_encrypt(access_key)
        data["account_id"] = uuid(name=data["name"])
        res = opt_obj.handle_add(data)
        add_cloud_jobs()

        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        access_key = data.get("access_key", None).strip()
        res = update_cloud_settings(data)

        add_cloud_jobs()
        if len(access_key) < 110:
            return self.write({"code": 0, "msg": "系统认为当前密钥为原始密钥，如果无法自动发现，则删除重建"})
        return self.write(res)

    def patch(self):
        """开关控制，开启/禁用"""
        data = json.loads(self.request.body.decode("utf-8"))
        cloud_id, is_enable = data.get("cloud_id", None), data.get("is_enable")
        new_data = dict(cloud_id=cloud_id)

        if not (cloud_id and is_enable):
            return self.write({"code": 1, "msg": "参数错误"})

        # bool值取反
        new_data["is_enable"] = not is_enable
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
        account_id = self.get_argument("account_id", default=None, strip=True)
        res = get_cloud_sync_log(account_id)

        return self.write(res)


class CloudSyncHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    def __init__(self, *args, **kwargs):
        super(CloudSyncHandler, self).__init__(*args, **kwargs)
        self.cloud_service = CloudService()

    # 前端手动触发
    @run_on_executor(executor="_thread_pool")
    def asset_sync_main(self, cloud_name: Optional[str], account_id: Optional[str], resources: List[str]):
        synchronize = cloud_loader.get_sync_function(cloud_name)
        synchronize(account_id=account_id, resources=resources)

    def get(self):
        """
        cloud_name: 'aliyun' / 'qcloud' / 'aws' / 'cds' / 'vmware' / 'volc'/ 'gcp'/ 'pve'
        """
        cloud_name: Optional[str] = self.get_argument("cloud_name", None)
        if not cloud_name:
            return self.write({"code": 1, "msg": "missing 1 required positional argument: cloud_name"})

        resources = self.cloud_service.get_resource_types(cloud_name)
        return self.write({"code": 0, "msg": "获取成功", "data": resources})

    async def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        cloud_name: Optional[str] = data.get("cloud_name", None)
        account_id: Optional[str] = data.get("account_id", None)
        resources: List[str] = data.get("resources", None)
        if not cloud_name or not resources:
            return self.write({"code": 1, "msg": "缺少账号/资源类型信息"})

        if not self.cloud_service.get_sync_function(cloud_name):
            return self.write({"code": 1, "msg": "不支持的云厂商"})

        IOLoop.current().add_callback(self.asset_sync_main, cloud_name, account_id, resources)

        # await self.asset_sync_main(cloud_name, account_id, resources)

        return self.write({"code": 0, "msg": "导入完成"})


cloud_urls = [
    (r"/api/v2/cmdb/cloud/conf/", CloudSettingHandler, {"handle_name": "配置平台-多云配置", "method": ["ALL"]}),
    (
        r"/api/v2/cmdb/cloud/sync/log/",
        SyncLogHandler,
        {"handle_name": "配置平台-多云配置-查看同步日志", "method": ["GET"]},
    ),
    (r"/api/v2/cmdb/cloud/sync/", CloudSyncHandler, {"handle_name": "配置平台-多云配置-资产同步", "method": ["ALL"]}),
]
