# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/12
# @Description: 集群入口

import json
from abc import ABC

from services.asset_cluster_service import get_cluster_list_for_api, opt_obj as opt_obj_cluster

from libs.base_handler import BaseHandler


class K8sClusterHandler(BaseHandler, ABC):
    def get(self):
        res = get_cluster_list_for_api(**self.params)
        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_cluster.handle_delete(data)
        self.write(res)


cluster_urls = [
    (
        r"/api/v2/cmdb/k8s/cluster/",
        K8sClusterHandler,
        {"handle_name": "配置平台-云商-集群管理", "method": ["ALL"]},
    ),
]
