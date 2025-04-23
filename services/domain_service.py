#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018年5月7日
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from shortuuid import uuid
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.utils.pydantic_utils import ValidationError, sqlalchemy_to_pydantic

from models.domain import DomainName, DomainOptLog, DomainRecords


class CreateDomainName(BaseModel):
    domain_name: str = Field(..., title="域名", description="域名")
    remark: str = Field(default="", title="备注", description="备注")
    record_end_time: datetime = Field(..., title="过期时间", description="过期时间")
    domain_id: str = Field(default="", title="domain_id", description="domain_id")
    domain_state: str = Field(default="正常", title="域名状态", description="域名状态")

    @field_validator("domain_name", "record_end_time", mode="before")
    @classmethod
    def validate_not_empty(cls, v: str, info):
        v = v.strip() if isinstance(v, str) else v
        if not v:
            field_mapping = {
                "domain_name": "域名",
                "record_end_time": "过期时间",
            }
            field_name = field_mapping.get(info.field_name)
            raise ValueError(f"{field_name}不能为空")
        return v

    def __post_init__(self):
        if not "." not in self.domain_name:
            raise ValueError("域名格式错误")
        if not self.record_end_time:
            raise ValueError("过期时间不能为空")
        if not self.domain_id:
            self.domain_id = uuid()


class UpdateDomainName(BaseModel):
    id: int = Field(..., title="ID", description="ID")
    remark: Optional[str] = Field(default="", title="备注", description="备注")
    record_end_time: Optional[datetime] = Field(None, title="过期时间", description="过期时间")
    star_mark: Optional[bool] = Field(default=False, title="星标", description="星标")

    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values: dict):
        # id 是必须的
        if "id" not in values or not str(values.get("id")).strip():
            raise ValueError("id不能为空")

        # record_end_time 只有当传入了才校验非空
        if "record_end_time" in values:
            v = values.get("record_end_time")
            if not v or (isinstance(v, str) and not v.strip()):
                raise ValueError("过期时间不能为空")

        return values


PydanticDomainNameBase = sqlalchemy_to_pydantic(DomainName, exclude=["id"])

PydanticDomainNameUP = sqlalchemy_to_pydantic(DomainName)


class PydanticDomainNameUP2(BaseModel):
    id: int
    star_mark: bool


class PydanticDomainNameDel(BaseModel):
    id_list: list[int]


def add_domain_name(data: dict) -> dict:
    try:
        valid_data = CreateDomainName(**data)
    except ValidationError as e:
        print(e.json())
        return dict(code=-1, msg=str(e))
    create_data = valid_data.model_dump()
    try:
        with DBContext("w", None, True) as db:
            db.add(DomainName(**create_data))
    except IntegrityError as e:
        print(e)
        return dict(code=-2, msg="不要重复添加相同的配置")

    except Exception as e:
        return dict(code=-3, msg=f"{e}")

    return dict(code=0, msg="创建成功")


def up_domain_name(data: dict) -> dict:
    try:
        valid_data = UpdateDomainName(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    update_data = valid_data.model_dump(exclude_unset=True)
    try:
        with DBContext("w", None, True) as db:
            db.query(DomainName).filter(DomainName.id == valid_data.id).update(update_data)

    except IntegrityError as e:
        return dict(code=-2, msg="修改失败，已存在")

    except Exception as err:
        return dict(code=-3, msg=f"修改失败, {err}")

    return dict(code=0, msg="修改成功")


def del_domain_name(data: dict):
    user = data.pop("user")
    try:
        valid_data = PydanticDomainNameDel(**data)
    except ValidationError as e:
        return dict(code=-1, msg=str(e))

    try:
        with DBContext("w", None, True) as db:
            domains = db.query(DomainName).filter(DomainName.id.in_(valid_data.id_list)).all()

            # 记录日志前先收集信息
            logs = [
                DomainOptLog(domain_name=d.domain_name, username=user, action="删除", record="删除根域名")
                for d in domains
            ]

            # 删除数据
            db.query(DomainName).filter(DomainName.id.in_(valid_data.id_list)).delete(synchronize_session=False)

            # 写入日志
            db.add_all(logs)
    except Exception as err:
        return dict(code=-3, msg=f"删除失败, {str(err)}")

    return dict(code=0, msg="删除成功")


def _get_domain_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainName.domain_name.like(f"%{value}%"),
        DomainName.cloud_name.like(f"%{value}%"),
        DomainName.version.like(f"%{value}%"),
        DomainName.account.like(f"%{value}%"),
        DomainName.id.like(f"%{value}%"),
    )


def get_cloud_domain(**params) -> dict:
    value = params.get("searchValue") if "searchValue" in params else params.get("searchVal")

    filter_map = params.pop("filter_map") if "filter_map" in params else {}
    if "biz_id" in filter_map:
        filter_map.pop("biz_id")  # 暂时不隔离
    if "page_size" not in params:
        params["page_size"] = 300  # 默认获取到全部数据

    with DBContext("r") as session:
        page = paginate(session.query(DomainName).filter(_get_domain_value(value)).filter_by(**filter_map), **params)

    return dict(msg="获取成功", code=0, count=page.total, data=page.items)


def _get_record_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainRecords.domain_rr.like(f"%{value}%"),
        DomainRecords.domain_value.like(f"%{value}%"),
        DomainRecords.domain_type.like(f"%{value}%"),
        DomainRecords.line.like(f"{value}%"),
        DomainRecords.state.like(f"%{value}%"),
        DomainRecords.account.like(f"%{value}%"),
        DomainRecords.record_id.like(f"%{value}%"),
        DomainRecords.remark.like(f"%{value}%"),
    )


def get_cloud_record(**params) -> dict:
    value = params.get("searchValue") if "searchValue" in params else params.get("searchVal")

    filter_map = params.pop("filter_map") if "filter_map" in params else {}
    if "biz_id" in filter_map:
        filter_map.pop("biz_id")  # 暂时不隔离
    if "page_size" not in params:
        params["page_size"] = 300  # 默认获取到全部数据
    domain_name = params.pop("domain_name")
    filter_map["domain_name"] = domain_name
    with DBContext("r") as session:
        page = paginate(session.query(DomainRecords).filter(_get_record_value(value)).filter_by(**filter_map), **params)

    return dict(msg="获取成功", code=0, count=page.total, data=page.items)


def _get_log_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainOptLog.username.like(f"%{value}%"),
        DomainOptLog.action.like(f"%{value}%"),
        DomainOptLog.state.like(f"%{value}%"),
        DomainOptLog.id.like(f"%{value}%"),
        DomainOptLog.update_time.like(f"%{value}%"),
        DomainOptLog.record.like(f"%{value}%"),
    )


def get_domain_opt_log(**params) -> dict:
    value = params.get("searchValue") if "searchValue" in params else params.get("searchVal")
    if "domain_name" not in params:
        return dict(code=-1, msg="关键参数域名不能为空")

    filter_map = params.pop("filter_map") if "filter_map" in params else {}
    if "order_by" not in params:
        params["order_by"] = "update_time"
    if "biz_id" in filter_map:
        filter_map.pop("biz_id")  # 暂时不隔离
    if "page_size" not in params:
        params["page_size"] = 300  # 默认获取到全部数据
    filter_map["domain_name"] = params.pop("domain_name")
    with DBContext("r") as session:
        page = paginate(session.query(DomainOptLog).filter(_get_log_value(value)).filter_by(**filter_map), **params)

    return dict(msg="获取成功", code=0, count=page.total, data=page.items)
