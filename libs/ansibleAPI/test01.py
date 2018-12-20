#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: test01.py.py
@time: 18/11/22下午4:33
'''
from runner import Runner
import json

Error_host = []

runner1 = Runner(
    module_name="copy",
    module_args="src=/Users/yangmv/PycharmProjectsPy3/CMDB/libs/script/sysinfo.py dest=/tmp/ backup=yes",
    remote_user="root",
    pattern="all",
    hosts="172.16.0.8"
)
runner2 = Runner(
    module_name="shell",
    module_args="/usr/bin/python /tmp/sysinfo.py",
    remote_user="root",
    pattern="all",
    hosts="172.16.0.8"
)


result1 = runner1.run()
if result1['dark']:
    for err_host in result1['dark']:
        Error_host.append(err_host)
    print('[Error] copy file faild => %s'%Error_host)
    exit(1)


result2 = runner2.run()
if result2['dark']:
    for err_host in result2['dark']:
        Error_host.append(err_host)
    print('[Error] exec sysinfo faild => %s'%Error_host)
    exit(2)

data = {}
for k,v in result2['contacted'].items():
    data[k] = json.loads(v['stdout'])
print(json.dumps(data))
