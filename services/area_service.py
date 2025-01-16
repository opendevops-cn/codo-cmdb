# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: CBB区服接口
import time
from typing import List, Optional, Dict, Any
from functools import wraps

from pydantic import BaseModel, ValidationError, model_validator, field_validator

from libs.api_gateway.cbb.area import AreaAPI
from libs.api_gateway.cbb.big_area import BigAreaAPI
from libs.api_gateway.cbb.sign import Signer
from libs.mycrypt import mc
from models import EnvType
from services.env_service import get_env_by_id

# todo 存入数据库
GameBizMapping = {
    "515": "ROmeta",
    "522": "MS2", 
    "536": "baokemeng", # 宝可梦
    "511": "ACT", # ACT
    "516": "qa", # QA
    "517": "cbb" # CBB  
}


class BigArea(BaseModel):
    big_area: str
    name: str  # 大区名称
    ext: Optional[str] = ""  # 扩展信息
    tags: List[str] = []  # 大区标签
    visible: bool = False  # 玩家是否可见
    utc_offset: int = 0  # UTC偏移
    address: str = None  # 大区地址
    protocol_converter_host: str = None  # gm回调地址

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "big_area" not in values or not values["big_area"]:
            raise ValueError("大区编号不能为空")
        if "name" not in values or not values["name"]:
            raise ValueError("大区名称不能为空")
        if "visible" not in values:
            raise ValueError("玩家可见不能为空")
        if "utc_offset" not in values:
            raise ValueError("UTC时间偏移不能为空")
        return values

    @field_validator("big_area")
    def validate_big_area(cls, v):
        if len(v) > 50:
            raise ValueError("大区编号最多50个字符")
        return v

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) > 100:
            raise ValueError("大区名称最多100个字符")
        return v

    @field_validator("tags")
    def validate_tags(cls, v):
        if len(v) > 20:
            raise ValueError("大区标签最多20个")
        for tag in v:
            if len(tag) > 15:
                raise ValueError("大区标签最多15个字符")
        return v

    @field_validator("visible", mode="before")
    def validate_visible(cls, v):
        if not isinstance(v, bool):
            raise ValueError("玩家可见必须为bool类型")
        return v


    @field_validator("utc_offset")
    def validate_utc_offset(cls, v):
        if not isinstance(v, int):
            raise ValueError("UTC时间偏移必须为int类型")
        if v < -12 or v > 14:
            raise ValueError("UTC时间偏移必须在-12到14之间")
        return v

    @field_validator("address")
    def validate_address(cls, v):
        if len(v) > 50:
            raise ValueError("ping地址最多50个字符")
        return v

    @field_validator("ext")
    def validate_ext(cls, v):
        if len(v) > 500:
            raise ValueError("ext最多500个字符")
        return v
    
    @field_validator("protocol_converter_host")
    def validate_protocol_converter_host(cls, v):
        if len(v) > 1000:
            raise ValueError("protocol_converter_host最多1000个字符")
        return v

class Area(BaseModel):
    area: str  # 区服编号
    name: str  # 区服名
    tags: List[str] = []  # 区服标签
    state: int  # 区服状态 (0:维护中, 1:流畅, 2:拥挤, 3:火爆)
    big_area: str  # 所属大区id
    ext: Optional[str] = "" # 附加信息
    max_reg_count: int  # 最大注册人数
    max_alive_count: int  # 最大在线人数
    is_top: bool  # 是否为置顶
    open_timestamp: int  # 开服时间(ms)
    visible: bool  # 玩家可见
    gate_address: List[str] = []  # 区服网关地址

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "area" not in values or not values["area"]:
            raise ValueError("区服编号不能为空")
        if "name" not in values or not values["name"]:
            raise ValueError("区服名称不能为空")
        if "state" not in values:
            raise ValueError("区服状态不能为空")
        if "big_area" not in values or not values["big_area"]:
            raise ValueError("所属大区id不能为空")
        if "max_reg_count" not in values:
            raise ValueError("最大注册人数不能为空")
        if "max_alive_count" not in values:
            raise ValueError("最大在线人数不能为空")
        if "is_top" not in values:
            raise ValueError("是否置顶不能为空")
        if "open_timestamp" not in values:
            raise ValueError("开服时间(ms)不能为空")
        if "visible" not in values:
            raise ValueError("玩家可见不能为空")
        if "gate_address" not in values:
            raise ValueError("区服网关地址不能为空")
        return values

    @field_validator('area')
    def validate_area(cls, v):
        if not v:
            raise ValueError("区服编号不能为空")
        if len(v) > 50:
            raise ValueError("区服编号最多50个字符")
        return v

    @field_validator("name")
    def validate_name(cls, v):
        if not v:
            raise ValueError("区服名称不能为空")
        if len(v) > 100:
            raise ValueError("区服名称最多100个字符")
        return v

    @field_validator("tags")
    def validate_tags(cls, v):
        if len(v) > 20:
            raise ValueError("区服标签最多20个")
        for tag in v:
            if len(tag) > 15:
                raise ValueError("区服标签最多15个字符")
        return v

    @field_validator("gate_address", mode="before")
    def validate_gate_address(cls, v):
        if not isinstance(v, list):
            raise ValueError("区服网关地址必须为list类型")
        if len(v) < 1:
            raise ValueError("区服网关地址不能为空")
        if len(v) > 20:
            raise ValueError("区服网关地址最多20个")
        for address in v:
            if len(address) > 50:
                raise ValueError("区服网关地址最多50个字符")
        return v

    @field_validator("state", mode="before")
    def validate_state(cls, v):
        if v not in [0, 1, 2, 3]:
            raise ValueError("区服状态必须为0, 1, 2, 3")
        return v

    @field_validator("big_area")
    def validate_big_area(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("所属大区id不能为空")
        if len(v) > 50:
            raise ValueError("所属大区id最多50个字符")
        return v

    @field_validator("ext")
    def validate_ext(cls, v):
        if len(v) > 1000:
            raise ValueError("附加信息最多500个字符")
        return v

    @field_validator("max_reg_count")
    def validate_max_reg_count(cls, v):
        if not isinstance(v, int):
            raise ValueError("最大注册人数必须为int类型")
        if v < 0:
            raise ValueError("最大注册人数必须大于等于0")
        return v

    @field_validator("max_alive_count")
    def validate_max_alive_count(cls, v):
        if not isinstance(v, int):
            raise ValueError("最大在线人数必须为int类型")
        if v < 0:
            raise ValueError("最大在线人数必须大于等于0")
        return v

    @field_validator("is_top", mode="before")
    def validate_is_top(cls, v):
        if not isinstance(v, bool):
            raise ValueError("是否置顶必须为bool类型")
        return v

    @field_validator("open_timestamp")
    def validate_open_timestamp(cls, v):
        if not isinstance(v, int):
            raise ValueError("开服时间(ms)必须为int类型")
        return v

    @field_validator("visible", mode="before")
    def validate_visible(cls, v):
        if not isinstance(v, bool):
            raise ValueError("玩家可见必须为bool类型")
        return v


def handle_api_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return dict(code=-1, msg='参数错误', data=str(e))
        except ValueError as e:
            return dict(code=-1, msg=str(e), data=[])
        except Exception as e:
            return dict(code=-1, msg=str(e), data=[])
    return wrapper


def get_env_details(env_id: int) -> Dict[str, Any]:
    env = get_env_by_id(env_id)
    if not env:
        raise ValueError('环境不存在')
    required_fields = ['idip', 'app_secret', 'app_id']
    for field in required_fields:
        if not env.get(field):
            raise ValueError(f'环境{field}不存在')
    return env


def get_game_appid(biz_id: str) -> str:
    game_appid = GameBizMapping.get(str(biz_id))
    if not game_appid:
        raise ValueError('当前业务暂无相关数据,请切换到RO3或MS2业务')
    return game_appid


@handle_api_exceptions
def get_big_area_list(**params):
    """
    获取大区列表.
    :param params.
    :return: 大区列表.
    """
    tag_filter = params.pop('tag_filter', None)
    big_area = params.pop('big_area', None)
    env_id = params.pop('env_id', 0)
    searchValue = params.pop('searchValue', None)
    page = int(params.pop('page', 1)) or 1
    limit = int(params.pop('limit', 10)) or 10
    biz_id = params.pop('biz_id')
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    big_area_api = BigAreaAPI(signer, env['idip'], game_appid)
    big_areas = big_area_api.get_big_areas(tag_filter=tag_filter, big_area=big_area, query_string=searchValue,
                                           page_no=page, page_size=limit)
    big_areas_body = big_areas.get("body", {})
    big_area_list = big_areas_body.get('big_areas', [])
    big_area_count = big_areas_body.get('big_area_count', 0)
    for big_area in big_area_list:
        big_area.update({'env_id': env_id, 'env_name': env.get('env_name'), 'env_type': env.get('env_type')})
    return dict(code=0, msg='获取成功', data=big_area_list, count=big_area_count)


@handle_api_exceptions
def get_big_area_detail(**params):
    """
    获取大区.
    :param params.
    :return: 大区详情.
    """
    tag_filter = params.pop('tag_filter', None)
    big_area = params.pop('big_area', None)
    env_id = params.pop('env_id', 0)
    biz_id = params.pop('biz_id', "")
    if not big_area:
        return dict(code=-1, msg='大区id不能为空', data=[])
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    big_area_api = BigAreaAPI(signer, env['idip'], game_appid)
    big_areas = big_area_api.get_big_area_detail(tag_filter=tag_filter, big_area=big_area)
    big_areas_body = big_areas.get("body", {})
    big_area_list = big_areas_body.get('big_areas', [])
    for big_area in big_area_list:
        big_area.update({'env_id': env_id, 'env_name': env.get('env_name'), 'env_type': env.get('env_type')})
    return dict(code=0, msg='获取成功', data=big_area_list)


@handle_api_exceptions
def create_or_update_big_area(**data):
    """
    创建或更新大区.
    :param data: 大区数据.
    """
    env_id = data.pop('env_id', 0)
    if not env_id:
        return dict(code=-1, msg='环境id不能为空', data=[])
    biz_id = data.pop('biz_id')
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    big_area_api = BigAreaAPI(signer, env['idip'], game_appid)
    big_area = BigArea(**data)
    result = big_area_api.create_or_update_big_area(**big_area.model_dump())
    return dict(code=0, msg='操作成功', data=result)


@handle_api_exceptions
def delete_big_area(big_area: str, env_id: int, biz_id: str):
    """
    删除大区.
    :param big_area: 大区id.
    :param env_id: 环境id.
    :param biz_id: 业务appid.
    """
    if not big_area:
        return dict(code=-1, msg='大区id不能为空', data=[])
    if not env_id:
        return dict(code=-1, msg='环境id不能为空', data=[])
    if not biz_id:
        return dict(code=-1, msg='业务不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    big_area_api = BigAreaAPI(signer, env['idip'], game_appid)
    big_area_obj = big_area_api.get_big_areas(big_area=big_area)
    if not big_area_obj:
        return dict(code=-1, msg='大区不存在', data=[])
    area_list = get_area_list(big_area=big_area)
    if area_list.get('data', []):
        return dict(code=-1, msg='请先删除大区下的所有区服', data=[])
    result = big_area_api.delete_big_area(big_area)
    return dict(code=0, msg='操作成功', data=result)


@handle_api_exceptions
def get_area_list(**params):
    """
    获取区服列表.
    """
    tag_filter = params.pop('tag_filter', None)
    area = params.pop('area', None)
    big_area = params.pop('big_area', None)
    if not big_area:
        return dict(code=-1, msg='大区id不能为空', data=[])
    env_id = params.pop('env_id', 0)
    searchValue = params.pop('searchValue', None)
    page = int(params.pop('page', 1)) or 1
    limit = int(params.pop('limit', 10)) or 10
    biz_id = params.pop('biz_id', "")
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    area_api = AreaAPI(signer, env['idip'], game_appid)
    areas = area_api.get_areas(tag_filter=tag_filter, area=area, big_area=big_area, query_string=searchValue,
                               page_no=page, page_size=limit)
    areas_body = areas.get("body", {})
    area_list = areas_body.get('areas', [])
    area_count = areas_body.get('area_count', 0)
    for r in area_list:
        r.update({'env_id': env_id, 'env_name': env.get('env_name'), 'big_area': big_area, 'env_type': env.get('env_type')})
    return dict(code=0, msg='获取成功', data=area_list, count=area_count)

@handle_api_exceptions
def create_area(**data):
    """
    创建区服.
    :param data: 区服数据.
    """
    biz_id = data.pop('biz_id', "")
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env_id = data.pop('env_id')
    if not env_id:
        return dict(code=-1, msg='环境id不能为空', data=[])
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    area_api = AreaAPI(signer, env['idip'], game_appid)
    area = Area(**data)
    result = area_api.create_or_update_area(**area.model_dump())
    return dict(code=0, msg='操作成功', data=result)


@handle_api_exceptions
def update_area(**data):
    """
    更新区服.
    """
    biz_id = data.pop('biz_id', "")
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = get_game_appid(biz_id)
    env_id = data.pop('env_id')
    if not env_id:
        return dict(code=-1, msg='环境id不能为空', data=[])
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    area_api = AreaAPI(signer, env['idip'], game_appid)
    area_obj = area_api.get_area(area=data.get('area'), big_area=data.get('big_area'))
    detail = area_obj.get('body', {}).get('areas', [])
    if not detail:
        return dict(code=-1, msg='区服不存在', data=[])
    env_type = env["env_type"]
    gate_address = data.get('gate_address', [])
    if env_type == EnvType.Prd:
        curr_gate_address = detail[0].get('gate_address', [])
        if set(gate_address) != set(curr_gate_address):
            return dict(code=-1, msg='生产环境不允许编辑区服网关地址，请联系运维修改', data=[])
        now = int(time.time() * 1000)
        open_timestamp = data.get('open_timestamp')
        curr_open_timestamp = detail[0].get('open_timestamp')
        if now > open_timestamp and open_timestamp != curr_open_timestamp:
            return dict(code=-1, msg='生产环境下当前时间超过开服时间后，开服时间不允许编辑', data=[])
    area = Area(**data)
    result = area_api.create_or_update_area(**area.model_dump())
    return dict(code=0, msg='操作成功', data=result)


@handle_api_exceptions
def delete_area(**data):
    """
    删除区服.
    """
    biz_id = data.pop('biz_id')
    if not biz_id:
        return dict(code=-1, msg='业务id不能为空', data=[])
    game_appid = GameBizMapping.get(str(biz_id))
    if not game_appid:
        return dict(code=-1, msg='当前业务暂无相关数据', data=[])
    area = data.pop('area', None)
    if not area:
        return dict(code=-1, msg='区服id不能为空', data=[])
    big_area = data.pop('big_area', None)
    if not big_area:
        return dict(code=-1, msg='大区id不能为空', data=[])
    env_id = data.pop('env_id')
    if not env_id:
        return dict(code=-1, msg='环境id不能为空', data=[])
    env = get_env_details(env_id)
    signer = Signer(secret=mc.my_decrypt(env['app_secret']), app_id=env['app_id'])
    area_api = AreaAPI(signer, env['idip'], game_appid)
    areas = area_api.get_areas(area=area, big_area=big_area)
    areas_body = areas.get("body", {})
    area_list = areas_body.get('areas', [])
    if not area_list:
        return dict(code=-1, msg='区服不存在', data=[])
    result, msg = area_api.delete_area(area=area, big_area=big_area)
    if not result:
        return dict(code=-1, msg=msg, data=[])
    return dict(code=0, msg='操作成功', data=[])
