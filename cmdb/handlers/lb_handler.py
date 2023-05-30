#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : this module is used for lb handler.
"""

import json
from abc import ABC
from typing import *
from sqlalchemy import or_
from websdk2.db_context import DBContext
from websdk2.model_utils import queryset_to_list
from libs.base_handler import BaseHandler
from models.asset import AssetLBModels


def _get_lb_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]
    query_filter_map = {
        "is_normal": [AssetLBModels.is_expired == False],
        "is_expired": [AssetLBModels.is_expired == True],
        "is_alb": [AssetLBModels.type == "alb"],
        "is_slb": [AssetLBModels.type == "slb"],
        "is_nlb": [AssetLBModels.type == "nlb"],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_lb_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetLBModels.cloud_name.like(f'%{search_val}%'),
        AssetLBModels.name.like(f'%{search_val}%'),
        AssetLBModels.dns_name.like(f'%{search_val}%'),
        AssetLBModels.endpoint_type.like(f'%{search_val}%'),
        AssetLBModels.instance_id.like(f'%{search_val}%'),
        AssetLBModels.type.like(f'%{search_val}%'),
        AssetLBModels.state.like(f'%{search_val}%'),
    )


class AssetLBHandler(BaseHandler, ABC):
    def get(self):
        search_val = self.get_argument('search_val', '')
        search_filter = self.get_argument('search_filter', None)
        page_size = self.get_argument('page_size', default='10', strip=True)
        page_number = self.get_argument('page_number', default='1', strip=True)
        page_number = (int(page_number) - 1) * int(page_size)
        with DBContext('r') as session:
            query = session.query(AssetLBModels).filter(
                *_get_lb_by_filter(search_filter), _get_lb_by_val(search_val)
            )
            count: Optional[int] = query.count()
            models: List[AssetLBModels] = query.order_by(AssetLBModels.id.desc()).offset(
                int(page_number)).limit(int(page_size)).all()
            # models to list[dict]
            data: List[dict] = queryset_to_list(models)
        return self.write(dict(code=0, msg='获取成功', count=count, data=data))

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        items = data.get('items', [])
        if not items:
            return self.write({"code": 0, "msg": "未发现数据"})
        _ids = [i.get('id') for i in items]
        with DBContext('w', None, True) as session:
            for _id in _ids:
                session.query(AssetLBModels).filter(
                    AssetLBModels.id == _id
                ).delete(synchronize_session=False)
        return self.write({"code": 0, "msg": "success"})


lb_urls = [
    (r"/api/v2/cmdb/lb/", AssetLBHandler, {"handle_name": "CMDB-LB管理", "handle_status": "y"}),
]
