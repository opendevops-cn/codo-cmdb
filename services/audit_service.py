# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/30
# @Description: 审计日志

from shortuuid import uuid
import logging
from functools import wraps

from sqlalchemy import or_
from websdk2.model_utils import CommonOptView
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate

from models.autdit import AuditModels

opt_obj = CommonOptView(AuditModels)


def _get_value(value: str = None):
    """模糊查询"""
    if not value:
        return True

    return or_(
        AuditModels.business_name.like(f'%{value}%'),
        AuditModels.module_name.like(f'%{value}%'),
        AuditModels.message.like(f'%{value}%'),
        AuditModels.exec_uuid.like(f'%{value}%'),
    )


def get_audit_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AuditModels).filter(_get_value(value),
                                                          ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def add_audit_log(**data):
    """
    创建审计日志
    """
    business_name = data.get('business_name')
    if not business_name:
        return {"code": -1, "msg": "业务名称不能为空"}
    module_name = data.get('module_name')
    if not module_name:
        return {"code": -1, "msg": "模块名称不能为空"}
    message = data.get('message')
    if not message:
        return {"code": -1, "msg": "日志内容不能为空"}
    data.update(uuid=uuid())
    try:
        with DBContext('w', None, True) as session:
            session.add(AuditModels(**data))
        return True
    except Exception as error:
        logging.error(f"审计日志写入失败: {error}")
        return False


def audit_log(business_name: str = '服务树', module_name: str = '服务树', message: str = None, operator: str = None):
    """
    审计日志装饰器
    :param business_name: 业务名称，默认值为'服务树'。
    :param module_name: 模块名称，默认值为'服务树'。
    :param message: 日志信息，默认值为None。
    :param operator: 操作人，默认值为None。
    :return: 装饰器函数。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                # 一般用于service调用后，因此对result返回判断操作是否成功
                if result.get("code") == 0:
                    # 操作成功、记录日志
                    _audit_log_message = result.pop("audit_log_message", None)
                    _message = message or _audit_log_message
                    _create_user = args[0].get("create_user") if args else kwargs.get("create_user")
                    _modify_user = args[0].get("modify_user") if args else kwargs.get("modify_user")
                    _operator = operator or _create_user or _modify_user
                    if _message:
                        add_audit_log(business_name=business_name, module_name=module_name,
                                      message=_message, operator=_operator)
            except Exception as error:
                logging.error(error)
            finally:
                return result
        return wrapper
    return decorator


