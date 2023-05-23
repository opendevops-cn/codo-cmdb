#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2019年5月6日
role   : Application
"""

from abc import ABC
from websdk2.application import Application as myApplication
from domain.handlers.cloud_domain_handler import cloud_domain_urls


class Application(myApplication, ABC):
    def __init__(self, **settings):
        urls = []
        urls.extend(cloud_domain_urls)
        super(Application, self).__init__(urls, **settings)


if __name__ == '__main__':
    pass
