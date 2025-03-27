#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 操作Models公共方法
"""
import json
import datetime
import logging
from typing import *

import pymysql
from sqlalchemy.sql import or_
from sqlalchemy.orm.attributes import flag_modified
from websdk2.db_context import DBContext
from websdk2.model_utils import model_to_dict, insert_or_update
from websdk2.client import AcsClient
from websdk2.api_set import api_set
from websdk2.configs import configs

from settings import settings
from models.cloud import SyncLogModels, CloudSettingModels
from models.asset import AssetServerModels, AssetMySQLModels, AssetRedisModels, AssetLBModels, AssetVPCModels, \
    AssetVSwitchModels, AssetEIPModels, SecurityGroupModels, AssetImagesModels, AssetNatModels, AssetClusterModels, \
    AssetMongoModels
from models.event import CloudEventsModels
from models import asset_mapping

if configs.can_import: configs.import_dict(**settings)


def mark_expired(resource_type: Optional[str], account_id: Optional[str]):
    """
    根据时间标记过期的数据
    """
    # 定义类型和模型的关系
    # mapping = {'server': AssetServerModels, 'mysql': AssetMySQLModels, 'redis': AssetRedisModels, 'lb': AssetLBModels}
    if resource_type not in asset_mapping.keys():
        logging.error(f"标记过期，资源类型错误，类型={resource_type}")
        return
    with DBContext('w', None, True, **settings) as session:
        # 7天前
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        resource_model = asset_mapping.get(resource_type)
        # 过期
        session.query(resource_model).filter(
            resource_model.account_id == account_id, resource_model.update_time <= seven_days_ago
        ).update({resource_model.is_expired: True})
        
        
def mark_expired_by_sync(cloud_name: str, account_id: str, resource_type: str, instance_ids: list, region=None):
    """根据同步结果标记过期状态
    Args:
        cloud_name: 云服务商名称
        account_id: 账号ID
        resource_type: 资源类型
        instance_ids: 当前同步到的实例ID列表
        region: 区域    
    """
    if resource_type not in asset_mapping.keys():
        logging.error(f"标记过期，资源类型错误，类型={resource_type}")
        return

    try:
        with DBContext('w', None, True, **settings) as session:
            resource_model = asset_mapping.get(resource_type)
            
            # 基础过滤条件
            base_filter = [
                resource_model.cloud_name == cloud_name,
                resource_model.account_id == account_id,
                resource_model.is_expired == False,
                ~resource_model.instance_id.in_(instance_ids)
            ]
            # 如果指定了region，添加region过滤条件
            if region:
                base_filter.append(resource_model.region == region)
            
            # 将不在当前同步列表中的资源标记为未同步
            unsync_resources = session.query(resource_model).filter(*base_filter).all()
            
            for resource in unsync_resources:
                resource.state = '未同步'
                # 更新ext_info中的state字段
                if hasattr(resource, 'ext_info') and resource.ext_info:
                    if isinstance(resource.ext_info, dict):
                        resource.ext_info['state'] = '未同步'
                        flag_modified(resource, 'ext_info')
            
            # 将7天未同步的资源标记为过期
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            expire_filter = [
                resource_model.cloud_name == cloud_name,
                resource_model.account_id == account_id,
                resource_model.update_time <= seven_days_ago,
                resource_model.is_expired == False
            ]
            if region:
                expire_filter.append(resource_model.region == region)
            session.query(resource_model).filter(*expire_filter).update({resource_model.is_expired: True})

            session.commit()
    except Exception as e:
        logging.error(f"标记过期状态失败: {e}")


def get_cloud_config(cloud_name: Optional[str], account_id: Optional[str] = None) -> List[dict]:
    """
    获取云资产配置
    :return:
    cloud_name: 云厂商Name
    account_id: 一个厂商多个账号的情况，自动生成的ID
    """
    cloud_config_list: List[Dict[str, Any]] = []
    try:
        with DBContext('r', None, None, **settings) as db_session:
            if not account_id:
                qcloud_info: List[CloudSettingModels] = db_session.query(CloudSettingModels).filter(
                    CloudSettingModels.is_enable == True, CloudSettingModels.cloud_name == cloud_name
                ).all()
            else:
                qcloud_info: List[CloudSettingModels] = db_session.query(CloudSettingModels).filter(
                    CloudSettingModels.is_enable == True, CloudSettingModels.cloud_name == cloud_name,
                    CloudSettingModels.account_id == account_id
                ).all()
            for data in qcloud_info:
                data_dict = model_to_dict(data)
                data_dict['create_time'] = str(data_dict['create_time'])
                data_dict['update_time'] = str(data_dict['update_time'])
                cloud_config_list.append(data_dict)
    except Exception as err:
        logging.error(f'获取access_key配置失败， 云厂商={cloud_name}, 账号={account_id},错误={err}')
        return []

    if not cloud_config_list:
        logging.error(f"没有发现已开启自动发现的配置信息，云厂商={cloud_name}, 账号={account_id}")
        return []

    return cloud_config_list


def get_all_cloud_interval() -> List[dict]:
    """
    获取云账号的间隔时间
    """
    with DBContext('r', None, None, **settings) as session:
        _info: List[tuple] = session.query(
            CloudSettingModels.cloud_name, CloudSettingModels.account_id, CloudSettingModels.interval
        ).filter(CloudSettingModels.is_enable == True).all()

        return [
            {
                "cloud_name": i[0],
                "account_id": i[1],
                "interval": i[2]
            } for i in _info
        ]


def sync_log_task(data: Dict[str, str]):
    """
    资产同步日志入库
    :param data:
    :return:
    """
    # 示例
    example_data = {
        "name": "", "cloud_name": "", "sync_type": "", "sync_region": "", "sync_state": "", "account_id": "",
        "sync_consum": "", "loginfo": ""
    }
    if data.keys() != example_data.keys():
        logging.error(f"记录Log参数错误,元数据是={data}")
        return

    with DBContext('w', None, None, **settings) as db_session:
        db_session.add(SyncLogModels(**data))
        db_session.commit()


def get_all_agent_info() -> dict:
    agent_info = {}
    try:
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_agent_list)
        if resp.status_code != 200:
            logging.error(f"获取agent列表失败，状态码={resp.status_code}")
            return {}
        agent_info = resp.json()
    except Exception as err:
        logging.error(f"获取失败，{err}")

    return agent_info


def server_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """

    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-server task写入数据库完成"
    # logging.error(f"{cloud_name}, {account_id}")
    try:
        all_agent_info = get_all_agent_info()
        with DBContext('w', None, True, **settings) as db_session:
            for __info in rows:
                instance_id = __info['instance_id']
                region = __info.get('region')
                inner_ip = __info.get('inner_ip')
                filter_map = dict(instance_id=instance_id)
                exist_id = db_session.query(AssetServerModels.id, AssetServerModels.agent_id).filter_by(**filter_map).first()
                agent_id = "0"

                if exist_id:
                    # 更新时更新agent_info
                    agent_info = all_agent_info.get(exist_id[1], {})
                    try:
                        update_data = {
                            AssetServerModels.cloud_name: cloud_name,
                            AssetServerModels.account_id: account_id,
                            AssetServerModels.name: __info.get('name'),
                            AssetServerModels.region: region,
                            AssetServerModels.zone: __info.get('zone'),
                            AssetServerModels.state: __info.get('state'),
                            # AssetServerModels.agent_id: agent_id,
                            # AssetServerModels.agent_info: agent_info,
                            AssetServerModels.outer_ip: __info.get('outer_ip'),
                            AssetServerModels.inner_ip: inner_ip,
                            AssetServerModels.vpc_id: __info.get('vpc_id'),
                            AssetServerModels.is_expired: False,  # 改为正常状态
                            AssetServerModels.ext_info: __info  # 存json
                        }
                        if agent_info:
                            update_data[AssetServerModels.agent_info] = agent_info
                        db_session.query(AssetServerModels).filter_by(**filter_map).update(update_data)
                    except Exception as err:
                        logging.error(err)
                else:
                    try:
                        db_session.add(AssetServerModels(
                            cloud_name=cloud_name, account_id=account_id, instance_id=instance_id,
                            state=__info.get('state'), name=__info.get('name'),
                            region=region, zone=__info.get('zone'), vpc_id=__info.get('vpc_id'),
                            inner_ip=inner_ip, outer_ip=__info.get('outer_ip'), agent_id=agent_id,
                            ext_info=__info, is_expired=False  # 新机器标记正常
                        ))
                    except pymysql.err.IntegrityError as err:
                        db_session.query(AssetServerModels).filter(
                            AssetServerModels.account_id == account_id,
                            AssetServerModels.region == region,
                            AssetServerModels.inner_ip == inner_ip
                        ).delete(synchronize_session=False)
                        logging.error(err)

            db_session.commit()
    except Exception as err:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-server task写入数据库失败:{err}"
        logging.error(ret_msg)
    return ret_state, ret_msg


def server_task_batch(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """批量更新服务器信息
    Args:
        cloud_name: 云服务商名称
        account_id: 账号ID
        rows: 服务器信息列表
    Returns:
        Tuple[bool, str]: (是否成功, 消息)
    """
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-server task写入数据库完成"
    
    try:
        all_agent_info = get_all_agent_info()
        with DBContext('w', None, True, **settings) as db_session:
            # 获取所有实例ID
            instance_ids = [row['instance_id'] for row in rows]
            
            # 批量查询现有记录
            existing_records = {
                record.instance_id: record 
                for record in db_session.query(AssetServerModels).filter(
                    AssetServerModels.instance_id.in_(instance_ids)
                ).all()
            }
            
            # 准备批量更新和插入的数据
            to_update = []
            to_insert = []
            
            for info in rows:
                instance_id = info['instance_id']
                region = info.get('region')
                inner_ip = info.get('inner_ip')
                
                if instance_id in existing_records:
                    # 准备更新数据
                    record = existing_records[instance_id]
                    agent_info = all_agent_info.get(record.agent_id, {})
                    
                    update_data = {
                        'id': record.id,  # 需要包含主键
                        'cloud_name': cloud_name,
                        'account_id': account_id,
                        'name': info.get('name'),
                        'region': region,
                        'zone': info.get('zone'),
                        'state': info.get('state'),
                        'outer_ip': info.get('outer_ip'),
                        'inner_ip': inner_ip,
                        'vpc_id': info.get('vpc_id'),
                        'is_expired': False,
                        'ext_info': info
                    }
                    if agent_info:
                        update_data['agent_info'] = agent_info
                    
                    to_update.append(update_data)
                else:
                    # 准备插入数据
                    to_insert.append({
                        'cloud_name': cloud_name,
                        'account_id': account_id,
                        'instance_id': instance_id,
                        'state': info.get('state'),
                        'name': info.get('name'),
                        'region': region,
                        'zone': info.get('zone'),
                        'vpc_id': info.get('vpc_id'),
                        'inner_ip': inner_ip,
                        'outer_ip': info.get('outer_ip'),
                        'agent_id': "0",
                        'ext_info': info,
                        'is_expired': False
                    })
            
            # 批量更新
            if to_update:
                try:
                    db_session.bulk_update_mappings(AssetServerModels, to_update)
                except Exception as err:
                    logging.error(f"批量更新失败: {err}")
            
            # 批量插入
            if to_insert:
                try:
                    db_session.bulk_insert_mappings(AssetServerModels, to_insert)
                except pymysql.err.IntegrityError as err:
                    logging.error(f"批量插入失败: {err}")
            
            db_session.commit()
            
    except Exception as err:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-server task写入数据库失败:{err}"
        logging.error(ret_msg)
    
    return ret_state, ret_msg


def mysql_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
    mysql资产写入数据库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-mysql task写入数据库完成"
    try:
        with DBContext('w', None, True, **settings) as db_session:
            for __info in rows:
                instance_id = __info['instance_id']
                exist_id = db_session.query(AssetMySQLModels.id).filter(
                    AssetMySQLModels.instance_id == instance_id).first()
                if exist_id:
                    try:
                        db_session.query(AssetMySQLModels).filter(
                            AssetMySQLModels.instance_id == instance_id
                        ).update({
                            AssetMySQLModels.cloud_name: cloud_name,
                            AssetMySQLModels.account_id: account_id,
                            AssetMySQLModels.region: __info.get('region'),
                            AssetMySQLModels.zone: __info.get('zone'),
                            AssetMySQLModels.is_expired: False,
                            AssetMySQLModels.ext_info: __info,
                            AssetMySQLModels.name: __info.get('name'),
                            AssetMySQLModels.state: __info.get('state'),
                            AssetMySQLModels.db_class: __info.get('db_class'),
                            AssetMySQLModels.db_engine: __info.get('db_engine'),
                            AssetMySQLModels.db_version: __info.get('db_version'),
                            AssetMySQLModels.db_address: __info.get('db_address')
                        })
                    except Exception as err:
                        logging.error(f"mysql sync task err {err}")
                else:
                    db_session.add(AssetMySQLModels(
                        cloud_name=cloud_name, account_id=account_id, instance_id=instance_id,
                        region=__info.get('region'), zone=__info.get('zone'), is_expired=False, ext_info=__info,
                        # up base, down self models data
                        name=__info.get('name'), state=__info.get('state'),
                        db_class=__info.get('db_class'), db_engine=__info.get('db_engine'),
                        db_version=__info.get('db_version'), db_address=__info.get('db_address')
                    ))
            db_session.commit()
    except Exception as err:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-mysql task写入数据库失败:{err}"
        logging.error(ret_msg)
    return ret_state, ret_msg


def redis_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-redis task写入数据库完成"
    try:
        with DBContext('w', None, True, **settings) as db_session:
            for __info in rows:
                instance_id = __info['instance_id']
                exist_id = db_session.query(AssetRedisModels.id).filter(
                    AssetRedisModels.instance_id == instance_id
                ).first()
                if exist_id:
                    db_session.query(AssetRedisModels).filter(
                        AssetRedisModels.instance_id == instance_id
                    ).update({
                        AssetRedisModels.cloud_name: cloud_name,
                        AssetRedisModels.account_id: account_id,
                        AssetRedisModels.region: __info.get('region'),
                        AssetRedisModels.zone: __info.get('zone'),
                        AssetRedisModels.is_expired: False,
                        AssetRedisModels.ext_info: __info,
                        AssetRedisModels.name: __info.get('name'),
                        AssetRedisModels.state: __info.get('state'),
                        AssetRedisModels.instance_class: __info.get('instance_class'),
                        AssetRedisModels.instance_arch: __info.get('instance_arch'),
                        AssetRedisModels.instance_type: __info.get('instance_type'),
                        AssetRedisModels.instance_version: __info.get('instance_version'),
                        AssetRedisModels.instance_address: __info.get('instance_address')
                    })
                else:
                    db_session.add(AssetRedisModels(
                        cloud_name=cloud_name, account_id=account_id, instance_id=instance_id,
                        region=__info.get('region'), zone=__info.get('zone'), is_expired=False, ext_info=__info,
                        # up base, down self models data
                        name=__info.get('name'), state=__info.get('state'),
                        instance_class=__info.get('instance_class'), instance_arch=__info.get('instance_arch'),
                        instance_type=__info.get('instance_type'), instance_version=__info.get('instance_version'),
                        instance_address=__info.get('instance_address')
                    ))
            db_session.commit()
    except Exception as err:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-redis task写入数据库失败:{err}"
    return ret_state, ret_msg


def lb_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
    LoadBalancer资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-lb task写入数据库完成"
    try:
        with DBContext("w", None, True, **settings) as db_session:
            for row in rows:
                instance_id = row.get("instance_id")
                exist_id = db_session.query(AssetLBModels.id).filter(
                    AssetLBModels.account_id == account_id, AssetLBModels.instance_id == instance_id
                ).first()
                if not exist_id:
                    db_session.add(AssetLBModels(
                        name=row.get("name"), cloud_name=cloud_name, type=row.get("type"), account_id=account_id,
                        instance_id=row.get("instance_id"), region=row.get("region"), zone=row.get("zone"),
                        endpoint_type=row.get("endpoint_type"), lb_vip=row.get("lb_vip"), dns_name=row.get("dns_name"),
                        is_expired=False, state=row.get("status"), ext_info=row.get("ext_info")
                    ))
                else:
                    db_session.query(AssetLBModels).filter(
                        AssetLBModels.account_id == account_id,
                        AssetLBModels.instance_id == instance_id
                    ).update({
                        AssetLBModels.type: row.get("type"),
                        AssetLBModels.region: row.get("region"),
                        AssetLBModels.zone: row.get("zone"),
                        AssetLBModels.lb_vip: row.get("lb_vip"),
                        AssetLBModels.state: row.get("status"),
                        AssetLBModels.is_expired: False,
                        AssetLBModels.instance_id: row.get("instance_id"),
                        AssetLBModels.endpoint_type: row.get("endpoint_type"),
                        AssetLBModels.dns_name: row.get("dns_name"),
                        AssetLBModels.ext_info: row.get("ext_info")
                    })
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-lb task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def vpc_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     虚拟局域网资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-vpc task写入数据库完成"
    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetVPCModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 vpc_name=row.get('vpc_name'),
                                                 region=row.get('region'),
                                                 cidr_block_v4=row.get('cidr_block_v4'),
                                                 cidr_block_v6=row.get('cidr_block_v6'),
                                                 vpc_router=row.get('vpc_router'),
                                                 vpc_switch=row.get('vpc_switch'),
                                                 is_default=row.get('is_default', False)
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-vpc task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def vswitch_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     虚拟交换机资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-vswitch task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetVSwitchModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 vpc_id=row.get('vpc_id'),
                                                 vpc_name=row.get('vpc_name', ''),
                                                 region=row.get('region'), zone=row.get('zone'),
                                                 name=row.get('name'),
                                                 address_count=row.get('address_count'),
                                                 cidr_block_v4=row.get('cidr_block_v4'),
                                                 cidr_block_v6=row.get('cidr_block_v6'),
                                                 route_id=row.get('route_id'),
                                                 is_default=row.get('is_default', False)
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-vswitch  task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def eip_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     弹性IP资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-eip task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetEIPModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 name=row.get('name'),
                                                 address=row.get('address'),
                                                 region=row.get('region'),
                                                 binding_instance_id=row.get('binding_instance_id'),
                                                 binding_instance_type=row.get('binding_instance_type'),
                                                 state=row.get('state'),
                                                 bandwidth=row.get('bandwidth'),
                                                 internet_charge_type=row.get('internet_charge_type'),
                                                 charge_type=row.get('charge_type', False)
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-eip  task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def security_group_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     安全组资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-安全组task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(SecurityGroupModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 region=row.get('region'),
                                                 vpc_id=row.get('vpc_id'),
                                                 security_group_name=row.get('security_group_name'),
                                                 security_info=row.get('security_info'),
                                                 ref_info=row.get('ref_info'),
                                                 description=row.get('description'),
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-安全组task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def image_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     系统镜像资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-系统镜像task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetImagesModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 region=row.get('region'),
                                                 name=row.get('name'),
                                                 image_type=row.get('image_type'),
                                                 image_size=row.get('image_size'),
                                                 os_platform=row.get('os_platform'),
                                                 os_name=row.get('os_name'),
                                                 state=row.get('state'),
                                                 arch=row.get('arch'),
                                                 description=row.get('description')
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-系统镜像task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def cloud_event_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     维护事件入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-维护事件task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                event_id = row.get("event_id")
                try:
                    session.add(insert_or_update(CloudEventsModels, f"event_id='{event_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 event_id=event_id,
                                                 region=row.get('region'),
                                                 event_service=row.get('event_service'),
                                                 event_type=row.get('event_type'),
                                                 event_status=row.get('event_status'),
                                                 event_instance_id=row.get('event_instance_id'),
                                                 event_instance_name=row.get('event_instance_name'),
                                                 event_start_time=row.get('event_start_time'),
                                                 event_end_time=row.get('event_end_time'),
                                                 event_detail=row.get('event_detail')
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-维护事件task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def nat_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     NAT网关资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-NAT网关task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetNatModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 region=row.get('region'),
                                                 name=row.get('name'),
                                                 network_type=row.get('network_type'),
                                                 network_interface_id=row.get('network_interface_id'),
                                                 charge_type=row.get('charge_type'),
                                                 outer_ip=row.get('outer_ip'),
                                                 zone=row.get('zone'),
                                                 description=row.get('description'),
                                                 spec=row.get('spec'),
                                                 subnet_id=row.get('subnet_id'),
                                                 project_name=row.get('project_name'),
                                                 vpc_id=row.get('vpc_id'),
                                                 state=row.get('state'),
                                                 update_time=datetime.datetime.now(),
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-NAT网关task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def cluster_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     集群资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-集群task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetClusterModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 region=row.get('region'),
                                                 name=row.get('name'),
                                                 inner_ip=row.get('inner_ip'),
                                                 outer_ip=row.get('outer_ip'),
                                                 zone=row.get('zone'),
                                                 description=row.get('description'),
                                                 version=row.get('version'),
                                                 vpc_id=row.get('vpc_id'),
                                                 total_node=row.get('total_node'),
                                                 total_running_node=row.get('total_running_node'),
                                                 tags=row.get('tags'),
                                                 state=row.get('state'),
                                                 update_time=datetime.datetime.now(),
                                                 ext_info=row.get('ext_info'),
                                                 cluster_type=row.get('cluster_type'),
                                                 ))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-集群task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg


def mongodb_task(cloud_name: str, account_id: str, rows: list) -> Tuple[bool, str]:
    """
     MongoDB资源入库
    :param cloud_name:
    :param account_id:
    :param rows:
    :return:
    """
    # 定义返回
    ret_state, ret_msg = True, f"{cloud_name}-{account_id}-MongoDB task写入数据库完成"

    try:
        with DBContext("w", None, True, **settings) as session:
            for row in rows:
                if not row: continue
                instance_id = row.get("instance_id")
                try:
                    session.add(insert_or_update(AssetMongoModels, f"instance_id='{instance_id}'",
                                                 cloud_name=cloud_name, account_id=account_id,
                                                 instance_id=instance_id,
                                                 region=row.get('region'),
                                                 name=row.get('name'),
                                                 db_class=row.get('db_class'),
                                                 db_version=row.get('db_version'),
                                                 db_address=row.get('db_address'),
                                                 subnet_id=row.get('subnet_id'),
                                                 vpc_id=row.get('vpc_id'),
                                                 project_name=row.get('project_name'),
                                                 state=row.get('state'),
                                                 tags=row.get('tags'),
                                                 zone=row.get('zone'),
                                                 update_time=datetime.datetime.now(),
                                                 storage_type=row.get('storage_type')))
                except Exception as err:
                    logging.error(err)
    except Exception as error:
        ret_state, ret_msg = False, f"{cloud_name}-{account_id}-MongoDB task写入数据库失败,错误行:{row},详细信息:{error}"
    return ret_state, ret_msg



if __name__ == '__main__':
    pass
