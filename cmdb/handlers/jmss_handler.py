# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/16
# @Description: jmss

from abc import ABC
from libs.base_handler import BaseHandler
from libs.api_gateway.jumpserver.asset_accounts import AssetAccountPushAutomationsAPI


class JmssHandler(BaseHandler, ABC):

    def get(self):
        result = AssetAccountPushAutomationsAPI().get(**self.params)
        return self.write(dict(msg='获取成功', code=0, data=result, count=len(result)))


jmss_urls = [
    (r"/api/v2/cmdb/jmss/accounts/", JmssHandler, {"handle_name": "配置平台-堡垒机资产账户列表", "method": ["GET"]}),
]
