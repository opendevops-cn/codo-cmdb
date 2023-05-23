#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  Tree build
"""

from typing import *


class Tree:
    def __init__(self, data):
        self._data = data

    def get_root_node(self) -> dict:
        root_node = list(filter(lambda node: node["node_type"] == 0, self._data))[0]
        return root_node

    def get_child(self, node, parent_node=None):
        items = []  # type: List[Any]
        if node["node_type"] == 0:
            childs = list(
                filter(
                    lambda n: n["node_type"] == 1, self._data
                )
            )
            childs = sorted(childs, key=lambda s: s['node_sort'], reverse=False)  # 升序

        elif node["node_type"] == 1:
            childs = list(
                filter(
                    lambda n: n["node_type"] == 2 and n["parent_node"] == node["title"],
                    self._data
                )
            )
            childs = sorted(childs, key=lambda s: s['node_sort'], reverse=False)  # 升序

        elif node["node_type"] == 2:
            childs = list(filter(
                lambda n: n["node_type"] == 3 and n["parent_node"] == node["title"] and n["grand_node"] == node[
                    "parent_node"], self._data))
            # for i in childs: i['grand_node'] = node['parent_node']  ### 强行加了爷爷的名字
            childs = sorted(childs, key=lambda s: s['node_sort'], reverse=False)  # 升序

        else:
            childs = []
        for child in childs:
            child["children"] = self.get_child(child, node)
            # 2023年3月7日 为了让最后一级支持异步加载
            if not child["children"]:
                child["children"] = []
                child["loading"] = False
            items.append(child)
        return items

    def build(self):
        root_node = self.get_root_node()
        childs = self.get_child(root_node)
        root_node["children"] = childs
        return root_node
