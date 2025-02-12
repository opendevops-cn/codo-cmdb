# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/2/8
# @Description: Description
import json

from confluent_kafka import Producer


class KafkaProducer:
    def __init__(
        self, bootstrap_servers=None, client_id: str = None, topic=None):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
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
