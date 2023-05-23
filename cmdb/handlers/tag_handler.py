# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Since: 2023/2/12 15:10
Description: 标签管理路由
"""

import json
import logging
from abc import ABC
from typing import *
from libs.base_handler import BaseHandler
from models.tag import TagModels, TagAssetModels
from models.asset import AssetServerModels, AssetMySQLModels, AssetRedisModels, AssetLBModels
from sqlalchemy import or_
from websdk2.db_context import DBContext
from websdk2.model_utils import queryset_to_list


class TagHandler(BaseHandler, ABC):
    def get(self):
        page_size = self.get_argument('page_size', default='10', strip=True)
        page_number = self.get_argument('page_number', default='1', strip=True)
        page_number = (int(page_number) - 1) * int(page_size)
        search_val = self.get_argument('search_val', default='', strip=True)

        with DBContext('r', None, None) as session:
            tag_info = session.query(TagModels).filter(or_(
                TagModels.tag_key.like(f'%{search_val}%'),
                TagModels.tag_value.like(f'%{search_val}%'),
            )).offset(int(page_number)).limit(int(page_size))
            tag_count: Optional[int] = session.query(TagModels).count()
            # 支持关联Tag的资产
            asset_type_list = ['server', 'mysql', 'redis', 'lb']
            # 先根据用户分页返回的数据取查询出来Tag关联信息 只查一次，返回到内存处理
            tag_ids: List[int] = [tag.id for tag in tag_info]
            tag_asset_info: List[TagAssetModels] = session.query(TagAssetModels).filter(
                TagAssetModels.tag_id.in_(tag_ids)).all()

            # 处理字典合并，过滤每个type的数量
            # type  List[Dict[str, Any]] = [{count: {server: 2, mysql: 0, redis: 0, lb: 0}, create_time: "2022-09-07 16:41:25",…},…]
            latest_data = list(
                map(
                    lambda tag_item: dict(
                        {
                            "count": {
                                asset_type: len(
                                    list(
                                        filter(
                                            lambda tag_asset_item: tag_asset_item["tag_id"] == tag_item["id"] and
                                                                   tag_asset_item["asset_type"] == asset_type,
                                            queryset_to_list(tag_asset_info),
                                        )
                                    )
                                )
                                for asset_type in asset_type_list
                            },
                        },
                        **tag_item
                    ),
                    queryset_to_list(tag_info),
                ),
            )
        return self.write({'code': 0, 'msg': '获取成功', 'count': tag_count, 'data': latest_data})

    def post(self):
        """批量创建Tag"""
        data = json.loads(self.request.body.decode("utf-8"))
        tags = data.get('tags', None)
        tag_detail = data.get('tag_detail', '')

        if not isinstance(tags, list):
            return self.write({"code": 1, "msg": "Tag类型错误"})

        # 处理 0表示前端标记删除
        tags = list(
            filter(
                lambda rule: rule["status"] == 1, tags
            )
        )
        if not tags:
            return self.write({"code": 1, "msg": "条件不能为空"})

        with DBContext('w', None, True) as session:
            for item in tags:
                tag_key = item['tag_key']
                tag_value = item['tag_value']
                is_exist_id: Union[TagModels, None] = session.query(TagModels).filter(
                    TagModels.tag_key == tag_key, TagModels.tag_value == tag_value
                ).first()
                if is_exist_id:
                    logging.error(f"{tag_key}:{tag_key} has existed.")
                else:
                    session.add(TagModels(tag_key=tag_key, tag_value=tag_value, tag_detail=tag_detail))
        return self.write({'code': 0, 'msg': '添加成功'})

    def patch(self):
        """绑定资源"""
        data = json.loads(self.request.body.decode("utf-8"))
        tag_id = data.get('tag_id')
        asset_type = data.get('asset_type', None)
        asset_ids = data.get('asset_ids', None)
        tag_key = data.get('tag_key', None)
        tag_value = data.get('tag_value', None)
        tag_detail = data.get('tag_detail', '')

        if not tag_key and not tag_value:
            return self.write({'code': 1, 'msg': '缺少标签键值'})

        if not asset_type and not asset_ids:
            return self.write({'code': 1, 'msg': '缺少类型和资产ID'})

        with DBContext('w', None, True) as session:
            session.add_all([
                TagAssetModels(tag_id=tag_id, asset_type=asset_type, asset_id=asset_id)
                for asset_id in asset_ids
            ])
            # 只是更新下备注，好像也没什么用..
            session.query(TagModels).filter(TagModels.id == tag_id).update({TagModels.tag_detail: tag_detail})

        return self.write({'code': 0, 'msg': '更新成功'})

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        tag_id = data.get('tag_id', None)
        if not tag_id:
            return self.write({'code': 1, 'msg': 'tag_id为空'})
        # 查询如果有资源就不让删除
        with DBContext('w', None, True) as session:
            is_exist_asset: Union[TagAssetModels, None] = session.query(TagAssetModels).filter(
                TagAssetModels.tag_id == tag_id).first()
            if is_exist_asset:
                return self.write({'code': 1, 'msg': '该标签存在资源关联，不允许删除'})
            session.query(TagModels).filter(
                TagModels.id == tag_id
            ).delete(synchronize_session=False)
        return self.write({'code': 0, 'msg': '删除成功'})


class TagAssetIOHandler(BaseHandler, ABC):
    def get(self):
        """主要用来绑定资源选择的时候，获取资产ID"""
        tag_id = self.get_argument('tag_id', default='', strip=True)
        asset_type = self.get_argument('asset_type', default='', strip=True)

        if not tag_id and not asset_type:
            return self.write({'code': 1, 'msg': 'tag_id/asset_type为空'})

        with DBContext('r', None, None) as session:
            asset_ids: List[tuple] = session.query(TagAssetModels.asset_id).filter(
                TagAssetModels.tag_id == tag_id, TagAssetModels.asset_type == asset_type
            ).group_by(TagAssetModels.asset_id).all()
            asset_ids: List[int] = [i[0] for i in asset_ids] if asset_ids else []

        return self.write({'code': 0, 'msg': '获取成功', 'data': asset_ids})


#  以下2个方法。暂时先放这里把
def get_tag_asset(db_session, tag_key: Optional[str], tag_value: Optional[str]) -> List[dict]:
    """
    获取TAG和资产的关系信息
    1。 如果有tag_key+tag_value  tag_id一定只有1条
    2。 如果用户根据tag_key大范围去查询，tag_id有多个
    ps:
        sqlalchemy.orm.session.Session  Typing对这个类型标注支持不友好，先不用了
    """
    if not tag_value:
        tag_ids: List[tuple] = db_session.query(TagModels.id).filter(
            TagModels.tag_key == tag_key
        ).all()
    else:
        tag_ids: List[tuple] = db_session.query(TagModels.id).filter(
            TagModels.tag_key == tag_key, TagModels.tag_value == tag_value
        ).all()
    tag_ids: List[int] = [i[0] for i in tag_ids] if tag_ids else []
    tag_asset_info: List[TagAssetModels] = db_session.query(TagAssetModels).filter(
        TagAssetModels.tag_id.in_(tag_ids)).all()
    return queryset_to_list(tag_asset_info)


def get_asset_detail(db_session, tag_key: Optional[str], tag_value: Optional[str] = None) -> Dict[str, List[dict]]:
    """
    获取详细的资产信息
    """
    # 获取TAG和资产关系，过滤对应类型的asset_id
    tag_asset_info: List[Dict[str, Any]] = get_tag_asset(db_session, tag_key, tag_value)
    # 定义返回
    res: Dict[str, List[dict]] = {}

    # 定义类型和模型的关系
    mapping = {'server': AssetServerModels, 'mysql': AssetMySQLModels, 'redis': AssetRedisModels, 'lb': AssetLBModels}

    # 查询
    for asset_type in mapping.keys():
        asset_ids = set([
            i['asset_id'] for i in tag_asset_info if i['asset_type'] == asset_type
        ])
        #  对应的model
        _the_model = mapping.get(asset_type)
        asset_info: List[_the_model] = db_session.query(_the_model).filter(_the_model.id.in_(asset_ids)).all()
        res[asset_type] = queryset_to_list(asset_info)
    return res


class TagAssetDetailHandler(BaseHandler, ABC):
    def get(self):
        tag_key = self.get_argument('tag_key', default='', strip=True)
        tag_value = self.get_argument('tag_value', default='', strip=True)

        if not tag_key:
            return self.write({'code': 1, 'msg': '缺少tag_key参数'})

        with DBContext('r', None, None) as session:
            data: Dict[str, List[dict]] = get_asset_detail(session, tag_key, tag_value)

        return self.write({'code': 0, 'msg': 'success', 'data': data})


tag_urls = [
    (r"/api/v2/cmdb/tag/", TagHandler, {"handle_name": "标签管理", "handle_status": "y"}),
    (r"/api/v2/cmdb/tag/asset_id/", TagAssetIOHandler, {"handle_name": "获取资产ID", "handle_status": "y"}),
    (r"/api/v2/cmdb/tag/asset_detail/", TagAssetDetailHandler, {"handle_name": "标签资产关系详细信息", "handle_status": "y"}),
]
