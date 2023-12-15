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
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
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
from models.models_utils import get_all_cloud_interval
from services.cloud_service import opt_obj, get_cloud_settings, get_cloud_sync_log
from apscheduler.schedulers.tornado import TornadoScheduler
from libs.mycrypt import mc

# 同步关系
mapping = {"aws": aws_synchronize, "aliyun": aliyun_synchronize, "qcloud": qcloud_synchronize,
           "cds": cbs_synchronize, "vmware": vm_synchronize, "volc": vol_synchronize, "gcp": gcp_synchronize}
# 定时器
scheduler = TornadoScheduler(timezone="Asia/Shanghai")


# 资产自动同步任务
# 2023年5月9日 必须添加到 mapping 才能提供同步功能
def add_cloud_jobs():
    resp: List[Dict[str, Union[str, int]]] = get_all_cloud_interval()
    for item in resp:
        func_name = mapping.get(item['cloud_name'])
        if not func_name: continue
        scheduler.add_job(
            func_name, 'interval', minutes=item.get('interval', 30),
            replace_existing=True, id=item.get('account_id'), name=str(item)
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
        if len(access_key) < 110:
            data['access_key'] = mc.my_encrypt(access_key)  # 密钥如果太短，则认为当前密钥为原始密钥

        res = opt_obj.handle_update(data)

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

    # 前端手动触发
    @run_on_executor(executor='_thread_pool')
    def asset_sync_main(self, cloud_name: Optional[str], account_id: Optional[str], resources: List[str]):
        synchronize = mapping.get(cloud_name)
        synchronize(account_id=account_id, resources=resources)

    def get(self):
        """
        cloud_name: 'aliyun' / 'qcloud' / 'aws' / 'cds' / 'vmware' / 'volc'
        """
        cloud_name: Optional[str] = self.get_argument('cloud_name', None)
        if not cloud_name:
            return self.write({'code': 1, 'msg': 'missing 1 required positional argument: cloud_name'})

        mappings = {
            "aws": aws_mapping,
            "qcloud": qcloud_mapping,
            "aliyun": aliyun_mapping,
            "cds": cbs_mapping,
            "vmware": vm_mapping,
            "volc": vol_mapping,
            "gcp": gcp_mapping
        }
        # 不同产品支持的类型
        resources = mappings.get(cloud_name).keys()  # type dict_keys
        resources = [i for i in resources]  # type list[str]
        return self.write({"code": 0, "msg": "获取成功", "data": resources})

    async def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        cloud_name: Optional[str] = data.get('cloud_name', None)
        account_id: Optional[str] = data.get('account_id', None)
        resources: List[str] = data.get('resources', None)
        if not cloud_name or not resources:
            return self.write({"code": 1, "msg": "缺少账号/资源类型信息"})

        if cloud_name not in ['aliyun', 'aws', 'qcloud', 'cds', 'vmware', 'volc', 'gcp']:
            return self.write({"code": 1, "msg": "不支持的云厂商"})

        await self.asset_sync_main(cloud_name, account_id, resources)

        return self.write({"code": 0, "msg": "导入完成"})


cloud_urls = [
    (r"/api/v2/cmdb/cloud/conf/", CloudSettingHandler, {"handle_name": "配置平台-多云配置", "method": ["ALL"]}),
    (r"/api/v2/cmdb/cloud/sync/log/", SyncLogHandler,
     {"handle_name": "配置平台-多云配置-查看同步日志", "method": ["GET"]}),
    (r"/api/v2/cmdb/cloud/sync/", CloudSyncHandler, {"handle_name": "配置平台-多云配置-资产同步", "method": ["ALL"]}),
]
