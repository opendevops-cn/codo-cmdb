#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   asset_switch_service.py
# @Time    :   2024/12/05 12:05:30
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   内网交换机

from typing import Optional, List

from pydantic import BaseModel, field_validator, ValidationError
from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView
from pysnmp.hlapi import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    getCmd,
)

from models.asset import AssetSwitchModels
from settings import settings

opt_obj_switch = CommonOptView(AssetSwitchModels)


def get_snmp_data(ip: str, community: str, oid: str) -> str:
    """
    获取 SNMP 数据。

    :param ip: 设备 IP 地址
    :param community: SNMP 公共团体字符串
    :param oid: 要查询的 OID
    :return: 查询结果或 None
    """
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=0),  # SNMP v1 或 v2c
            UdpTransportTarget((ip, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        errorIndication, errorStatus, _, varBinds = next(iterator)

        if errorIndication:
            return ""

        if errorStatus:
            return ""

        for varBind in varBinds:
            bind_oid, bind_value = varBind
            if str(bind_oid) == oid:  # 转换为字符串进行比较
                return str(bind_value)

    except Exception:
        return ""


def get_snmp_model(
    ip: str, community: Optional[str]=None, oid: Optional[str] = None
) -> str:
    """查询内网交换机设备型号

    Args:
        ip (str): 交换机 IP 地址
        community (str):  SNMP 公共团体字符串
        oid (str): 型号对应的 OID
    Returns:
        Optional[str]: 设备型号或空字符串
    """
    if community is None:
        community = settings.get("switch_community", "")
    if oid is None:
        oid = settings.get("switch_model_oid", "")
    model = get_snmp_data(ip=ip, community=community, oid=oid)
    sep = "\r\n"
    if sep in model:
        return model.split(sep)[0]
    return model


def get_snmp_name(
    ip: str, community: Optional[str]=None, oid: Optional[str] = None
) -> str:
    """查询内网交换机设备名称

    Args:
        ip (str): 交换机IP地址
        community (str): SNMP 公共团体字符串
        oid (str): 型号对应的 OID

    Returns:
        Optional[str]: 设备型名称或空字符串
    """
    if community is None:
        community = settings.get("switch_community", "")
    if oid is None:
        oid = settings.get("switch_name_oid", "")
    return get_snmp_data(ip=ip, community=community, oid=oid)


def get_snmp_sn(
    ip: str, community: Optional[str]=None, oid: Optional[str] = None
) -> str:
    """查询内网交换机设备序列号

    Args:
        ip (str): 交换机IP地址
        community (str): SNMP 公共团体字符串
        oid (str): 型号对应的 OID'.

    Returns:
        str: Optional[str]: 设备型号序列号或空字符串
    """
    if community is None:
        community = settings.get("switch_community", "")
    if oid is None:
        oid = settings.get("switch_sn_oid", "")
    return get_snmp_data(ip=ip, community=community, oid=oid)



class SwitchBase(BaseModel):
    """交换机设备模型"""
    name: str = None
    manage_ip: str
    sn: str = None
    mac_address: str 
    vendor: str
    model: str = None
    idc: str
    rack: str
    position: int
    role: str
    status: str = ''
    description: Optional[str] = None

    @field_validator("mac_address")
    def normalize_mac_address(cls, v):
        """标准化MAC地址格式"""
        # 移除所有分隔符
        mac = "".join(c for c in v if c.isalnum())
        # 转换为大写
        mac = mac.upper()
        # 格式化为标准格式 (XX:XX:XX:XX:XX:XX)
        return ":".join(mac[i : i + 2] for i in range(0, 12, 2))

    @field_validator("manage_ip")
    def validate_ip(cls, v):
        """验证IP地址"""
        try:
            ip = str(v)
            # 可以添加其他IP地址验证规则
            if ip.startswith("127."):
                raise ValueError("不能使用本地回环地址")
            if ip.startswith("169.254."):
                raise ValueError("不能使用链路本地地址")
        except Exception as e:
            raise ValueError(f"无效的IP地址: {str(e)}")
        return v
    
class BatchSwitchCreate(BaseModel):
    devices: List[SwitchBase]


def _get_switch_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetSwitchModels.id == search_val,
        AssetSwitchModels.vendor.like(f"%{search_val}%"),
        AssetSwitchModels.name.like(f"%{search_val}%"),
        AssetSwitchModels.manage_ip.like(f"%{search_val}%"),
        AssetSwitchModels.sn.like(f"%{search_val}%"),
        AssetSwitchModels.mac_address.like(f"%{search_val}%"),
        AssetSwitchModels.model.like(f"%{search_val}%"),
        AssetSwitchModels.idc.like(f"%{search_val}%"),
        AssetSwitchModels.rack.like(f"%{search_val}%"),
        AssetSwitchModels.position.like(f"%{search_val}%"),
        AssetSwitchModels.role.like(f"%{search_val}%"),
        AssetSwitchModels.status.like(f"%{search_val}%")
    )


def get_switch_list_for_api(**params) -> dict:
    value = (
        params.get("searchValue")
        if "searchValue" in params
        else params.get("searchVal")
    )
    filter_map = params.pop("filter_map") if "filter_map" in params else {}
    if "page_size" not in params:
        params["page_size"] = 300  # 默认获取到全部数据
    with DBContext("r") as session:
        page = paginate(
            session.query(AssetSwitchModels)
            .filter(
                _get_switch_by_val(value),
            )
            .filter_by(**filter_map),
            **params,
        )
    return dict(code=0, msg="获取成功", data=page.items, count=page.total)


def delete_switch_list_for_api(**data) -> dict:
    """删除内网交换机

    Returns:
        dict: {"code": "", "data": "", "msg": ""}
    """
    # names


def import_switch(data: List[SwitchBase]) -> dict:
    result = {
        "success_count": 0,
        "failed_count": 0,
        "errors": []
    }
    valid_switches = []
    file_content =  data.get("data", [])
    if not file_content:
        return dict(code=-1, msg="无数据可导入", data=result)
    
    # 验证数据
    for index, switch in enumerate(file_content):
        try:            
            item = SwitchBase(**switch)
            result["success_count"] += 1
            sn = get_snmp_sn(item.manage_ip)
            item.sn = sn
            name = get_snmp_name(item.manage_ip)
            item.name = name
            model = get_snmp_model(item.manage_ip)
            item.model = model
            valid_switches.append(item)
        except ValidationError as e:
            result["failed_count"] += 1
            errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            result["errors"].append(f"第 {index + 1} 行数据验证失败: {errors}")
        except Exception as e:
            result["failed_count"] += 1
            result["errors"].append(f"第 {index + 1} 行处理失败: {str(e)}")
    
    if result["failed_count"] > 0:
        return dict(code=-1, msg='数据校验失败', data=result)
            
    if valid_switches:
        with DBContext("r") as session:
            try:
                session.bulk_insert_mappings(
                    AssetSwitchModels,
                    [item.model_dump() for item in valid_switches],
                )
                session.commit()
            except Exception as e:
                result["failed_count"] += len(valid_switches)
                result["success_count"] -= len(valid_switches)
                result["errors"].append(f"数据库操作失败: {str(e)}")
    
    return dict(code=0, msg="操作完成", data=result)
    

