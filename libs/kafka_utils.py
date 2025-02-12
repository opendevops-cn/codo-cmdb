# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/2/8
# @Description: Description
import json

from confluent_kafka import Producer
from websdk2.configs import configs
from websdk2.consts import const


class KafkaProducer:
    def __init__(
        self, bootstrap_servers=None, client_id: str = None, topic=None):
        if bootstrap_servers is None:
            self.bootstrap_servers = configs[const.KAFKA_BOOTSTRAP_SERVERS]
        else:
            self.bootstrap_servers = bootstrap_servers
        if client_id is None:
            self.client_id = configs[const.KAFKA_CLIENT_ID]
        else:
            self.client_id = client_id
        if topic is None:
            self.topic = configs[const.KAFKA_TOPIC]
        else:
            self.topic = topic
        self._create_producer()

    def _create_producer(self):
        producer_conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
        }
        self.producer = Producer(producer_conf)

    def send(self, message):
        if isinstance(message, dict):  # 如果是字典，转换为 JSON 字符串
            message = json.dumps(message).encode("utf-8")  # 变成 bytes
        elif isinstance(message, str):
            message = message.encode("utf-8")
        elif not isinstance(message, bytes):
            raise TypeError("message 必须是 dict, str 或 bytes 类型")
        self.producer.produce(self.topic, message)
        self.producer.flush()
