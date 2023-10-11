#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/7/27 10:19
# @Author  : harilou
# @Describe: 处理回调结果数据


import logging
from typing import *
import traceback
from websdk2.model_utils import insert_or_update
from libs.qcloud import DEFAULT_CLOUD_NAME
from libs.qcloud.qcloud_cvm import get_run_type
from websdk2.db_context import DBContextV2 as DBContext
from models.cloud_region import CloudRegionModels, CloudRegionAssetModels
from models.asset import AssetServerModels
from models.tag import TagAssetModels, TagModels


class CloudCallback(object):

    def __init__(self):
        pass

    @staticmethod
    def save_asset(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
        """保存资源信息"""
        # 定义返回
        ret_state, ret_msg = True, None
        existed_list = list()
        try:
            with DBContext('w', None, True) as db_session:
                for __info in rows:
                    instance_id = __info['instance_id']
                    try:
                        db_session.add(insert_or_update(AssetServerModels, f"instance_id='{instance_id}'", **__info))
                    except Exception as err:
                        logging.error(err)
        except Exception as err:
            ret_state, ret_msg = False, f"{cloud_name}-{account_id}-server task写入数据库失败:{err}"
            logging.error(ret_msg)
        if existed_list:
            ret_state, ret_msg = False, f"instance_id 已存在:{','.join(existed_list)}"
        return ret_state, ret_msg

    @staticmethod
    def save_cloud_region(cloud_region_id, asset_type, asset_list):
        """保存云区域关联信息"""
        ret_state, ret_msg = True, "关联云区域完成"
        with DBContext('w', None, True) as session:
            try:
                __cr_info = session.query(CloudRegionModels).filter(
                    CloudRegionModels.cloud_region_id == cloud_region_id).first()
                if not __cr_info:
                    ret_state, ret_msg = False, "云区域ID不存在"
                    return ret_state, ret_msg
                region_id = __cr_info.id
                for asset_id in asset_list:
                    cloud_region_data = {
                        "asset_id": asset_id,
                        "region_id": region_id,
                        "cloud_region_id": cloud_region_id,
                        "asset_type": asset_type
                    }
                    obj = session.query(CloudRegionAssetModels.id).filter_by(**cloud_region_data).first()
                    if not obj:
                        session.add(CloudRegionAssetModels(**cloud_region_data))
                    else:
                        logging.warning("云区域无需重复绑定")
                session.commit()
            except Exception as err:
                logging.error(traceback.format_exc())
                ret_state, ret_msg = False, f"关联云区域写入数据库失败:{err}"
        return ret_state, ret_msg

    @staticmethod
    def save_tags(asset_type, asset_list, tags):
        """保存标签信息"""
        ret_state, ret_msg = True, "关联标签完成"
        with DBContext('w', None, True) as session:
            try:
                for _key, _val in tags.items():

                    tag_obj = session.query(TagModels).filter(TagModels.tag_key == _key,
                                                              TagModels.tag_value == _val).first()
                    if not tag_obj:
                        # 如果标签不存在则创建
                        session.add(TagModels(tag_key=_key, tag_value=_val))
                        logging.warning(f"{_key}:{_val} 标签不存在,进行创建")
                        tag_obj = session.query(TagModels).filter(TagModels.tag_key == _key,
                                                                  TagModels.tag_value == _val).first()

                    session.add_all([
                        TagAssetModels(tag_id=tag_obj.id, asset_type=asset_type, asset_id=asset_id)
                        for asset_id in asset_list
                    ])
                session.commit()
            except Exception as err:
                logging.error(traceback.format_exc())
                ret_state, ret_msg = False, f"关联标签写入数据库失败:{err}"
        return ret_state, ret_msg

    @staticmethod
    def get_asset_server_id(ins_ids):
        """获取资产ID"""
        with DBContext('w', None, True) as session:
            asset_lists = session.query(AssetServerModels).filter(AssetServerModels.instance_id.in_(ins_ids)).all()
            return [i.id for i in asset_lists]

    @staticmethod
    def update_order():
        """更新订单状态"""

        return

    def tx_vm(self, data):
        rows_list, ins_ids = list(), list()
        account_id = data["account_id"]
        cloud_region_id = data["cloud_region_id"]
        region = data["region"]
        asset_type = data["res_type"]
        agent_id = data["cloud_region_id"]
        tags = None
        public_ip = None
        for resources in data["data"]["resources"]:
            if resources["type"] == "tencentcloud_eip":
                public_ip = resources["instances"][0]["attributes"]["public_ip"]
            if resources["type"] != "tencentcloud_instance":
                continue
            for _item in resources["instances"]:
                item = _item["attributes"]
                _public_ip = item["public_ip"] if item["public_ip"] else public_ip
                instance_id = item["id"]
                private_ip = item["private_ip"]
                rows_list.append(dict(
                    cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id, instance_id=instance_id,
                    state=get_run_type(item["instance_status"]), name=item["instance_name"],
                    region=region, zone=item["availability_zone"], outer_biz_addr=_public_ip,
                    inner_ip=private_ip, outer_ip=item["public_ip"], agent_id=agent_id, ext_info=item,
                    is_expired=False  # 新机器标记正常
                ))
                ins_ids.append(instance_id)
                tags = item["tags"]

        ret_state, ret_msg = self.save_asset(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id, rows=rows_list)
        if not ret_state:
            return dict(msg=ret_msg, code=-1)

        asset_list = self.get_asset_server_id(ins_ids)

        ret_state, ret_msg = self.save_cloud_region(cloud_region_id=cloud_region_id, asset_type=asset_type,
                                                    asset_list=asset_list)
        if not ret_state:
            return dict(msg=ret_msg, code=-1)

        if tags:
            ret_state, ret_msg = self.save_tags(asset_type=asset_type, asset_list=asset_list, tags=tags)
            if not ret_state:
                return dict(msg=ret_msg, code=-1)
        return dict(msg=f'完成', code=0)

    def cds_vm(self, data):
        pass

    def save(self, data):
        vendor = data["csp"]
        if vendor == "tencent":
            return self.tx_vm(data)
        elif vendor == "cds":
            return self.cds_vm(data)
        return dict(msg=f'不支持该云厂商:{vendor}', code=-1)
