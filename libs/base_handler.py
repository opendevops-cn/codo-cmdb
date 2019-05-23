# !/usr/bin/env python
# -*-coding:utf-8-*-

import shortuuid
from websdk.base_handler import BaseHandler as SDKBaseHandler


class BaseHandler(SDKBaseHandler):
    def __init__(self, *args, **kwargs):
        self.new_csrf_key = str(shortuuid.uuid())
        super(BaseHandler, self).__init__(*args, **kwargs)

