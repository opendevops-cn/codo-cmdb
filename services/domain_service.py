#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018年5月7日
"""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, BaseModel
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.domain import DomainOptLog, DomainName, DomainRecords

PydanticDomainNameBase = sqlalchemy_to_pydantic(DomainName, exclude=['id'])

PydanticDomainNameUP = sqlalchemy_to_pydantic(DomainName)


class PydanticDomainNameUP2(BaseModel):
    id: int
    star_mark: bool


class PydanticDomainNameDel(BaseModel):
    id_list: list[int]


def add_domain_name(data: dict) -> dict:
    if '_index' in data:
        del data['_index']
    if '_rowKey' in data:
        del data['_rowKey']
    try:
        PydanticDomainNameBase(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.add(DomainName(**data))
    except IntegrityError as e:
        return dict(code=-2, msg='不要重复添加相同的配置')

    except Exception as e:
        return dict(code=-3, msg=f'{e}')

    return dict(code=0, msg="创建成功")


def up_domain_name(data: dict) -> dict:
    if '_index' in data:
        del data['_index']
    if '_rowKey' in data:
        del data['_rowKey']

    try:
        if len(data) == 2:
            valid_data = PydanticDomainNameUP2(**data)
        else:
            valid_data = PydanticDomainNameUP(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(DomainName).filter(DomainName.id == valid_data.id).update(data)

    except IntegrityError as e:
        return dict(code=-2, msg=f'修改失败，已存在')

    except Exception as err:
        return dict(code=-3, msg=f'修改失败, {err}')
    if len(data) == 2:
        return dict(code=0, msg="星标成功")
    return dict(code=0, msg="修改成功")


def del_domain_name(data: dict):
    user = data.pop('user')
    try:
        valid_data = PydanticDomainNameDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext('w', None, True) as db:
            db.query(DomainName).filter(DomainName.id.in_(valid_data.id_list)).delete(synchronize_session=False)
            for i in valid_data.id_list:
                domain_info = db.query(DomainName).filter(DomainName.id == i).first()
                db.add(DomainOptLog(domain_name=domain_info.domain_name, username=user, action='删除',
                                    record='删除根域名'))
    except Exception as err:
        return dict(code=-3, msg=f'删除失败, {str(err)}')

    return dict(code=0, msg="删除成功")


def _get_domain_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainName.domain_name.like(f'%{value}%'),
        DomainName.cloud_name.like(f'%{value}%'),
        DomainName.version.like(f'%{value}%'),
        DomainName.account.like(f'%{value}%'),
        DomainName.id.like(f'%{value}%')
    )


def get_cloud_domain(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据

    with DBContext('r') as session:
        page = paginate(session.query(DomainName).filter(_get_domain_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def _get_record_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainRecords.domain_rr.like(f'%{value}%'),
        DomainRecords.domain_value.like(f'%{value}%'),
        DomainRecords.domain_type.like(f'%{value}%'),
        DomainRecords.line.like(f'{value}%'),
        DomainRecords.state.like(f'%{value}%'),
        DomainRecords.account.like(f'%{value}%'),
        DomainRecords.record_id.like(f'%{value}%'),
        DomainRecords.remark.like(f'%{value}%')
    )


def get_cloud_record(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    domain_name = params.pop('domain_name')
    filter_map['domain_name'] = domain_name
    with DBContext('r') as session:
        page = paginate(session.query(DomainRecords).filter(_get_record_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, count=page.total, data=page.items)


def _get_log_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainOptLog.username.like(f'%{value}%'),
        DomainOptLog.action.like(f'%{value}%'),
        DomainOptLog.state.like(f'%{value}%'),
        DomainOptLog.id.like(f'%{value}%'),
        DomainOptLog.update_time.like(f'%{value}%'),
        DomainOptLog.record.like(f'%{value}%')
    )


def get_domain_opt_log(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    if 'domain_name' not in params:
        return dict(code=-1, msg='关键参数域名不能为空')

    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if "order_by" not in params:
        params['order_by'] = 'update_time'
    if 'biz_id' in filter_map:
        filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    filter_map['domain_name'] = params.pop('domain_name')
    with DBContext('r') as session:
        page = paginate(session.query(DomainOptLog).filter(_get_log_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, count=page.total, data=page.items)
