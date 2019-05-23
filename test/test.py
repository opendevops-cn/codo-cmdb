# import paramiko
# import sys
# import os
# import socket
# import getpass
#
# # from paramiko.py3compat import u
#
# # windows does not have termios...
# try:
#     import termios
#     import tty
#     has_termios = True
# except ImportError:
#     has_termios = False
#
# def interactive_shell(chan):
#     if has_termios:
#         posix_shell(chan)
#     else:
#         windows_shell(chan)
#
#
# def posix_shell(chan):
#     import select
#
#     oldtty = termios.tcgetattr(sys.stdin)
#     try:
#         tty.setraw(sys.stdin.fileno())
#         tty.setcbreak(sys.stdin.fileno())
#         chan.settimeout(0.0)
#         f = open('handle.log','a+')
#         tab_flag = False
#         temp_list = []
#         while True:
#             r, w, e = select.select([chan, sys.stdin], [], [])
#             if chan in r:
#                 try:
#                     x = chan.recv(1024)
#                     if len(x) == 0:
#                         sys.stdout.write('\r\n*** EOF\r\n')
#                         break
#                     if tab_flag:
#                         if x.startswith('\r\n'):
#                             pass
#                         else:
#                             f.write(x)
#                             f.flush()
#                         tab_flag = False
#                     sys.stdout.write(x)
#                     sys.stdout.flush()
#                 except socket.timeout:
#                     pass
#             if sys.stdin in r:
#                 x = sys.stdin.read(1)
#                 if len(x) == 0:
#                     break
#                 if x == '\t':
#                     tab_flag = True
#                 else:
#                     f.write(x)
#                     f.flush()
#                 chan.send(x)
#
#     finally:
#         termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
#
#
# def windows_shell(chan):
#     import threading
#
#     sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")
#
#     def writeall(sock):
#         while True:
#             data = sock.recv(256)
#             if not data:
#                 sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
#                 sys.stdout.flush()
#                 break
#             sys.stdout.write(data)
#             sys.stdout.flush()
#
#     writer = threading.Thread(target=writeall, args=(chan,))
#     writer.start()
#
#     try:
#         while True:
#             d = sys.stdin.read(1)
#             if not d:
#                 break
#             chan.send(d)
#     except EOFError:
#         # user hit ^Z or F6
#         pass
#
#
# def run():
#     # 获取当前登录用户
#
#
#     host_list = [
#         {'host': "172.16.0.101", 'username': 'root', 'pwd': "shinezone2015"},
#         {'host': "172.16.0.93", 'username': 'root', 'pwd': "shinezone2015"},
#         {'host': "172.16.0.219", 'username': 'root', 'pwd': "123123"},
#
#     ]
#     for item in enumerate(host_list, 1):
#         print(item['host'])
#
#     num = raw_input('序号：')
#     sel_host = host_list[int(num) -1]
#     hostname = sel_host['host']
#     username = sel_host['username']
#     pwd = sel_host['pwd']
#     print(hostname,username,pwd)
#
#
#     tran = paramiko.Transport((hostname, 22,))
#     tran.start_client()
#     tran.auth_password(username, pwd)
#     # 打开一个通道
#     chan = tran.open_session()
#     # 获取一个终端
#     chan.get_pty()
#     # 激活器
#     chan.invoke_shell()
#
#     interactive_shell(chan)
#
#     chan.close()
#     tran.close()
#
#
# if __name__ == '__main__':
#     run()


# -*- conding:utf-8 -*-
import json
import os
import sys
import time

from collections import namedtuple
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.inventory.group import Group
from ansible.inventory.host import Host
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager
from ansible.executor.playbook_executor import PlaybookExecutor


class ResultsCollector(CallbackBase):
    def __init__(self, *args, **kwargs):
        super(ResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.host_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result

    def v2_runner_on_skipped(self, result):
        self.state = 'skipped'
        self.result = result._result

    def v2_runner_on_no_hosts(self, task):
        print('skipping: no hosts matched')

    def v2_playbook_on_task_start(self, task, is_conditional):
        print("TASK [%s]" % task.get_name().strip())

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        if not name:
            msg = "PLAY"
        else:
            msg = "PLAY [%s]" % name

        print(msg)

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)

            msg = "PLAY RECAP [%s] : %s %s %s %s %s" % (
                h,
                "ok: %s" % (t['ok']),
                "changed: %s" % (t['changed']),
                "unreachable: %s" % (t['unreachable']),
                "skipped: %s" % (t['skipped']),
                "failed: %s" % (t['failures']),
            )
        print(msg)


class MyInventory(Inventory):
    """
    this is my ansible inventory object.
    """

    def __init__(self, resource, loader, variable_manager):
        self.resource = resource
        self.inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=[])
        self.gen_inventory()

    def my_add_group(self, hosts, groupname, groupvars=None):
        """
        add hosts to a group
        """
        my_group = Group(name=groupname)

        # if group variables exists, add them to group
        if groupvars:
            for key, value in groupvars.iteritems():
                my_group.set_variable(key, value)

                # add hosts to group
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            hostip = host.get('ip', hostname)
            hostport = host.get("port")
            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostip)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            my_host.set_variable('ansible_ssh_private_key_file', ssh_key)

            # set other variables
            for key, value in host.items():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
                    # add to group
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.my_add_group(self.resource, 'default_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.items():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class MyRunner(object):
    """
    This is a General object for parallel execute modules.
    """

    def __init__(self, resource, *args, **kwargs):
        self.resource = resource
        self.inventory = None
        self.variable_manager = None
        self.loader = None
        self.options = None
        self.passwords = None
        self.callback = None
        self.__initializeData()
        self.results_raw = {}

    def __initializeData(self):
        """
        初始化ansible
        """
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'timeout', 'remote_user',
                                         'ask_pass', 'private_key_file', 'ssh_common_args', 'ssh_extra_args',
                                         'sftp_extra_args',
                                         'scp_extra_args', 'become', 'become_method', 'become_user', 'ask_value_pass',
                                         'verbosity',
                                         'check', 'listhosts', 'listtasks', 'listtags', 'syntax'])

        # initialize needed objects
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.options = Options(connection='smart',
                               module_path='/usr/local/python36/lib/python3.6/site-packages/ansible/modules', forks=100,
                               timeout=10,
                               remote_user='root', ask_pass=False, private_key_file=None, ssh_common_args=None,
                               ssh_extra_args=None,
                               sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None,
                               become_user='root', ask_value_pass=False, verbosity=None, check=False, listhosts=False,
                               listtasks=False, listtags=False, syntax=False)

        self.passwords = dict(sshpass=None, becomepass=None)
        self.inventory = MyInventory(self.resource, self.loader, self.variable_manager).inventory
        self.variable_manager.set_inventory(self.inventory)

    def run(self, host_list, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        # create play with tasks
        print(host_list, module_name, module_args)
        play_source = dict(
            name="Ansible Play",
            hosts=host_list,
            gather_facts='no',
            tasks=[dict(action=dict(module=module_name, args=module_args))]
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        tqm = None
        self.callback = ResultsCollector()
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
            )
            tqm._stdout_callback = self.callback
            result = tqm.run(play)
            time.sleep(10)
        finally:
            if tqm is not None:
                tqm.cleanup()

    # def run_playbook(self, host_list, role_name, role_uuid, temp_param):
    def run_playbook(self, hosts, playbookfile, playbookvars):
        """
        run ansible palybook
        """
        try:
            self.callback = ResultsCollector()
            filenames = [playbookfile]  # playbook的路径
            print('ymal file path:%s' % filenames)

            extra_vars = playbookvars  # 额外的参数 sudoers.yml以及模板中的参数，它对应ansible-playbook test.yml --extra-vars "host='aa' name='cc' "
            self.variable_manager.extra_vars = extra_vars
            print('playbook 额外参数:%s' % self.variable_manager.extra_vars)

            executor = PlaybookExecutor(
                playbooks=filenames, inventory=self.inventory, variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options, passwords=self.passwords,
            )
            executor._tqm._stdout_callback = self.callback
            executor.run()
        except Exception as e:
            print("run_playbook:%s" % e)

        #    def run_rule(self, hosts, playbookfile, playbooktag):

    #        """
    #        run ansible palybook
    #        """
    #        try:
    #            self.callback = ResultsCollector()
    #            filenames = [playbookfile]  # playbook的路径
    #            print('ymal file path:%s' % filenames)
    #
    #            extra_vars = {}  # 额外的参数 sudoers.yml以及模板中的参数，它对应ansible-playbook test.yml --extra-vars "host='aa' name='cc' "
    #            extra_vars['host'] = hosts
    #            self.variable_manager.extra_vars = extra_vars
    #            print('playbook 额外参数:%s' % self.variable_manager.extra_vars)
    #
    #            self.options = self.options._replace(tags=playbooktag)
    ##            executor = PlaybookExecutor(
    #                playbooks=filenames, inventory=self.inventory, variable_manager=self.variable_manager,
    ##                loader=self.loader,
    #                options=self.options, passwords=self.passwords,
    #            )
    #            executor._tqm._stdout_callback = self.callback
    #            executor.run()
    #        except Exception as e:
    #            print("run_playbook:%s" % e)

    def get_result(self):
        self.results_raw = {'success': {}, 'failed': {}, 'unreachable': {}}
        for host, result in self.callback.host_ok.items():
            self.results_raw['success'][host] = result._result

        for host, result in self.callback.host_failed.items():
            self.results_raw['failed'][host] = result._result['msg']

        for host, result in self.callback.host_unreachable.items():
            self.results_raw['unreachable'][host] = result._result['msg']

        print("Ansible执行结果集:%s" % json.dumps(self.results_raw, indent=4))
        return json.dumps(self.results_raw, indent=4)


if __name__ == '__main__':
    res = {
        "app": {
            "hosts": [
                {
                    'hostname': '192.168.176.112'
                }
            ]
        },
        "one": {
            "hosts": [
                {
                    'username': 'root',
                    'hostname': '192.168.1.1',
                    'ip': '192.168.1.1',
                    'ssh_key': '/usr/local/python36/django/key/local',
                    'password': '12345678',  # password 不能认证
                    'port': 22
                }
            ]
        }
    }
    rapi = MyRunner(res)
    rapi.run('one', 'shell', 'ss -tnl')
    rapi.get_result()