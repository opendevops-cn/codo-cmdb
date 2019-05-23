#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/1 13:17
# @Author  : Fred Yangxiaofei
# @File    : test02.py.py
# @Role    : 说明脚本功能


from  libs.ansibleAPI.runner import Runner
import json


def exec_shell():
    runner1 = Runner(
        module_name="shell",
        module_args="uptime",
        remote_user="root",
        pattern="all",
        hosts="1.1.1.1"
    )
    result1 = runner1.run()
    print(result1)
    if result1['dark']:
        print(result1['dark'])



def exec_setup():
    '''获取主机详情'''
    runner2 = Runner(
        module_name="setup",
        module_args="",
        remote_user="root",
        pattern="all",
        hosts="172.16.0.101"
    )

    result2 = runner2.run()
    print(result2)


if __name__ == '__main__':
    exec_shell()
    exec_setup()
