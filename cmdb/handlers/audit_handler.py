# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/31
# @Description: Description
import json
from abc import ABC
from libs.base_handler import BaseHandler

from services.audit_service import get_audit_list_for_api


class AuditHandler(BaseHandler, ABC):

    def get(self):
        res = get_audit_list_for_api(**self.params)
        self.write(res)


audit_urls = [
    (r"/api/v2/cmdb/audit/list/", AuditHandler,
     {"handle_name": "配置平台-审计日志", "method": ["GET"]}),
]
