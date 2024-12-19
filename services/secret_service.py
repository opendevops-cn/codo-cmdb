#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   secret.py
# @Time    :   2024/12/19 15:00:21
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   欢乐剑密钥逻辑入口

from typing import List, Any, TypedDict, Union, Dict, Optional

from sqlalchemy import or_
from pydantic import model_validator, field_validator, ValidationError,BaseModel

from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict, CommonOptView
from websdk2.sqlalchemy_pagination import paginate

from models.secret import SecretModels
from libs.mycrypt import mc

opt_obj = CommonOptView(SecretModels)

class CommonResponseDict(TypedDict):
    code: int
    msg: str
    data: Union[List[Any], Dict[str, Any]]
    count: Optional[int] = None

class Secret(BaseModel):
    uuid: str
    secret: str

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "uuid" not in values or not values["uuid"]:
            raise ValueError("uuid不能为空")
        if "secret" not in values or not values["secret"]:
            raise ValueError("secret不能为空")
        return values

    @field_validator('uuid')
    def uuid_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("uuid必须为字符串")
        return v

    @field_validator('secret')
    def secret_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("secret必须为字符串")
        return v


def _get_secret_by_val(value: str = None) -> Any:
    """
    模糊查询

    Args:
        value (str, optional): 模糊查询value. Defaults to None.

    Returns:
        _type_: 查询条件
    """
    if not value:
        return True

    return or_(
        SecretModels.uuid.like(f"%{value}%"),
        SecretModels.secret.like(f"%{value}%"),
    )


def get_secret_by_uuid(uuid: str) -> dict:
    """
    根据uuid查询数据库

    Args:
        uuid (str): uuid

    Returns:
        Secret: 密钥信息
    """
    with DBContext('r') as session:
        secret_obj = session.query(SecretModels).filter(SecretModels.uuid == uuid.strip()).first()
        if not secret_obj:
            return {}
        return model_to_dict(secret_obj)
    
def get_secret_by_uuid_for_api(uuid: str) -> CommonResponseDict:
    """
    根据uuid查询密钥
    
    Args:
        uuid (str): uuid

    Returns:
        Secret: 密钥信息
    """
    secret_obj = get_secret_by_uuid(uuid)
    if not secret_obj:
        return dict(code=-1, msg="查询失败", data=[])
    secret_obj['secret'] = mc.my_decrypt(secret_obj['secret'])
    return CommonResponseDict(code=0, msg="查询成功", data=secret_obj)
    
def get_secret_list_for_api(**params: dict) -> CommonResponseDict:
    """ 查询欢乐剑密钥列表
    Args:
        params(dict): 查询参数
    """
    value = params.get('searchValue') or params.get('searchVal')
    filter_map = params.pop('filter_map', {})
    if 'page_size' not in params:
        params.setdefault("page_size", 300) # 默认获取到全部数据
    if 'order' not in params: 
        params.setdefault("order", 'descend')
    if "uuid" in params:
        # 根据uuid查询
        uuid = params.pop('uuid')
        return get_secret_by_uuid_for_api(uuid)
    with DBContext('r') as session:
        page = paginate(session.query(SecretModels).filter(_get_secret_by_val(value)).filter_by(**filter_map), **params)
    # 解密
    decrypted_items = []
    for item in page.items:
        item["secret"] = mc.my_decrypt(item["secret"])
        decrypted_items.append(item)
    return CommonResponseDict(
        code=0, msg="获取成功", data=decrypted_items, count=page.total
    )


def add_secret_for_api(data: dict) -> CommonResponseDict:
    """ 
    添加欢乐剑密钥
    
    Args:
        data(dict): 数据字典
    Returns:
        CommonResponseDict: 返回结果
    """
    try:
        secret_obj = Secret(**data)
    except ValidationError as e:
        return CommonResponseDict(code=-1, msg=f"参数不合法:{str(e)}")
    secret_obj.secret = mc.my_encrypt(secret_obj.secret)
    with DBContext('w', None, True) as session:
        if get_secret_by_uuid(secret_obj.uuid):
            return CommonResponseDict(code=-1, msg="添加失败，已存在")
        secret_obj = SecretModels(**secret_obj.model_dump())
        session.add(secret_obj)
    return CommonResponseDict(code=0, msg="添加成功")

