# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/4/22
# @Description: 全局线程池


import threading
from concurrent.futures.thread import ThreadPoolExecutor


class GlobalThreadPoolManager:
    """全局线程池管理类，提供共享的线程池资源"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GlobalThreadPoolManager, cls).__new__(cls)
                cls._instance._cloud_executor = ThreadPoolExecutor(max_workers=10)
                cls._instance._general_executor = ThreadPoolExecutor(max_workers=5)
            return cls._instance

    @property
    def cloud_executor(self):
        """云资源同步专用线程池"""
        return self._cloud_executor

    @property
    def general_executor(self):
        """通用线程池"""
        return self._general_executor

    def shutdown(self, wait: bool = False):
        """关闭所有线程池"""
        self._cloud_executor.shutdown(wait=wait)
        self._general_executor.shutdown(wait=wait)


# 创建全局线程池实例
global_executors = GlobalThreadPoolManager()


if __name__ == '__main__':
    pass