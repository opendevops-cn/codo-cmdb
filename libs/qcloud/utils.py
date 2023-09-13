#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/7/25 10:09
# @Author  : harilou
# @Describe:

import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models

from typing import *
from models.models_utils import get_cloud_config
from libs.qcloud import  DEFAULT_CLOUD_NAME
from libs.mycrypt import mc
import logging
import traceback


class QCloudAPI(object):
    def __init__(self, region: str, access_id: str = None, access_key: str = None, account_id: str = None):
        self.region = region
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        if account_id:
            self._access_id, self._access_key = self._get_access(account_id)
        self.__cred = credential.Credential(self._access_id, self._access_key)
        self.cvm = cvm_client.CvmClient(self.__cred, self._region)
        self.vpc = vpc_client.VpcClient(self.__cred, self._region)

    def _get_access(self, account_id):
        cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
        if not cloud_configs: return
        return cloud_configs[0]['access_id'], mc.my_decrypt(cloud_configs[0]['access_key'])

    def get_price_ins(self, params):
        """获取cvm实例费用"""
        error, data = None, None
        try:
            req = cvm_models.InquiryPriceRunInstancesRequest()
            req.from_json_string(json.dumps(params))
            resp = self.cvm.InquiryPriceRunInstances(req)
            data = json.loads(resp.to_json_string())
        except TencentCloudSDKException as err:
            logging.error(traceback.format_exc())
            error = err
        return error, data

    def get_cvm_ins_type(self, zone, instance_type):
        """获取实例类型的配置"""
        error, data = None, None
        try:
            req = cvm_models.DescribeInstanceTypeConfigsRequest()
            params = {
                "Filters": [
                    {
                        "Name": "zone",
                        "Values": [zone]
                    },
                    {
                        "Name": "instance-type",
                        "Values": [instance_type]
                    }
                ]
            }
            req.from_json_string(json.dumps(params))
            resp = self.cvm.DescribeInstanceTypeConfigs(req)
            data = json.loads(resp.to_json_string())
        except TencentCloudSDKException as err:
            logging.error(traceback.format_exc())
            error = err
        return error, data

    def get_bandwidth_packages(self, **params):
        """获取实例类型的配置"""
        error, data = None, None
        try:
            req = vpc_models.DescribeBandwidthPackagesRequest()
            req.from_json_string(json.dumps(params))
            resp = self.vpc.DescribeBandwidthPackages(req)
            data = json.loads(resp.to_json_string())
        except TencentCloudSDKException as err:
            logging.error(traceback.format_exc())
            error = err
        return error, data