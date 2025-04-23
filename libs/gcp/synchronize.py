#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/11/22 11:02
Desc    : 谷歌云资产同步入口
"""
import tempfile
import traceback
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import *

from websdk2.configs import configs
from websdk2.tools import RedisLock

from libs import deco
from libs.gcp import mapping, DEFAULT_CLOUD_NAME
from libs.mycrypt import mc
from models.models_utils import sync_log_task, get_cloud_config


def sync(data: Dict[str, Any]) -> None:
    """
    谷歌云统一资产入库
    """
    obj, cloud_type, account_id = data.get("obj"), data.get("type"), data.get("account_id")

    cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
    if not cloud_configs:
        return

    for conf in cloud_configs:
        sync_regions(conf, obj, cloud_type)


def sync_regions(conf: Dict[str, str], obj: Callable, cloud_type: str) -> None:
    region = ""
    logging.info(f"同步开始, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.")
    start_time = time.time()
    account_file = mc.my_decrypt(conf["account_file"])
    project_id = conf["project_id"]
    account_id = conf["account_id"]
    sync_state = "failed"
    msg = ""


    account_path = f"/tmp/{project_id}_account_file.json"
    with open(account_path, "w", encoding="utf-8") as file:
        file.write(account_file)  # 写入字符串
    # 使用 with 自动清理临时文件
    try:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_file:
            tmp_file.write(account_file)
            tmp_file.flush()
            account_path = tmp_file.name
        is_success, msg = obj(
            project_id=project_id,
            account_path=account_path,
            account_id=account_id,
            region=region
        ).sync_cmdb()

        sync_state = "success" if is_success else "failed"

    except Exception as e:
        msg = f"同步异常: {str(e)}"
        logging.exception(f"同步异常: {e}")
    finally:
        # 确保文件被删除
        if os.path.exists(account_path):
            os.remove(account_path)

    end_time = time.time()

    sync_consum = "%.2f" % (end_time - start_time)

    sync_log_task(
        dict(
            name=conf["name"],
            cloud_name=DEFAULT_CLOUD_NAME,
            sync_type=cloud_type,
            account_id=account_id,
            sync_region=region,
            sync_state=sync_state,
            sync_consum=sync_consum,
            loginfo=str(msg),
        )
    )

    logging.info(f"同步结束, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.")


def get_gcp_sync_config() -> bool:
    """获取GCP同步配置

    优先从配置文件获取，其次从环境变量获取
    默认为 False
    """

    def parse_bool_value(value: Optional[str]) -> bool:
        if not value:
            return False
        return value.lower() in ("yes", "true", "1", "on")

    # 依次检查配置来源
    config_value = configs.get("gcp_sync", "")
    env_value = os.getenv("gcp_sync", "")
    # 优先使用配置文件值
    return parse_bool_value(config_value) or parse_bool_value(env_value)


def main(account_id: Optional[str] = None, resources: List[str] = None, executors=None):
    """
    账户级别的任务锁，确保每个 account_id 只能有一个同步任务运行。
    资产手动触发同步入口。
    定时任务默认同步所有账号和所有资源类型。
    :param executors:
    :param account_id:  账号ID，对应 CMDB 的唯一标识
    :param resources: 需要同步的资源类型，例如 ['ecs', 'rds', '...']
    :return:
    """
    # 读取全局配置，判断是否启用 GCP 同步
    # gcp_sync = get_gcp_sync_config()
    # if not gcp_sync:
    #     return
    sync_mapping = mapping.copy()
    if account_id is not None:
        for _, v in sync_mapping.items():
            v["account_id"] = account_id

        # 定义账户级别的任务锁，确保同一账户的任务不会并发执行且支持多账户执行

    @deco(RedisLock(f"async_gcp_to_cmdb_{account_id}_redis_lock_key"
                    if account_id else "async_gcp_to_cmdb_redis_lock_key"), release=True)
    def index():
        filtered_sync_mapping = {k: v for k, v in sync_mapping.items() if k in resources} if resources else sync_mapping
        if not filtered_sync_mapping:
            logging.warning("未找到需要同步的资源类型")
            return
        # 使用传入的线程池或创建临时线程池
        if executors:
            # 使用传入的线程池
            futures = []
            for config in filtered_sync_mapping.values():
                future = executors.submit(sync, config)
                futures.append(future)

            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"资源同步任务失败: {traceback.print_exc()}")
        else:
            with ThreadPoolExecutor(max_workers=len(filtered_sync_mapping)) as executor:
                executor.map(sync, filtered_sync_mapping.values())

    index()


if __name__ == "__main__":
    main()
