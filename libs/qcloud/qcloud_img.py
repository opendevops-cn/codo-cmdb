#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/6 17:51
Desc    : 腾讯云 虚拟局域网
"""

import logging
from typing import *
import json
from tencentcloud.common import credential
from tencentcloud.cvm.v20170312 import cvm_client, models
from models.models_utils import image_task, mark_expired, mark_expired_by_sync


def get_img_type(val):
    __map = {
        "PRIVATE_IMAGE": "私有镜像",
        "PUBLIC_IMAGE": "公共镜像",
        "SHARED_IMAGE": "共享镜像"
    }
    return __map.get(val, '未知')


def get_img_state(val):
    __map = {
        "NORMAL": "正常",
        "CREATING": "创建中",
        "CREATEFAILED": "创建失败",
        "USING": "使用中",
        "SYNCING": "同步中",
        "IMPORTING": "导入中",
        "IMPORTFAILED": "导入失败"
    }
    return __map.get(val, '未知')


class QCloudCImg:
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = cvm_client.CvmClient(self.__cred, self._region)
        self.req = models.DescribeImagesRequest()

    def get_all_img(self):
        __list = []
        limit = self._limit
        offset = self._offset
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                self.req.from_json_string(json.dumps(params))
                resp = self.client.DescribeImages(self.req)

                if not resp.ImageSet:
                    break
                __list.extend(map(self.format_data, resp.ImageSet))
                offset += limit
            return __list
        except Exception as err:
            logging.error(err)
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.ImageId
        res['name'] = data.ImageName
        res['description'] = data.ImageDescription
        res['region'] = self._region
        res['create_time'] = data.CreatedTime
        res['image_type'] = get_img_type(data.ImageType)
        res['image_size'] = data.ImageSize  # 镜像硬盘
        res['os_platform'] = data.Platform  # 平台
        res['os_name'] = data.OsName  # 系统名称
        res['state'] = get_img_state(data.ImageState)  # 镜像状态
        res['arch'] = data.Architecture  # 架构

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'image') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        all_img_list: List[list, Any, None] = self.get_all_img()

        if not all_img_list:
            return False, "镜像列表为空"
        # 同步资源
        ret_state, ret_msg = image_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_img_list)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [img['instance_id'] for img in all_img_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)
        return ret_state, ret_msg
