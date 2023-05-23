#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2013/3/27 11:02
Desc    : 解释一下吧
"""

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from websdk2.utils.pydantic_utils import sqlalchemy_to_pydantic, ValidationError, PydanticDel, BaseModel
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.business import DynamicRulesModels, BizModels
from websdk2.model_utils import GetInsertOrUpdateObj
from models import TreeAssetModels
from models.tree import TreeModels
from models import asset_mapping, des_rule_type_mapping, operator_list
from websdk2.model_utils import CommonOptView


class PydanticRulesUP(sqlalchemy_to_pydantic(DynamicRulesModels)):
    des_data: list


class PydanticDynamicRule(sqlalchemy_to_pydantic(DynamicRulesModels, exclude=['id'])):
    des_data: list


class TempOptView(CommonOptView):
    def __init__(self, model, **kwargs):
        super(TempOptView, self).__init__(model, **kwargs)
        self.model = model
        self.pydantic_model_base = PydanticRulesUP
        self.pydantic_model = PydanticDynamicRule


opt_obj = TempOptView(DynamicRulesModels)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        DynamicRulesModels.name.like(f'%{value}%'),
        DynamicRulesModels.modify_user.like(f'%{value}%')
    )


def get_dynamic_rules(**params):
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(DynamicRulesModels).filter(_get_value(value)).filter_by(**filter_map), **params)

    return page.total, page.items


def _sql_merge(asset_model, condition_dict: dict):
    sql_list = []
    for k, condition in condition_dict.items():
        print(condition)
        src_type = condition.get('src_type')
        src_operator = condition.get('src_operator')
        src_content = condition.get('src_content')

        query_value = None
        if src_operator not in operator_list: continue

        if src_operator == "包含": query_value = f"%{src_content}%"
        if src_operator == "开始": query_value = f"{src_content}%"
        if src_operator == "结束": query_value = f"%{src_content}"
        if src_operator == "==": query_value = src_content
        if query_value:
            sql_list.append(getattr(asset_model, src_type).like(query_value))
        if src_operator == "正则":
            sql_list.append(getattr(asset_model, src_type).op('regexp')(src_content))

    return sql_list


### 预览
def get_dynamic_rules_asset(**params) -> dict:
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  ### 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  ### 默认获取到全部数据
    rule_id = params.pop('id')
    with DBContext('r') as session:
        __info = session.query(DynamicRulesModels).filter_by(id=rule_id).first()
        if not __info: return dict(code=-1, msg="动态规则不存在")
        ## 查找资源模型
        asset_model = asset_mapping.get(__info.asset_type)
        if not asset_model: return dict(code=-2, msg=f"{__info.asset_type}对应的模型不存在")

        condition_list = __info.condition_list  ###  规则数据

        try:
            page = paginate(session.query(asset_model).filter(*_sql_merge(asset_model, condition_list)), **params)
            return dict(code=0, msg="获取成功", count=page.total, data=page.items)
        except Exception as err:
            return dict(code=-10, msg=f"获取失败 {err}")


def refresh_asset(data: dict) -> dict:
    # force  yes/no
    rule_id = data.pop('id')
    with DBContext('w', None, True) as session:
        __info = session.query(DynamicRulesModels).filter_by(id=rule_id).first()
        if not __info: return dict(code=-1, msg="动态规则不存在")

        des_type = __info.des_type
        asset_type = __info.asset_type
        des_data = __info.des_data
        relational_model = des_rule_type_mapping.get(des_type)
        if not relational_model: return dict(code=-2, msg=f"{des_type} 对应的关联模型不存在")

        __biz_info = session.query(BizModels).filter(BizModels.biz_cn_name == des_data[0]).first()
        if not __biz_info: return dict(code=-3, msg="业务数据查询失败")
        biz_id = __biz_info.biz_id
        if des_type == "业务":
            if len(des_data) == 1:
                print('挂载业务')
                if not __info: return dict(code=-4, msg="暂时不支持绑定业务")
            elif len(des_data) == 2:
                if not __info: return dict(code=-5, msg="暂时不支持绑定环境")
                print('挂载环境')
            elif len(des_data) == 3:
                print('挂载集群')
                filter_map = dict(region_name=des_data[2], env_name=des_data[1], biz_id=__biz_info.biz_id,
                                  asset_type=asset_type)
            elif len(des_data) == 4:
                print('挂载模块')
                filter_map = dict(module_name=des_data[3], region_name=des_data[2],
                                  env_name=des_data[1], biz_id=__biz_info.biz_id, asset_type=asset_type)

            res = get_dynamic_rules_asset(**{"id": rule_id})
            asset_list = res.get('data')
            asset_set = set([i.get('id') for i in asset_list])  ### 正则匹配数据的资产ID集合

            if len(des_data) == 3:
                try:
                    __tree_topo = session.query(TreeModels.title).filter(TreeModels.parent_node == des_data[2],
                                                                         TreeModels.grand_node == des_data[1],
                                                                         TreeModels.biz_id == __biz_info.biz_id).all()
                    model_list = [i[0] for i in __tree_topo]
                    for m in model_list:
                        for i in asset_set:
                            try:
                                session.add(GetInsertOrUpdateObj(TreeAssetModels,
                                                                 f"asset_id='{i}' and asset_type='{asset_type}' and module_name='{m}' and region_name='{des_data[2]}' and env_name='{des_data[1]}' and biz_id='{biz_id}'",
                                                                 asset_id=i, module_name=m,
                                                                 region_name=des_data[2], env_name=des_data[1],
                                                                 biz_id=biz_id, asset_type=asset_type))
                            except Exception as e:
                                print(e)
                    # session.add_all(
                    #     [TreeAssetModels(**{**filter_map, **{"asset_id": i, "module_name": m}}) for i in
                    #      need_add_asset_set
                    #      for m in model_list])
                    return dict(code=0, msg=f"绑定到{des_data[-1]}完成")
                except Exception as err:
                    return dict(code=-9, msg=f"绑定出错 {err}")

            elif len(des_data) == 4:
                try:
                    ### 当前目标拓扑上已经挂载的数据
                    __tree_asset_id = session.query(TreeAssetModels.id, TreeAssetModels.asset_id).filter_by(
                        **filter_map).all()
                    asset_exist_ids = set([i[1] for i in __tree_asset_id])
                    ## 正则能匹配到的(asset_set)有   而当前拓扑下没有 asset_exist_ids没有
                    need_add_asset_set = asset_set.difference(asset_exist_ids)

                    if len(need_add_asset_set) < 1: return dict(code=0, msg=f"当前没有可以绑定的资源")
                    session.add_all([TreeAssetModels(**{**filter_map, **{"asset_id": i}}) for i in need_add_asset_set])
                    # print(need_add_asset_set)
                    return dict(code=0, msg=f"绑定到{des_data[-1]}完成, 数量为{len(need_add_asset_set)}")
                except Exception as err:
                    return dict(code=-10, msg=f"绑定出错 {err}")

    return dict(code=-10, msg=f"绑定出错")


def del_relational_asset(data: dict) -> dict:
    rule_id = data.pop('id')

    res = get_dynamic_rules_asset(**{"id": rule_id})
    asset_list = res.get('data')
    asset_set = set([i.get('id') for i in asset_list])  ### 正则匹配数据的资产ID集合

    with DBContext('w', None, True) as session:
        session.query(TreeAssetModels).filter(
            TreeAssetModels.asset_id.in_(asset_set)).delete(synchronize_session=False)
    return dict(code=0, msg=f"删除关联关系 {len(asset_set)} 条")
