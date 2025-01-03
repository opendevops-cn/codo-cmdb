#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
"""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError
from models.business import BizModels
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(BizModels)

PydanticBiz = sqlalchemy_to_pydantic(BizModels, exclude=['id'])

# PydanticBizUP = sqlalchemy_to_pydantic(BizModels)


def add_default_business():
    """添加默认项目"""
    with DBContext('w', None, True) as session:
        has_biz_count = session.query(BizModels).count()
        if has_biz_count > 0:
            return
        is_exist = session.query(BizModels).filter(BizModels.biz_cn_name == '默认项目').first()
        if not is_exist:
            session.add(
                BizModels(**dict(biz_cn_name='默认项目', biz_en_name='default', life_cycle='开发中', biz_opser='Ops')))
        return


def add_biz(data: dict) -> dict:
    if '_index' in data:
        del data['_index']
    if '_rowKey' in data:
        del data['_rowKey']
    try:
        PydanticBiz(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            biz_info = db.query(BizModels).order_by(-BizModels.id).first()
            data['biz_id'] = biz_info.id + 500
            db.add(BizModels(**data))
    except IntegrityError as e:
        return dict(code=-2, msg='不要重复添加相同的配置')

    except Exception as e:
        return dict(code=-3, msg=f'{e}')

    return dict(code=0, msg="创建成功")


def _get_biz_value(value: str = None):
    if not value:
        return True
    return or_(
        BizModels.biz_cn_name.like(f'%{value}%'), BizModels.biz_en_name.like(f'%{value}%'),
        BizModels.biz_opser.like(f'%{value}%'), BizModels.biz_developer.like(f'%{value}%'),
        BizModels.biz_tester.like(f'%{value}%'), BizModels.life_cycle.like(f'%{value}%'),
    )


def get_business_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    if "order_by" not in params:
        params["order_by"] = "biz_en_name"
    # add_default_business()
    with DBContext('r') as session:
        page = paginate(session.query(BizModels).filter(_get_biz_value(value)).filter_by(**filter_map), **params)
    return dict(msg='获取成功', code=0, count=page.total, data=page.items)
