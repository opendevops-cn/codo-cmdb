#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
"""

from abc import ABC
from libs.base_handler import BaseHandler
from services.search_service import get_asset_list


class SearchHandler(BaseHandler, ABC):
    def get(self):
        res = get_asset_list(**self.params)
        return self.write(res)


search_urls = [
    (r"/api/v2/cmdb/search/", SearchHandler, {"handle_name": "配置平台-基础功能-统一查询", "method": ["GET"]}),
]
