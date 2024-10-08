# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/23
# @Description: 区服环境

from typing import Optional, List
from collections import namedtuple

from pydantic import model_validator, field_validator, ValidationError, BaseModel, validator
from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView
from websdk2.model_utils import model_to_dict

from models.env import EnvModels
from libs.mycrypt import mc

opt_obj = CommonOptView(EnvModels)

class EnvData(BaseModel):
    env_name: str
    env_no: str
    is_test: int
    idip: str
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    ext_info: Optional[str] = None
    env_tags: List[str] = []

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "env_name" not in values or not values["env_name"]:
            raise ValueError("env_name不能为空")
        if "env_no" not in values or not values["env_no"]:
            raise ValueError("env_no不能为空")
        if "is_test" not in values:
            raise ValueError("is_test不能为空")
        if "idip" not in values or not values["idip"]:
            raise ValueError("idip不能为空")
        if "app_id" not in values or not values["app_id"]:
            raise ValueError("app_id不能为空")
        if "app_secret" not in values or not values["app_secret"]:
            raise ValueError("app_secret不能为空")
        return values

    @field_validator('is_test', mode="before")
    def is_test_must_be_int(cls, v):
        if not isinstance(v, bool):
            raise ValueError("is_test必须为布尔类型")
        return v

    @field_validator('env_tags')
    def env_tags_must_be_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("env_tags必须为列表")
        if len(v) > 20:
            raise ValueError("env_tags最多只能有20个")
        for i in v:
            if len(i) > 15:
                raise ValueError("env_tags中的每个元素长度不能超过15")
        return v

    @field_validator('ext_info')
    def ext_info_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("ext_info必须为字符串")
        if len(v) > 1000:
            raise ValueError("ext_info长度不能超过1000")
        return v

    @field_validator('idip', mode="before")
    def idip_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("idip必须为字符串")
        if len(v) > 50:
            raise ValueError("idip长度不能超过50")
        return v

    @field_validator('env_no', mode="before")
    def env_no_must_be_str(cls, v):
        if not isinstance(v, int):
            raise ValueError("env_no必须为整数")
        if len(str(v)) > 50:
            raise ValueError("env_no长度不能超过50")
        return v

    @field_validator('env_name', mode="before")
    def env_name_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("env_name必须为字符串")
        if len(v) > 100:
            raise ValueError("env_name长度不能超过100")
        return v

    @field_validator('app_id', mode="before")
    def app_id_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("app_id必须为字符串")
        if len(v) > 100:
            raise ValueError("app_id长度不能超过100")
        return v

    @field_validator('app_secret', mode="before")
    def app_secret_must_be_str(cls, v):
        if not isinstance(v, str):
            raise ValueError("app_secret必须为字符串")
        if len(v) > 255:
            raise ValueError("app_secret长度不能超过255")
        return v


def _get_env_by_val(value: str = None):
    """模糊查询"""
    if not value:
        return True

    return or_(
        EnvModels.env_name.like(f'%{value}%'),
        EnvModels.env_no.like(f'%{value}%'),
        EnvModels.env_tags.like(f'%{value}%'),
        EnvModels.is_test.like(f'%{value}%'),
        EnvModels.idip.like(f'%{value}%'),
        EnvModels.ext_info.like(f'%{value}%'),
    )


def get_env_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    if 'order_by' not in params: params['order_by'] = 'is_test'
    if 'order' not in params: params['order'] = 'descend'
    with DBContext('r') as session:
        page = paginate(session.query(EnvModels).filter(_get_env_by_val(value),
                                                       ).filter_by(**filter_map), **params)
    # 优先展示非测试环境，其余使用环境编号倒排
    items = [item for item in page.items if not item["is_test"]] + \
    sorted([item for item in page.items if item["is_test"]], key=lambda x: int(x["env_no"]), reverse=True)
    return dict(code=0, msg='获取成功', data=items, count=page.total)


def get_all_env_list_for_api() -> dict:
    env_obj = namedtuple('Env', ['id', 'env_name', 'env_no'])
    try:
        with DBContext('r') as session:
            envs = session.query(EnvModels).filter()
            env_list = [env_obj(env.id, env.env_name, env.env_no)._asdict() for env in envs]
        return dict(code=0, msg='获取成功', data=env_list, count=envs.count())
    except Exception as e:
        return dict(code=-1, msg=str(e))


def update_env_for_api(data: dict) -> dict:
    """更新数据"""
    try:
        env_data = EnvData(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))
    try:
        with DBContext('w', None, True) as session:
            env_id = data.pop('id')
            if not env_id:
                return dict(code=-1, msg='ID不能为空')
            env_obj = session.query(EnvModels).filter(EnvModels.id == env_id).first()
            if not env_obj:
                return dict(code=-1, msg='环境不存在')
            if env_obj.app_secret != env_data.app_secret:
                # 修改app_secret加密
                env_data.app_secret = mc.my_encrypt(env_data.app_secret)
            session.query(EnvModels).filter(EnvModels.id == env_id).update(env_data.model_dump())
        return dict(code=0, msg='更新成功')
    except Exception as e:
        return dict(code=-1, msg=str(e))


def add_env_for_api(data: dict) -> dict:
    """添加数据"""
    try:
        env_data = EnvData(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))
    # app_secret加密
    env_data.app_secret = mc.my_encrypt(env_data.app_secret)
    try:
        with DBContext('w', None, True) as session:
            if session.query(EnvModels).filter(EnvModels.env_no == env_data.env_no).first():
                return dict(code=-1, msg='环境编号已存在')
            session.add(EnvModels(**env_data.model_dump()))
        return dict(code=0, msg='创建成功')
    except Exception as e:
        return dict(code=-1, msg=str(e))

def get_env_by_id(env_id: int) -> dict:
    """根据ID获取数据"""
    with DBContext('r') as session:
        env_obj = session.query(EnvModels).filter(EnvModels.id == env_id).first()
        if not env_obj:
            return {}
        return model_to_dict(env_obj)