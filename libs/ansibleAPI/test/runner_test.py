#!/usr/bin/env python
# coding:utf8

import sys
sys.path.append("../")

from runner import Runner
from pprint import pprint

host_dict = {
    "group1": {
        'hosts': ["172.16.0.7", "1.1.1.1"],
        'vars': {'host': 'var_value'}
    },
    "_meta": {
        "hostvars": {
            "172.16.0.7": {"hosts": "hostvalue"}
        }
    }
}

runner = Runner(
    module_name="shell",
    module_args="uptime",
    remote_user="root",
    pattern="all",
    hosts=host_dict,
)

pprint(runner.run())
