#!/usr/bin/env python
# coding:utf8

from collections import Mapping
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils.six import iteritems, string_types
from ansible.module_utils._text import to_native

__all__ = ["MyInventory"]

HOSTS_PATTERNS_CACHE = {}


class MyInventory(InventoryManager):
    """
    this is my ansible inventory object.
    支持三种数据类型的主机信息:
        - 字符串形式： "1.1.1.1, 2.2.2.2", "1.1.1.1"
        - 列表/集合形式: ["1.1.1.1", "2.2.2.2"],  {"1.1.1.1", "2.2.2.2"}
        - 字典形式: {
            "group1": {
                "hosts": [{"hostname": "10.10.10.10", "port": "22",
                            "username": "test", "password": "mypass"}, ...]
                "vars": {"var1": value1, "var2": value2, ...}
            }
        }
    """
    def __init__(self, host_list=None):
        self.loader = DataLoader()
        super(MyInventory, self).__init__(self.loader, host_list)

    def _setup_inventory_plugins(self):
        self._inventory_plugins = [InventoryStringPlugin(),
                                   InventoryListPlugin(),
                                   InventoryDictPlugin()]

    def parse_sources(self, cache=False):
        """
        覆盖父类的解析方法，因为父类的该方法要:
            1. 遍历内容
            2. 路径字符串处理
        而这里的解析只需要直接解析就行.
        """

        self._setup_inventory_plugins()

        parsed = self.parse_source(self._sources)
        if parsed:
            self._inventory.reconcile_inventory()

        self._inventory_plugins = []

    def parse_source(self, source):
        parsed = False

        if not self._inventory_plugins:
            self._setup_inventory_plugins()

        for plugin in self._inventory_plugins:
            if plugin.verify_file(source):
                try:
                    plugin.parse(self._inventory, self._loader, source)
                    parsed = True
                    break
                except:
                    pass
        else:
            raise AnsibleParserError("No plugin could parse your data.")

        return parsed


class InventoryStringPlugin(BaseInventoryPlugin):
    """
    解析逗号间隔的主机地址
    参考原生插件: host_list
    """

    NAME = 'host_string'
    _load_name = NAME
    _original_path = ""

    def verify_file(self, host_string):
        return isinstance(host_string, string_types)

    def parse(self, inventory, loader, host_string, cache=None):
        super(InventoryStringPlugin, self).parse(inventory, loader, host_string)
        try:
            if "," in host_string:
                host_string = [h.strip() for h in host_string.split(',') if h and h.strip()]
            else:
                host_string = [ host_string]

            for h in host_string:
                if h not in self.inventory.hosts:
                    self.inventory.add_host(h, group='ungrouped', port=None)
        except Exception as e:
            raise AnsibleParserError("Invalid data from string, could not parse: %s" % to_native(e))


class InventoryListPlugin(BaseInventoryPlugin):
    """
    解析主机列表
    参考原生插件: host_list
    """

    NAME = "host_list"
    _load_name = NAME
    _original_path = ""

    def verify_file(self, host_list):
        return isinstance(host_list, (list, set))

    def parse(self, inventory, loader, host_list, cache=None):
        #print('11111111->',inventory, loader, host_list)
        super(InventoryListPlugin, self).parse(inventory, loader, host_list)
        try:
            for h in host_list:
                if h not in self.inventory.hosts:
                    self.inventory.add_host(h, group='ungrouped')
        except Exception as e:
            raise AnsibleParserError("Invalid data from sequnes, could not parse: %s" % to_native(e))


class InventoryDictPlugin(BaseInventoryPlugin):
    """
    参照原生插件: script
    Host inventory parser for ansible using Dict data. as inventory scripts.
    """
    NAME = "host_dict"
    _load_name = NAME
    _original_path = ""

    def __init__(self):
        super(InventoryDictPlugin, self).__init__()
        self._hosts = set()

    def verify_file(self, sources):
        return isinstance(sources, Mapping)

    def parse(self, inventory, loader, sources, cache=None):
        # print('souce---->',sources)
        super(InventoryDictPlugin, self).parse(inventory, loader, sources)
        try:
            self.inventory.add_host(host=sources.get('host'), group='ungrouped', port=sources.get('port'))
        except Exception as e:
            raise AnsibleParserError("Invalid data from sequnes, could not parse: %s" % to_native(e))

        # 下面这块有时间修改，应该是支持dict传入多主机的，目前先以self.inventory.add_host处理
        # data_from_meta = {}
        #
        # try:
        #     for group, gdata in sources.iteritems():
        #         if group == "_meta":
        #             if "hostvars" in gdata:
        #                 data_from_meta = gdata['hostvars']
        #         else:
        #             self._parse_group(group, gdata)
        #
        #     for host in self._hosts:
        #         got = {}
        #         if data_from_meta:
        #             got = data_from_meta.get(host, {})
        #
        #         self._set_host_vars([host], got)
        #
        # except Exception as e:
        #     raise AnsibleParserError(to_native(e))

    def _set_host_vars(self, *args, **kwargs):
        if hasattr(self, "populate_host_vars"):
            self.populate_host_vars(*args, **kwargs)
        elif hasattr(self, "_populate_host_vars"):
            self._populate_host_vars(*args, **kwargs)
        else:
            raise Exception("Have no host vars set function.")

    def _parse_group(self, group, data):
        self.inventory.add_group(group)

        if not isinstance(data, dict):
            data = {'hosts': data}
        elif not any(k in data for k in ('hosts', 'vars', 'children')):
            data = {'hosts': [group], 'vars': data}

        if 'hosts' in data:
            if not isinstance(data['hosts'], list):
                raise AnsibleError("You defined a group '%s' with bad data for the host list:\n %s" % (group, data))

            for hostname in data['hosts']:
                self._hosts.add(hostname)
                self.inventory.add_host(hostname, group)

        if 'vars' in data:
            if not isinstance(data['vars'], dict):
                raise AnsibleError("You defined a group '%s' with bad data for variables:\n %s" % (group, data))

            for k, v in iteritems(data['vars']):
                self.inventory.set_variable(group, k, v)

        if group != '_meta' and isinstance(data, dict) and 'children' in data:
            for child_name in data['children']:
                self.inventory.add_group(child_name)
                self.inventory.add_child(group, child_name)


if __name__ == "__main__":
    host_list = {
        "group1": ['1.1.1.1'],
        "group2": {
            "hosts": ["2.2.2.2"],
            "vars": {"var2": "var_value2"}
        },
        "3.3.3.3":{
            "ansible_ssh_host": "3.3.3.3",
            "3vars": "3value"
            },
        "_meta":{"hostvars":
                 {"1.1.1.1":{"var1": "value1"},
                  "2.2.2.2":{"h2":"v2"},
                  "3.3.3.3":{"h3":"v3"},
                  }}
    }

    host_list1 = "1.1.1.1"
    host_list2 = ["1.1.1.1","2.2.2.2"]

    hosts_source = host_list
    myhosts = MyInventory(hosts_source)