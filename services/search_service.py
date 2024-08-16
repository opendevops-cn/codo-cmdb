from typing import List, Dict, Any
from collections import namedtuple

from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from models.business import BizModels
from models import AssetServerModels, AssetMySQLModels, AssetRedisModels, AssetLBModels, TreeAssetModels
from models.domain import DomainRecords
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(BizModels)


def _get_server_value(value: str = None):
    if not value:
        return True
    return or_(
        AssetServerModels.name.like(f'%{value}%'),
        AssetServerModels.inner_ip.like(f'%{value}%'),
        AssetServerModels.outer_ip.like(f'%{value}%'),
    )


def _get_mysql_value(value: str = None):
    if not value:
        return True
    return or_(
        AssetMySQLModels.name.like(f'%{value}%'),
        AssetMySQLModels.db_address.like(f'%{value}%'),
        AssetMySQLModels.ext_info.like(f'%{value}%'),
    )


def _get_redis_value(value: str = None):
    if not value:
        return True
    return or_(
        AssetRedisModels.name.like(f'%{value}%'),
        AssetRedisModels.instance_address.like(f'%{value}%'),
        AssetRedisModels.ext_info.like(f'%{value}%'),
    )


def _get_lb_value(value: str = None):
    if not value:
        return True
    return or_(
        AssetLBModels.name.like(f'%{value}%'),
        AssetLBModels.dns_name.like(f'%{value}%'),
        AssetLBModels.lb_vip.like(f'%{value}%'),
        AssetLBModels.ext_info.like(f'%{value}%'),
    )


def _get_dns_value(value: str = None):
    if not value:
        return True
    return or_(
        DomainRecords.domain_value.like(f'%{value}%'),
        DomainRecords.domain_rr.like(f'%{value}%'),
        DomainRecords.remark.like(f'%{value}%')
    )


def get_asset_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    if not value:
        return dict(code=-1, msg='当前方法必须传入查询参数')

    page_size = 10  # 固定最多查询
    params['page_size'] = page_size

    with DBContext('r') as session:
        server_data = paginate(session.query(AssetServerModels).filter(_get_server_value(value)), **params)
        mysql_data = paginate(session.query(AssetMySQLModels).filter(_get_mysql_value(value)), **params)
        redis_data = paginate(session.query(AssetRedisModels).filter(_get_redis_value(value)), **params)
        lb_data = paginate(session.query(AssetLBModels).filter(_get_lb_value(value)), **params)
        dns_data = paginate(session.query(DomainRecords).filter(_get_dns_value(value)), **params)
        tree_asset_data = get_tree_asset_data(session, value, params)
    return dict(msg='获取成功', code=0, server_data=server_data.items, mysql_data=mysql_data.items,
                redis_data=redis_data.items, lb_data=lb_data.items, dns_data=dns_data.items,
                tree_asset_data=tree_asset_data)


def get_tree_asset_data(session, value: str = None, params: dict = None) -> List[Dict[str, Any]]:
    TreeAsset = namedtuple('TreeAsset', ['biz_id', 'biz_en_name', 'biz_cn_name', 'env_name', 'region_name',
                                         'module_name', 'inner_ip', 'is_enable'])
    params.update(items_not_to_list=True)
    page = paginate(session.query(TreeAssetModels.biz_id, BizModels.biz_en_name, BizModels.biz_cn_name,
                                  TreeAssetModels.env_name, TreeAssetModels.region_name, TreeAssetModels.module_name,
                                  AssetServerModels.inner_ip, TreeAssetModels.is_enable).
                    outerjoin(BizModels, BizModels.biz_id == TreeAssetModels.biz_id).
                    outerjoin(AssetServerModels, AssetServerModels.id == TreeAssetModels.asset_id).
                    filter(TreeAssetModels.asset_type == "server", _get_server_value(value)), **params)

    tree_asset_data = [TreeAsset(*item)._asdict() for item in page.items]
    return tree_asset_data

