#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
Desc    : 集群模板
"""

from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate
from websdk2.db_context import DBContextV2 as DBContext
from models.tree import TreeModels
from models.business import BizModels, SetTempModels
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(SetTempModels)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        SetTempModels.id == value,
        SetTempModels.temp_name.like(f'%{value}%'),
        SetTempModels.temp_data.like(f'%{value}%'),
        SetTempModels.create_user.like(f'%{value}%')
    )


def get_temp_list(**params):
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(SetTempModels).filter(_get_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def set_temp_batch(data: dict) -> dict:
    biz_id = data.get('biz_id')
    env_name = data.get('env_name')
    temp_id = data.get('temp_id')
    app_way = data.get('app_way')
    if not env_name:
        return dict(code=-1, msg='环境错误')

    if app_way == "model1":
        set_list = data.get('set_list')
        set_list = set_list.replace(',', ' ')
        set_list = set_list.split()
    elif app_way == "model2":
        set_name = data.get('set_name')
        num_range = data.get('num_range')
        delimiter = data.get('delimiter', '_')
        num_range_list = num_range.split(',')
        if not set_name:
            return dict(code=-2, msg='集群错误')

        if len(num_range_list) != 2:
            return dict(code=-4, msg='编号范围错误2')
        try:
            set_list = [f"{set_name}{delimiter}{i}" for i in range(int(num_range_list[0]), int(num_range_list[1]))]
        except Exception as err:
            return dict(code=-5, msg='编号错误，请参考说明文档')
    else:
        return dict(code=-6, msg='无效模式')

    if not set_list:
        return dict(code=-7, msg='集群不能为空')

    with DBContext('w', None, True) as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-6, msg='租户ID错误')
        _info = session.query(TreeModels).filter(TreeModels.biz_id == biz_id, TreeModels.parent_node == env_name,
                                                 TreeModels.node_type == 2).filter(
            TreeModels.title.in_(set_list)).first()
        if _info:
            return dict(code=-7, msg=f'模块冲突，以及存在模块 {_info.title}')

        temp_data = session.query(SetTempModels.temp_data).filter(SetTempModels.id == temp_id).first()

        if not temp_data:
            return dict(code=-8, msg='查询不到相关模板')
        set_temp_items = temp_data[0]['items']
        module_list = [item['module_name'] for item in set_temp_items]
        if not module_list:
            return dict(code=-9, msg='不能从模板里面获取到模块信息')

        set_set = [TreeModels(biz_id=biz_id, parent_node=env_name, title=set_name, ext_info={}, node_type=2,
                              node_sort=100)
                   for set_name in set_list]

        module_set = [TreeModels(biz_id=biz_id, grand_node=env_name, parent_node=set_name, title=module_name,
                                 node_type=3, node_sort=100)
                      for module_name in module_list
                      for set_name in set_list]
        set_set.extend(module_set)
        session.add_all(set_set)
        return dict(code=0, msg='批量添加完成')
