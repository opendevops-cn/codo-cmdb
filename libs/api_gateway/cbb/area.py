# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: 区服接口

from typing import List, Tuple, Optional

from libs.api_gateway.cbb.base import CBBBaseAPI


class AreaAPI(CBBBaseAPI):

    def get_areas(self, tag_filter: List[List[str]] = None, area: str = None, big_area: str = None,
                      query_string: str = None, page_no: int = 1, page_size: int = 10):
        """
        模糊查询区服列表.
        :param tag_filter: tag过滤器.
        :param area: 区服id.
        :param big_area: 大区id.
        :param query_string: 查询字符串.
        :param page_no: 页码.
        :param page_size: 每页数量.
        :return: 区服列表.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1011},
            "body": {}
        }
        if tag_filter:
            body["body"]["tag_filter"] = tag_filter
        if area:
            body["body"]["area"] = area
        if big_area:
            body["body"]["big_area"] = big_area
        if query_string:
            body["body"]["query_string"] = query_string
        if page_no:
            body["body"]["page_no"] = int(page_no)
        if page_size:
            body["body"]["page_size"] = int(page_size)
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e

    def get_area(self, tag_filter: List[List[str]] = None, area: str = None, big_area: str = None) -> dict:
        """
        获取区服详情.
        :param area: 区服id.
        :param tag_filter: tag过滤器.
        :param big_area: 大区id.
        :return: 区服详情.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1000},
            "body": {}
        }
        if tag_filter:
            body["body"]["tag_filter"] = tag_filter
        if area:
            body["body"]["area"] = area
        if big_area:
            body["body"]["big_area"] = big_area
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise


    def delete_area(self, area: str = None, big_area: str = None) -> Tuple[bool, Optional[str]]:
        """
        删除区服.
        :param area: 区服id.
        :param big_area: 大区id.
        :return: 删除结果.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1001},
            "body": {"area": area, "big_area": big_area}
        }
        try:
            data = self.send_request(self.base_url, body=body)
            head = data.get("head", {})
            if head.get("errno") != 0:
                return False, head.get("errmsg")
            return True, None
        except Exception as e:
            raise e


    def create_or_update_area(self, **data):
        """
        更新或创建区服.
        :param data: 区服数据.
        :return: 区服信息.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1002},
            "body": data
        }
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e


if __name__ == '__main__':
    pass
