from sqlalchemy import Enum
from .asset import AssetServerModels, AssetMySQLModels, AssetRedisModels, AssetLBModels, AssetVPCModels, \
    AssetVSwitchModels, AssetEIPModels, SecurityGroupModels
from .tree import TreeModels, TreeAssetModels
from .tag import TagModels

asset_type_enum = Enum(
    'server',
    'process',
    'mysql',
    'redis',
    'lb',
    'vpc',
    'disk',
    'switch',
    'domain',
    'oss',
    'cdn',
    'eip'
)

operator_list = [
    '包含',
    '正则',
    '==',
    '!=',
    '开始',
    '结束'
]
operator_enum = Enum(
    *operator_list,
    name='operator_enum'
)

src_type_list = [
    'name',
    'cloud_name',
    'account_id',
    'region',
    'inner_ip',
    'state'
]
src_type_enum = Enum(
    *src_type_list,
    name='src_type_enum'
)
des_rule_type_enum = Enum(
    '业务',
    '标签'
)
des_rule_type_mapping = {
    '业务': TreeModels,
    '标签': TagModels
}
asset_mapping = {'server': AssetServerModels, 'mysql': AssetMySQLModels, 'redis': AssetRedisModels,
                 'lb': AssetLBModels, 'eip': AssetEIPModels, 'vpc': AssetVPCModels, 'vswitch': AssetVSwitchModels,
                 'security_group': SecurityGroupModels}
