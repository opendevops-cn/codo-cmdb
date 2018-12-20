# Ansible2_myAPI

Ansible1.9版本的API的使用是非常简单的，但是进入2.0后，Ansible开发者对其代码结构 进行了重组，开放出来的API异常'笨重'。

`Ansible2_myAPI`是仿照Ansible1.9 API的使用风格，对Ansible2.0+ API的简单封装, 使得2.0+ API的使用像1.9 API一样简单。

[官方Ansible API](http://docs.ansible.com/ansible/dev_guide/developing_api.html#python-api-2-0)


## 特点
* Ansible的Inventory 不限于hosts静态文件和动态生成(可执行文件)，支持Python容器对象(列表，字典，字符串)，详见下文。
* 支持`Ad-hoc`和`playbook`两种执行方式。
* 支持组变量， 主机变量， 额外变量。

## 测试环境
* python2.7测试通过，其他python版本未测试
* Ansible2.0 ~ 2.3
* Ansible2.4 ~ 2.5
* 秘钥免登陆访问

## 分支说明
因ansible2.4版本较2.3版本改动较大,所以开一个分支兼容2.4以上版本
* master分支: 支持ansible2.0 ~ 2.3本版本
* for-2.4分支: 支持ansible2.4 + 2.5 版本

## Inventory 扩展
根据官方动态主机仓库(Dynamic Inventory)的使用规则，扩展了主机仓库的形式。
官方支持的inventory:
* 主机列表
```python
hosts = ['1.1.1.1', '2.2.2.2']
```
* 字符串
```python
hosts = "1.1.1.1,2.2.2.2"  # ','分割符两边不能有空格
hosts = "1.1.1.1," # 单个主机也必须有','
```
* 可执行文件
```python
hosts = "path/to/execalbe_file"  # 给定一个可执行的文件
```
* 静态hosts文件
```python
hosts = "/path/to/hosts"  # ini格式
```

扩展的inventory:
* 字符串
```python
hosts = "1.1.1.1" 				# 修复必须有','bug.
hosts = "1.1.1.1, 2.2.2.2"		# ','两边可以有空格
```
* 字典
```python
hosts = {
	"group1": ["1.1.1.1", "2.2.2.2"],  	#格式1
    "group2": {						    #格式2
    	"hosts": ["1.1.1.1", "2.2.2.2"],
        "vars":{"some_vars": "some_values"},
        "children": ["other_group"],
    },
    "3.3.3.3": {							# 格式3
    	"some_var2": "some_value2",
		"foo": "bar"
    }
    "_meta": {								# 主机变量
    	"hostvars": {
        	"1.1.1.1": {"var1": "value1"},
            "2.2.2.2": {"var2": "value2"},
            "3.3.3.3": {"var3": "value3"}
		}
    }
}
```

## 使用示例：
Ad-hoc
```python
from pprint import pprint
from Ansible2_myAPI.runner import Runner

runner = Runner(
	module_name="shell",
    module_args="uptime",
    remote_user="root",
    pattern="all",
    hosts="192.168.1.100, 1.1.1.1"
)

result = runner.run()

pprint(result)
```
输出
```python
{'contacted': {
	'192.168.1.100': {
    	'_ansible_no_log': False,
        '_ansible_parsed': True,
        u'changed': True,
        u'cmd': u'uptime',
        u'delta': u'0:00:00.006604',
        u'end': u'2017-01-16 16:47:44.051826',
        'invocation': {
        	u'module_args': {
                u'_raw_params': u'uptime',
                u'_uses_shell': True,
                u'chdir': None,
                u'creates': None,
                u'executable': None,
                u'removes': None,
                u'warn': True},
           'module_name': u'command'},
        u'rc': 0,
        u'start': u'2017-01-16 16:47:44.045222',
        u'stderr': u'',
        u'stdout': u' 16:47:44 up 570 days,  1:40,  1 user,  load average: 0.01, 0.02, 0.05',
        'stdout_lines': [u' 16:47:44 up 570 days,  1:40,  1 user,  load average: 0.01, 0.02, 0.05'],
        u'warnings': []}},
 'dark': {'1.1.1.1': {
             'changed': False,
             'msg': u'Failed to connect to the host via ssh: ssh: connect to host 1.1.1.1 port 22: Connection timed out\r\n',
             'unreachable': True}}}

```

playbook
```python
from pprint import pprint
from Ansible2_myAPI.playbook_runner import PlaybookRunner

runner = PlaybookRunner(
	playbook_path="some.yml",
    hosts="192.168.1.100, 1.1.1.1",
)

result = runner.run()
pprint(result)
```
some.yml
```YAML
---
- name: Test the plabybook API.
  hosts: all
  remote_user: root
  gather_facts: yes
  tasks:
   - name: exec uptime
     shell: uptime
```
输出
```
{'plays': [{'play': {'id': '9627b6a0-4507-4682-a1f4-242c51577b83',
                     'name': u'Test the plabybook API.'},
            'tasks': [{'hosts': {
            			'1.1.1.1': {'changed': False,
                             'msg': u'Failed to connect to the host via ssh: ssh: connect to host 1.1.1.1 port 22: Connection timed out\r\n',
                             'unreachable': True},
                     	'192.168.1.100': {'_ansible_no_log': False,
                              '_ansible_parsed': True,
                              u'_ansible_verbose_override': True,
                              u'changed': False,
                              'invocation': {
                                  u'module_args':
                                      {u'fact_path':u'/etc/ansible/facts.d',
                                      u'filter': u'*',
                                      u'gather_subset': [u'all'],
                                      u'gather_timeout': 10},
                             'module_name': u'setup'}}},
                       'task': {'name': 'setup'}},
                      {'hosts': {'192.168.1.100': {'_ansible_no_log': False,
                              '_ansible_parsed': True,
                              u'changed': True,
                              u'cmd': u'uptime',
                              u'delta': u'0:00:00.006512',
                              u'end': u'2017-01-16 16:56:33.838901',
                              'invocation': {u'module_args': {
                                                 u'_raw_params': u'uptime',
                                                  u'_uses_shell': True,
                                                  u'chdir': None,
                                                  u'creates': None,
                                                  u'executable': None,
                                                  u'removes': None,
                                                  u'warn': True},
                                             'module_name': u'command'},
                              u'rc': 0,
                              u'start': u'2017-01-16 16:56:33.832389',
                              u'stderr': u'',
                              u'stdout': u' 16:56:33 up 570 days,  1:49,  1 user,  load average: 0.01, 0.02, 0.05',
                              'stdout_lines': [u' 16:56:33 up 570 days,  1:49,  1 user,  load average: 0.01, 0.02, 0.05'],
                              u'warnings': []}},
                       'task': {'name': u'exec uptime'}}]}],
 'stats': {'1.1.1.1': {'changed': 0,
                       'failures': 0,
                       'ok': 0,
                       'skipped': 0,
                       'unreachable': 1},
           '192.168.1.100': {'changed': 1,
                            'failures': 0,
                            'ok': 2,
                            'skipped': 0,
                            'unreachable': 0}}}
```

