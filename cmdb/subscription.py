#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2024/1/19
Desc    : Redis消息订阅服务
"""

import json
import logging
import time
import redis
from shortuuid import uuid
from concurrent.futures import ThreadPoolExecutor
from websdk2.db_context import DBContext
from websdk2.consts import const
from models.asset import AssetServerModels as serverModel


class RedisSubscriber:

    def __init__(self, service="cc-cmdb-agent-consumer-name", channel='cc.v1.discover.stream', **settings):
        redis_info = settings.get(const.REDIS_CONFIG_ITEM, None).get(const.DEFAULT_RD_KEY, None)
        if not redis_info:  exit('not redis')
        self.pool = redis.ConnectionPool(host=redis_info.get(const.RD_HOST_KEY),
                                         port=redis_info.get(const.RD_PORT_KEY, 6379), db=2,
                                         password=redis_info.get(const.RD_PASSWORD_KEY, None), decode_responses=True)
        self.redis_conn = redis.StrictRedis(connection_pool=self.pool)
        # self.redis_conn = cache_conn(db=2)
        self.channel = channel  # 定义频道名称
        self.consumer_name = f"{service}-{uuid()[0:6]}"
        # self.consumer_name = service
        self.group_name = "cc-cmdb-agent-consumer-group"
        self.stream_name = channel
        self.create_consumer_group(self.stream_name, self.group_name)

    def start_server(self):
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.subscribe_msgs)

    def create_consumer_group(self, stream_name, group_name):
        try:
            if not self.redis_conn.exists(stream_name):
                self.redis_conn.xadd(stream_name, {'test': 'true'})
            ret = self.redis_conn.xgroup_create(stream_name, group_name, id=0)
        except Exception as err:
            logging.debug('create_consumer_group', err)

    def stream_message(self, stream_name):
        """stream and groups info"""
        logging.info(f'stream info: {self.redis_conn.xinfo_stream(stream_name)}')
        logging.info(f'groups info: {self.redis_conn.xinfo_groups(stream_name)}')

    @staticmethod
    def process_message(msg_id, fields) -> dict:
        # if 'test' in fields: return {}
        # logging.info(msg_id)

        log_data = list(fields.values())[0]
        log_data_dict = json.loads(log_data)
        return log_data_dict

    def subscribe_msgs(self):
        logging.info(f"Consumer {self.consumer_name} starting...")
        last_id = '0-0'
        check_backlog = True
        while True:
            try:
                consumer_id = last_id if check_backlog else '>'
                try:
                    # logging.error(f"{self.group_name, self.consumer_name, {self.stream_name: consumer_id} }")
                    items = self.redis_conn.xreadgroup(self.group_name, self.consumer_name,
                                                       {self.stream_name: consumer_id}, block=0, count=1)
                except Exception as err:
                    logging.warning(err)
                    items = []

                if not items:  # 如果 block 不是 0或者为空, 会需要这段
                    logging.warning("Read timeout, no new message received.")
                    self.stream_message(self.stream_name)
                    time.sleep(3)  # 空值等待 3s
                    self.redis_conn.xack(self.stream_name, self.group_name, last_id)  ### 删除错误信息
                    continue

                elif not items[0][1]:
                    check_backlog = False

                for msg_id, fields in items[0][1]:
                    try:
                        logging.info(f"Processing message {msg_id}: {fields}")
                        try:
                            # data = json.loads(fields['host_snap_info'].decode())
                            data = self.process_message(msg_id, fields)
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error: {e}")
                            continue

                        agent_info = data.get('agent_info')
                        if agent_info and 'agent_id' in agent_info:
                            agent_id = agent_info.get('agent_id')
                            logging.debug(f"agent info sync {agent_id} {agent_info}")
                            try:
                                with DBContext('w', None, True) as session:
                                    session.query(serverModel).filter(serverModel.agent_id == agent_id).update(
                                        dict(agent_info=agent_info))
                            except Exception as e:
                                logging.error(f"写入数据库失败{e}")

                    except Exception as err:
                        logging.error(f"Error processing message {msg_id}: {err}")
                        continue
                    finally:
                        last_id = msg_id
                        self.redis_conn.xack(self.stream_name, self.group_name, msg_id)
                        self.redis_conn.xdel(self.stream_name, msg_id)  # 删除消息

                time.sleep(2)  # Wait before the next iteration
                # one_day_ago = int((time.time() - 86400) * 1000)
                # self.redis_conn.xtrim(self.stream_name, minid=one_day_ago)
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")
                time.sleep(3)
