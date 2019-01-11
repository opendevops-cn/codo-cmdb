#!/usr/bin/env python
#encoding:utf-8

def get_object(model, **kwargs):
    """
    use this function for query
    使用改封装函数查询数据库
    """
    for value in kwargs.values():
        if not value:
            return None

    the_object = model.objects.filter(**kwargs)
    if len(the_object) == 1:
        the_object = the_object[0]
    else:
        the_object = None
    return the_object


def get_asset_info(asset):
    """
    获取资产的相关管理账号端口等信息
    """
    info = {}
    if asset.username:
        info['username'] = asset.username
        info['password'] = asset.password
    elif asset.admin_user:
        info['username'] = asset.admin_user.username
        info['password'] = asset.admin_user.password
        if bool(asset.admin_user.private_key):
            info['ssh_key'] = asset.admin_user.private_key
    else:
        return info
    info['hostname'] = asset.hostname
    info['ip'] =  asset.ip
    try:
        info['port'] = int(asset.port)
    except TypeError:
        info['port'] = 22
    return info