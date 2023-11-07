#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/10/30 20:58
# @Author  : harilou
# @Describe: 通用方法
from datetime import datetime


def human_date(date=None):
    if date:
        assert isinstance(date, datetime)
    else:
        date = datetime.now()
    return date.strftime('%Y-%m-%d')