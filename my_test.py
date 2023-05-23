import datetime
import logging
import consul
import requests
from settings import settings
from models.tree import TreeAssetModels
from models import asset_mapping
from websdk2.consts import const
from websdk2.web_logs import ins_log
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from websdk2.client import AcsClient
from libs.consul_registry import ConsulOpt
from models.asset import AssetServerModels

if configs.can_import: configs.import_dict(**settings)


def get_items_ip(db_address, port) -> tuple:
    addr_list = db_address['items']
    inner_ip, port = '', port
    for addr in addr_list:
        if addr.get('type') == 'private':
            return addr.get('ip'), addr.get('port')
        inner_ip, port = addr.get('ip'), addr.get('port')

    return inner_ip, port


def get_registry_mysql_info():
    asset_type = 'mysql'
    __model = asset_mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(TreeAssetModels, __model.instance_id, __model.name,
                               __model.db_address).outerjoin(__model, __model.id == TreeAssetModels.asset_id).filter(
            TreeAssetModels.asset_type == asset_type).all()

    for i in __info:
        data = model_to_dict(i[0])
        biz_id = data['biz_id']
        if not i[3]:
            continue
        inner_ip, port = get_items_ip(i[3], 3306)
        # print(i[2], inner_ip)
        tags = [biz_id]
        tags = [str(t) for t in range(50)]
        node_meta = dict(biz_id=biz_id, env_name=data['env_name'], region_name=data['region_name'],
                         module_name=data['module_name'])
        server_name = f"{asset_type}-exporter1"
        register_data = (server_name, f"{server_name}-{biz_id}-{inner_ip}-{port}", inner_ip, port, tags, node_meta)
        yield register_data


# def sync_agent_status():
#     def index():
#         client = AcsClient()
#         get_agent_list = dict(method='GET', url=f'/api/agent/v1/codo/agent_list',
#                               description='获取Agent List')
#         res = client.do_action_v2(**get_agent_list)
#         if res.status_code != 200: return
#         data = res.json()
#         agent_list = data.get('list')
#         with DBContext('w', None, True) as session:
#             __info = session.query(AssetServerModels.id, AssetServerModels.agent_id,
#                                    AssetServerModels.agent_status).all()
#
#         all_info = []
#         for asset_id, agent_id, agent_status, in __info:
#             if agent_status == '1' and agent_id not in agent_list:  # 如果状态在线  但是agent找不到
#                 print(f'{agent_id}改为离线')
#                 all_info.append(dict(id=asset_id, agent_status='2'))
#             if agent_status == '2' and agent_id in agent_list:  # 如果状态离线  但是agent存在
#                 print(f'{agent_id}改为在线')
#                 all_info.append(dict(id=asset_id, agent_status='1'))
#             if not agent_status and agent_id in agent_list:
#                 print(f'{agent_id}改为在线')
#                 all_info.append(dict(id=asset_id, agent_status='1'))
#         session.bulk_update_mappings(AssetServerModels, all_info)
#
#     index()


if __name__ == '__main__':
    c = ConsulOpt()
    sync_agent_status()
    # for s in get_registry_mysql_info():
    #     print(s)
    #     c.register_service(*s)
