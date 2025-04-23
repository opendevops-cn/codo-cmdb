#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/11/1 16:05
# @Author  : harilou
# @Describe: 资产变更通知

import datetime
import json
import logging
import traceback

import requests
from jinja2 import Template
from sqlalchemy import inspect

from websdk2.configs import configs
from websdk2.consts import const
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate

from websdk2.tools import RedisLock
from db_sync import engine, default_configs
from libs import deco
from libs.scheduler import scheduler
from libs.utils import human_date
from models import asset_mapping, RES_TYPE_MAP
from models.asset import AssetServerModels, AssetBackupModels
from services.asset_server_service import _models_to_list


class AssetChangeNotify:
    """资源变更通知"""

    def __init__(self, asset_type):
        self.asset_type = asset_type

    def get_model_columns_map(self, model) -> dict:
        """
        获取Model字段和字段映射
        @param model: model对象
        @return: {字段名：字段说明}
        """
        inspect_resp = inspect(engine)
        model_mate = inspect_resp.get_columns(model.__tablename__,
                                              schema=default_configs.get(const.DBNAME_KEY))  # 表名，库名
        return {field["name"]: field["comment"] for field in model_mate}

    def __delete_data(self, days=None) -> None:
        """
        删除过期的数据 60天前的数据
        @param days: 需要删除的日期
        @return:
        """
        if days is None:
            dest_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        else:
            dest_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        with DBContext('w', None, True) as session:
            session.query(AssetBackupModels).filter(AssetBackupModels.asset_type == self.asset_type,
                                                    AssetBackupModels.created_day < dest_date).delete(synchronize_session=False)
        return

    def get_cmdb_change_day(self, dest_date=None) -> dict:
        """
        根据时间和资源类型，比对差异内容并发送通知
        :param dest_date: 需要对比目标日期， 默认是昨天; 格式：2023-11-01
        :return: dict()
        """
        # 删除过期的数据
        self.__delete_data()

        if dest_date is None:
            dest_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        today = datetime.datetime.today().strftime("%Y-%m-%d")
        with DBContext('r', None, True) as session:
            today_obj = session.query(AssetBackupModels).filter(AssetBackupModels.asset_type == self.asset_type,
                                                                AssetBackupModels.created_day == today).all()
            dest_date_obj = session.query(AssetBackupModels).filter(AssetBackupModels.asset_type == self.asset_type,
                                                                    AssetBackupModels.created_day == dest_date).all()

            if not dest_date_obj or not today_obj:
                return dict()
            # 根据资源类型获取资源model对象
            asset_model = asset_mapping.get(self.asset_type)

            dest_data = {i.instance_id: json.loads(i.data) for i in dest_date_obj}
            # 字段的描述映射
            columns_map = self.get_model_columns_map(model=asset_model)

            del_list = list()
            add_list = list()
            update_list = list()
            host_change_data = dict()

            for item in today_obj:
                # 新增的资源
                if item.instance_id not in dest_data:
                    add_list.append(item.name)
                    continue
                hostname = item.name
                old_data = dest_data.get(item.instance_id)
                # 比对差异
                data = json.loads(item.data)
                for key, val in data.items():
                    if key in ["update_time", "create_time", "instance_expired_time"]:
                        continue
                    old_val = str(old_data.get(key, ""))
                    if str(val) != old_val:
                        if hostname not in host_change_data:
                            host_change_data[hostname] = list()
                        logging.info(f"hostname:{hostname};val:{val},old:{old_val}")
                        # 更新的内容
                        host_change_data[hostname].append({
                            "desc": columns_map.get(key, key),
                            "new": val,
                            "old": old_val
                        })
                        # 更新的资源
                        if hostname not in update_list:
                            update_list.append(hostname)

                dest_data.pop(item.instance_id)

            # 统计回收的资源
            if dest_data:
                del_list = [i["name"] for i in dest_data.values()]

            data_list = [
                {
                    "action": "新增",
                    "hostname_list": ", ".join(add_list),
                    "count": len(add_list)
                },
                {
                    "data": host_change_data,
                    "action": "变更",
                    "hostname_list": ", ".join(update_list),
                    "count": len(update_list)
                },
                {
                    "action": "回收",
                    "hostname_list": ", ".join(del_list),
                    "count": len(del_list)
                }]
            logging.info(f"data_list: {data_list}")
            # 获取资源的汇总数量
            asset_count = session.query(asset_model).count()
            gen_data = {"data_list": data_list, "total": asset_count}
        return gen_data

    def generate_tmp(self, data) -> str:
        """
        将数据进行渲染
        @param data: 需要渲染的数据
        @return: 渲染后的文本内容
        """
        notify_tmp = """
**总数:** 共**{{ data.total }}**台
**************************
{% for item in data.data_list %}
**{{ item.action }}:** 共**{{ item.count }}**台
    **服务器列表:** ({{ item.hostname_list }})
{% if item.data %}
{% for name, value_list in item.data.items() %}
        **{{ name }}:**
        {% for v in value_list %}
            **{{ v.desc }}:** {{ v.old }} **➔** {{ v.new }}
{% endfor  %}
{% endfor  %}
{% endif %}
**************************
{% endfor  %}
            """
        tm = Template(notify_tmp)
        msg = tm.render(data=data)
        # 去除空行
        msg_list = [i for i in msg.split("\n") if ":" in i or "*" in i]
        msg_text = "\n".join(msg_list)
        return msg_text

    def notify_to_fs(self, text, title) -> None:
        """
        向飞书推送报告
        @param text: 主体消息内容
        @param title: 标题
        @return:
        """
        if title:
            title = f"👏 CMDB{title} 👏"
        else:
            title = "👏 CMDB报告 👏"
        data = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [{
                    "tag": "markdown",
                    "content": text
                },
                    {
                        "tag": "action",
                        "actions": [{
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "打开CMDB"
                            },
                            "type": "primary",
                            "multi_url": {
                                "url": "http://spug.123u.com/resource/host",
                                "pc_url": "",
                                "android_url": "",
                                "ios_url": ""
                            }
                        }]
                    }
                ],
                "header": {
                    "template": "blue",
                    "title": {
                        "content": title,
                        "tag": "plain_text"
                    }
                }
            }
        }
        r = requests.post(configs["asset_change_notify"].get("feishu"), data=json.dumps(data))
        if r.status_code != 200 or r.json().get("StatusCode") != 0:
            logging.error(f"CMDB Changed send fail, error:{r.text}")
        else:
            logging.info(f"CMDB Changed send text:{r.text}")
        return

    def run(self, dest_date, title=None) -> None:
        """将变更数据差异部分发送通知"""
        gen_data = self.get_cmdb_change_day(dest_date)
        if not gen_data:
            return
        send_text = self.generate_tmp(gen_data)
        logging.info(f"send_text:\n{send_text}")
        self.notify_to_fs(send_text, title)
        return

    def send_change_to_yesterday(self) -> None:
        """发送日报，与昨天相比的资源变更"""
        date = datetime.datetime.now() - datetime.timedelta(days=1)
        title = f"日报-{dict(RES_TYPE_MAP).get(self.asset_type, self.asset_type)}"
        return self.run(dest_date=date.strftime("%Y-%m-%d"), title=title)

    def send_change_to_week(self) -> None:
        """发送周报，与一周前相比的资源变更"""
        date = datetime.datetime.now() - datetime.timedelta(days=7)
        title = f"周报-{dict(RES_TYPE_MAP).get(self.asset_type, self.asset_type)}"
        return self.run(dest_date=date.strftime("%Y-%m-%d"), title=title)

    def send_change_to_month(self) -> None:
        """发送周报，与30天相比的资源变更"""
        date = datetime.datetime.now() - datetime.timedelta(days=30)
        title = f"月报-{dict(RES_TYPE_MAP).get(self.asset_type, self.asset_type)}"
        return self.run(dest_date=date.strftime("%Y-%m-%d"), title=title)

@deco(RedisLock("asset_cmdb_backup_redis_lock_key"))
def cmdb_backup():
    """定时每天备份主机资源"""
    logging.info("===开始执行 定时每天备份资源")
    try:
        with DBContext('w', None, True) as session:
            asset_obj = session.query(AssetBackupModels).filter(AssetBackupModels.created_day == human_date()).order_by(
                "instance_id").all()
            ins_id_list = [i.instance_id for i in asset_obj]

            page = paginate(session.query(AssetServerModels), page_size=300)
            data = _models_to_list(page.items)
            for info in data:
                instance_id = info["instance_id"]
                insert_data = dict(
                    asset_id=info["id"],
                    name=info["name"],
                    inner_ip=info["inner_ip"],
                    instance_id=info["instance_id"],
                    asset_type="server",
                    created_day=human_date(),
                    data=json.dumps(info),
                )
                if instance_id not in ins_id_list:
                    session.add(AssetBackupModels(**insert_data))
            session.commit()
        logging.info("===执行完成 定时每天备份资源")
    except:
        logging.error(f"===执行失败 定时每天备份资源: {traceback.format_exc()}")
    return


@deco(RedisLock("asset_change_to_yesterday_redis_lock_key"))
def send_asset_change_to_yesterday_task():
    asset_notify = AssetChangeNotify(asset_type="server")
    asset_notify.send_change_to_yesterday()
    return


@deco(RedisLock("asset_change_to_week_redis_lock_key"))
def send_asset_change_to_week_task():
    asset_notify = AssetChangeNotify(asset_type="server")
    asset_notify.send_change_to_week()
    return


@deco(RedisLock("asset_change_to_month_redis_lock_key"))
def send_asset_change_to_month_task():
    asset_notify = AssetChangeNotify(asset_type="server")
    asset_notify.send_change_to_month()
    return


def init_cmdb_change_tasks() -> None:
    scheduler.add_job(cmdb_backup, 'cron', hour=5, minute=1)
    scheduler.add_job(send_asset_change_to_yesterday_task, 'cron', hour=10, minute=1)
    scheduler.add_job(send_asset_change_to_week_task, 'cron', day_of_week=4, hour=17, minute=1)
    scheduler.add_job(send_asset_change_to_month_task, 'cron', month="*", day=1, hour=10)
