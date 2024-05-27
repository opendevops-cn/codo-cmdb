# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/22
# @Description: Description
import json
import os
from typing import io
import logging
import hcl
from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.order_model import TemplateModel, OrderInfoModel
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic
from websdk2.model_utils import CommonOptView
from datetime import datetime
from jinja2 import Template


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


def render_new_content(content, params):
    """渲染内容"""
    template = Template(content)
    return template.render(**params)


def add_order_template_for_api(params):
    content = params.get('content')
    if not content:
        return {"code": 1, "msg": "TF配置不能为空"}

    name = params.get('name')
    if not name:
        return {"code": 1, "msg": "名称不能为空"}

    if not params.get('res_type'):
        return {"code": 1, "msg": "模板类型不能为空"}
    if not params.get("subnet_id"):
        return {"code": 1, "msg": "私有子网不能为空"}
    if not params.get('vpc_id'):
        return {"code": 1, "msg": "私有网络不能为空"}
    if not params.get("vendor"):
        return {"code": 1, "msg": "云厂商不能为空"}
    if not params.get('region'):
        return {"code": 1, "msg": "地域不能为空"}
    if not params.get('zone'):
        return {"code": 1, "msg": "可用区不能为空"}
    try:
        # 检查文件格式
        hcl.loads(content)
    except Exception as e:
        return {"code": 1, "msg": "TF格式不正确"}
    new_content = render_new_content(content, params)
    params['content'] = new_content
    try:
        with DBContext('w', None, True) as session:
            exist_obj = session.query(TemplateModel).filter(
                TemplateModel.name == name).first()
            if exist_obj:
                return {"code": 1,
                        "msg": f"{name} already exists."}

            session.add(TemplateModel(**params))
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}

    return {"code": 0, "msg": "添加成功"}


def update_order_template_for_api(data: dict) -> dict:
    if not data.get("id"):
        return {"code": 1, "msg": "模板ID不能为空"}
    if not data.get("name"):
        return {"code": 1, "msg": "模板名称不能为空"}
    if not data.get('res_type'):
        return {"code": 1, "msg": "模板类型不能为空"}
    if not data.get("subnet_id"):
        return {"code": 1, "msg": "私有子网不能为空"}
    if not data.get('vpc_id'):
        return {"code": 1, "msg": "私有网络不能为空"}
    if not data.get("vendor"):
        return {"code": 1, "msg": "云厂商不能为空"}
    if not data.get('region'):
        return {"code": 1, "msg": "地域不能为空"}
    if not data.get('zone'):
        return {"code": 1, "msg": "可用区不能为空"}
    if not data.get('content'):
        return {"code": 1, "msg": "TF不能为空"}
    if not data.get('tags'):
        return {"code": 1, "msg": "标签不能为空"}

    content = data.get('content')
    try:
        hcl.loads(content)
    except Exception as e:
        return {"code": 1, "msg": "TF格式不正确"}

    new_content = render_new_content(content, data)
    data['content'] = new_content

    try:
        with DBContext('w', None, True) as session:
            session.query(TemplateModel).filter(TemplateModel.id == data.get('id')).update(data)
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}
    return {"code": 0, "msg": "更新成功"}


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