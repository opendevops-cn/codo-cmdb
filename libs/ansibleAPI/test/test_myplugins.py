#!/usr/bin/env python
# coding:utf-8

import sys
from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader

sys.path.append("../")

from myinventory import (InventoryStringPlugin, InventoryDictPlugin,
                         InventoryListPlugin)



def test_string():
    inventory = InventoryData()
    loader = DataLoader()

    a = InventoryStringPlugin()
    a.parse(inventory, loader, "1.1.1.1")
    a.parse(inventory, loader, "1.1.1.1,")
    a.parse(inventory, loader, "1.1.1.1, 2.2.2.2")
    print "hosts:", inventory.hosts
    print "groups:", inventory.groups

def test_list():
    inventory = InventoryData()
    loader = DataLoader()

    b = InventoryListPlugin()
    b.parse(inventory, loader, ["1.1.1.1", "2.2.2.2"])
    b.parse(inventory, loader, {"1.1.1.1", "2.2.2.2"})

    print "hosts:", inventory.hosts
    print "groups:", inventory.groups

def test_dict():
    inventory = InventoryData()
    loader = DataLoader()
    source = {
        "group1": ['1.1.1.1'],
        "group2": {
            "hosts": ["2.2.2.2"],
            "vars": {"var2": "var_value2"}
        },
        "3.3.3.3":{
            "ansible_ssh_host": "3.3.3.3",
            "3vars": "3value"
            },
        "_meta":{"hostvars":{}}
    }

    c = InventoryDictPlugin()
    c.parse(inventory, loader, source)

    print "hosts:", inventory.hosts
    print "groups:", inventory.groups

if __name__ == "__main__":
    test_string()
    print "string ok"
    print
    test_list()
    print "list ok"
    print
    test_dict()
    print "dict ok"
    print

