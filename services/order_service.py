#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/7/20 15:08
# @Author  : harilou
# @Describe:

from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.order_model import TemplateModel, OrderInfoModel
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic
from websdk2.model_utils import CommonOptView
from datetime import datetime


PydanticDomainNameBase = sqlalchemy_to_pydantic(TemplateModel, exclude=['id'])
tmp_obj = CommonOptView(TemplateModel)
info_obj = CommonOptView(OrderInfoModel)


def _get_template_value(value: str = None):
    if not value:
        return True
    return or_(
        TemplateModel.name.like(f'%{value}%'),
        TemplateModel.res_type.like(f'%{value}%'),
        TemplateModel.vendor.like(f'%{value}%'),
        TemplateModel.region.like(f'%{value}%'),
        TemplateModel.description.like(f'%{value}%'),
    )


def _get_info_value(value: str = None):
    if not value:
        return True
    return or_(
        OrderInfoModel.name.like(f'%{value}%'),
        OrderInfoModel.res_type.like(f'%{value}%'),
        OrderInfoModel.vendor.like(f'%{value}%'),
        OrderInfoModel.instance_name.like(f'%{value}%'),
        OrderInfoModel.flow_id.like(f'%{value}%'),
        OrderInfoModel.status.like(f'%{value}%'),
    )


def get_order_template(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据

    res_type_choice_list = ["res_type", "vendor"]
    with DBContext('r') as session:
        page = paginate(session.query(TemplateModel).filter(_get_template_value(value)).filter_by(**filter_map), **params)
        for item in page.items:
            for _filed in res_type_choice_list:
                item[f"{_filed}_alias"] = item[_filed].value
                item[_filed] = item[_filed].code
    return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def get_order_info(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据

    res_type_choice_list = ["status", "res_type", "vendor"]
    with DBContext('r') as session:
        page = paginate(session.query(OrderInfoModel).filter(_get_info_value(value)).filter_by(**filter_map), **params)
        for item in page.items:
            for _filed in res_type_choice_list:
                item[f"{_filed}_alias"] = item[_filed].value
                item[_filed] = item[_filed].code
    return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def update_tmp_last_time(data):
    """更新模板最后使用时间"""
    if "id" in data:
        tmp_id = data.get("id")
        with DBContext('r') as session:
            _tmp_obj = session.query(TemplateModel).filter(TemplateModel.id == tmp_id)
            if _tmp_obj:
                for item in _tmp_obj:
                    item.last_time = datetime.now()
                    session.add(item)
            else:
                return dict(msg=f'ID:{tmp_id}不存在', code=-1)
            session.commit()
    else:
        return dict(msg='ID字段必填', code=-1)
    return dict(msg='修改成功', code=0)