#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
"""
from typing import List, Dict, Any, Union, Optional, TypedDict

# 定义通用返回值类型
class CommonResponse(TypedDict):
    code: int
    msg: str
    data: Optional[Union[List[Any], Dict[str, Any]]] = None
    count: Optional[int] = None