# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/26
# @Description: 同步数据到jumpserver
import json
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from loguru import logger
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.client import AcsClient
from websdk2.api_set import api_set

if configs.can_import: configs.import_dict(**settings)

# 实例化client
client = AcsClient()


def get_users():
    try:
        response = client.do_action(**api_set.get_user_list)
        return response
    except Exception as err:
        logger.error(f'get users error: {err}')
    return []


if __name__ == '__main__':
    print(get_users())
