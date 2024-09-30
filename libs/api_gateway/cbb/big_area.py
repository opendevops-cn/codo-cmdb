# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: 大区接口

from typing import List, Dict, Any, TypedDict

from libs.api_gateway.cbb.base import CBBBaseAPI


class BigArea(TypedDict):
    big_area: str
    name: str
    tags: List[str]
    address: str
    utc_offset: int
    visible: bool
    ext: str

class Body(TypedDict):
    big_area_count: int
    big_areas: List[BigArea]

class Head(TypedDict):
    errno: int
    errmsg: str

class BigAreaResponse(TypedDict):
    head: Head
    body: Body


class BigAreaAPI(CBBBaseAPI):

    def get_big_areas(self, tag_filter: List[List[str]] = None, big_area: str = None,
                          query_string: str = None, page_no: int = 1, page_size: int = 10) ->BigAreaResponse:
        """
        模糊查询大区列表.
        :param tag_filter: tag过滤器.
        :param big_area: 大区id.
        :param query_string: 查询字符串.
        :param page_no: 页码.
        :param page_size: 每页数量.
        :return: 大区列表.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1010},
            "body": {}
        }
        if tag_filter is not None:
            body["body"]["tag_filter"] = tag_filter
        if big_area is not None:
            body["body"]["big_area"] = big_area
        if query_string is not None:
            body["body"]["query_string"] = query_string
        if page_no is not None:
            body["body"]["page_no"] = int(page_no)
        if page_size is not None:
            body["body"]["page_size"] = int(page_size)
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e

    def get_big_area_detail(self, tag_filter: List[List[str]] = None, big_area: str = None) -> Dict[str, Any]:
        """
        获取大区详情.
        :param big_area: 大区id.
        :param tag_filter: tag过滤器.
        :return: 大区详情.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1003},
            "body": {}
        }
        if tag_filter is not None:
            body["body"]["tag_filter"] = tag_filter
        if big_area is not None:
            body["body"]["big_area"] = big_area
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e


    def delete_big_area(self, big_area: str) -> Dict[str, Any]:
        """
        删除大区.
        :param big_area: 大区id.
        :return: 无.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1004},
            "body": {"big_area": big_area}
        }
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e


    def create_or_update_big_area(self, **data) -> Dict[str, Any]:
        """
        上传大区.
        :param data: 大区数据.
        :return: 上传结果.
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1005},
            "body": data,
        }
        try:
            return self.send_request(self.base_url, body=body)
        except Exception as e:
            raise e
          

if __name__ == '__main__':
    pass
