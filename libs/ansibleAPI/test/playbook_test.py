#!/usr/bin/env python
# coding:utf8


import sys
sys.path.append("../")
from playbook_runner import PlaybookRunner
from pprint import pprint

host_dict = {
    "group1": {
        'hosts': ["192.168.1.100", "1.1.1.1", "192.168.70.39"],
        'vars': {'host': 'var_value'}
    },
    "_meta":{
        "hostvars":{
            "192.168.1.100":{
                "zone_dirs": ["/home/gjobs3","/home/gjobs2"]
                }
            }
        }
}


runner = PlaybookRunner(
    # playbook_path="two_play.yml",
    playbook_path="debug.yml",
    hosts=host_dict,
)


try:
    results = runner.run()
    pprint(results)
except Exception as e:
    print(e)
