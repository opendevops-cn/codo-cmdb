# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/30
# @Description: 权限分组

import logging
from typing import *
from shortuuid import uuid

from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import CommonOptView, model_to_dict

from models.business import PermissionGroupModels
from models.asset import AssetServerModels
from services.dynamic_group_service import get_dynamic_hosts_for_biz

opt_obj = CommonOptView(PermissionGroupModels)

public_resource = "公共项目"
public_tenantid = "501"


def add_perm_group_for_api(data: dict) -> dict:
    """

    :param data:
    :return:
    """
    perm_group_name = data.get("perm_group_name")
    if not perm_group_name:
        return {"code": 1, "msg": "权限分组名称不能为空"}
    perm_type = data.get("perm_type")
    if not perm_type:
        return {"code": 1, "msg": "权限类型不能为空"}
    user_group = data.get("user_group")
    if not user_group:
        return {"code": 1, "msg": "用户组不能为空"}
    data['user_group'] = ",".join(user_group)
    data['exec_uuid'] = uuid()
    try:
        with DBContext('w', None, True) as session:
            exist_obj = session.query(PermissionGroupModels).filter(
                PermissionGroupModels.perm_group_name == perm_group_name).first()
            if exist_obj:
                return {"code": 1,
                        "msg": f"{perm_group_name} already exists."}

            session.add(PermissionGroupModels(**data))
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}

    return {"code": 0, "msg": "添加成功"}


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        PermissionGroupModels.perm_group_name.like(f'%{value}%'),
        PermissionGroupModels.exec_uuid.like(f'%{value}%'),
        PermissionGroupModels.modify_user.like(f'%{value}%'),
        PermissionGroupModels.biz_id == value,
        PermissionGroupModels.perm_type == value,
        PermissionGroupModels.perm_group_detail.like(f'%{value}%'),
        PermissionGroupModels.user_group.like(f'%{value}%'),
    )


def get_perm_group_list_for_api(**params) -> dict:
    value = params.get(
        'searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    biz_id = filter_map.pop('biz_id') if filter_map.get('biz_id') else params.get('biz_id')

    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(PermissionGroupModels).filter(_get_value(value)).filter_by(**filter_map),
                        **params)

    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def update_perm_group_for_api(data: dict) -> dict:
    if 'id' not in data:
        return {"code": 1, "msg": "权限分组ID不能为空"}
    if 'perm_group_name' not in data:
        return {"code": 1, "msg": "权限分组名称不能为空"}
    if 'perm_type' not in data:
        return {"code": 1, "msg": "权限分组类型不能为空"}
    if 'biz_id' not in data:
        return {"code": 1, "msg": "业务ID不能为空"}
    user_group = data.get("user_group")
    if not user_group:
        return {"code": 1, "msg": "用户组不能为空"}
    data['user_group'] = ",".join(user_group)
    new_data = dict(
        biz_id=data.get('biz_id'), perm_group_name=data.get('perm_group_name'),
        perm_type=data.get('perm_type'),
        modify_user=data.get('modify_user', 'admin'),
        perm_group_detail=data.get('perm_group_detail'),
        user_group=data['user_group'],
        env_name=data.get('env_name'), region_name=data.get('region_name'),
        module_name=data.get('module_name'),

    )
    try:
        with DBContext('w', None, True) as session:
            session.query(PermissionGroupModels).filter(PermissionGroupModels.id == data.get('id')).update(new_data)
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}
    return {"code": 0, "msg": "更新成功"}


def preview_perm_group_for_api(exec_uuid_list: list) -> dict:
    res_list = []

    with DBContext('r') as session:
        for exec_id in exec_uuid_list:
            group_info = session.query(PermissionGroupModels).filter(PermissionGroupModels.exec_uuid == exec_id).first()
            if not group_info:
                return dict(code=-1, msg='权限分组ID不存在', data=[])

            is_success, result = get_dynamic_hosts_for_biz(model_to_dict(group_info))
            if not is_success or not result:
                logging.error(f"biz {exec_id} 没有发现主机信息")
            res_list.extend(result)

        asset_set = set(res_list)

        try:
            the_model = AssetServerModels
            __asset = session.query(the_model.instance_id, the_model.name, the_model.inner_ip, the_model.outer_ip,
                                    the_model.state, the_model.agent_status, the_model.agent_id).filter(
                the_model.id.in_(asset_set)).all()

            server_list = [dict(zip(res.keys(), res)) for res in __asset]
            __count = len(server_list)
            return dict(msg='获取成功', code=0, data=server_list, count=__count)
        except Exception as error:
            logging.error(f"{error} 获取主机失败")
            return dict(msg='获取失败', code=-1)
