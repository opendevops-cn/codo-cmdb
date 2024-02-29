#!/usr/bin/env python
# -*- coding: utf-8 -*-

from settings import settings
from websdk2.configs import configs

if configs.can_import:
    configs.import_dict(**settings)


def deco(cls, release=False, **kw):
    def _deco(func):
        def __deco(*args, **kwargs):
            key_timeout, func_timeout = kw.get("key_timeout", 300), kw.get("func_timeout", 90)
            if not cls.get_lock(cls, key_timeout=key_timeout, func_timeout=func_timeout): return False
            try:
                return func(*args, **kwargs)
            finally:
                # 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco
