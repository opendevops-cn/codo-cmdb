#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/7 10:06
# @Author  : Fred Yangxiaofei
# @File    : push_system_user.py
# @Role    : 多进程推送系统用户，配置免密钥和sudo权限


from libs.ansibleAPI.runner import Runner
from libs.ansibleAPI.myinventory import MyInventory
from libs.db_context import DBContext
from models.server import SystemUser, model_to_dict, Server, AdminUser, AssetErrorLog
from opssdk.operate import MyCryptV2


class PushSystemUser():
    def __init__(self):
        self.sudo = 'echo "" | sudo -S'
        self.exc_list = ['root', 'ubuntu', 'ec2-user', 'centos', 'admin']
        self.err_msg = {"status": False, "ip": "", "msg": ""}
        self.err_list = []
        self.msg = ''

    def run(self, module_name="shell", module_args='', hosts='', remote_user="root", timeout=10, forks=10):
        '''Ansible运行函数'''
        runner = Runner(
            module_name=module_name,
            module_args=module_args,
            remote_user=remote_user,
            pattern="all",
            hosts=hosts,
            forks=forks,
            timeout=timeout,
        )

        result = runner.run()
        return result

    def write_error_log(self):
        """
        将错误日志写入数据库
        :return:
        """
        # 错误日志记录，更新状态
        with DBContext('w') as session:
            for msg in self.err_list:
                ip = msg.get('ip')
                msg = msg.get('msg')
                error_log = '错误信息：{}'.format(msg)
                print(error_log)
                session.query(Server).filter(Server.ip == ip).update({Server.state: 'false'})
                exist_ip = session.query(AssetErrorLog).filter(AssetErrorLog.ip == ip).first()
                if exist_ip:
                    session.query(AssetErrorLog).filter(AssetErrorLog.ip == ip).update(
                        {AssetErrorLog.error_log: error_log})
                else:
                    new_error_log = AssetErrorLog(ip=ip, error_log=error_log)
                    session.add(new_error_log)
            session.commit()

    def get_system_user(self):
        """
        获取所有系统用户
        :return:
        """
        with DBContext('r') as session:
            system_user_list = []
            system_user_data = session.query(SystemUser).all()
            for data in system_user_data:
                data_dict = model_to_dict(data)
                data_dict['create_time'] = str(data_dict['create_time'])
                data_dict['update_time'] = str(data_dict['update_time'])
                system_user_list.append(data_dict)

            return system_user_list

    def get_asset_info(self):
        """
        获取所有可连接资产信息
        :return:
        """

        with DBContext('r') as session:
            # 只拿到登陆用到的IP Port User
            server_list = session.query(Server.ip, Server.port, AdminUser.system_user,
                                        ).outerjoin(AdminUser,
                                                    AdminUser.admin_user == Server.admin_user).filter(
                Server.state == 'true').all()
            return server_list

    def create_system_user(self):
        """
        Ansible API创建系统用户
        :return:
        """
        system_user_list = self.get_system_user()
        connect_server_list = self.get_asset_info()
        # print(connect_server_list)
        # connect_server_list = [('172.16.0.93', 22, 'yanghongfei'), ('172.16.0.219', 22, 'root'),
        #                        ('2.2.2.2', 22, 'root')]
        for host in connect_server_list:
            ip = host[0]
            user = host[2]
            for data in system_user_list:
                system_user = data.get('system_user')

                if system_user in self.exc_list:
                    self.msg = '{}内置用户不能创建，请跳过此类用户：{}'.format(system_user, self.exc_list)
                    return self.msg

                bash_shell = data.get('bash_shell')

                module_args = '{sudo} grep -c {system_user} /etc/passwd >> /dev/null || {sudo} useradd {system_user} -s {bash_shell}; echo ok'.format(
                    sudo=self.sudo, system_user=system_user, bash_shell=bash_shell
                )
                result = self.run("shell", module_args, ip, user)
                print(result)

                if result['dark']:
                    self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                    self.err_list.append(self.err_msg)

        if self.err_list:
            self.write_error_log()

    def configure_keyless(self):
        """
        配置系统用户免密钥登陆
        :return:
        """
        # connect_server_list = [('172.16.0.93', 22, 'root'), ('172.16.0.219', 22, 'root'),
        #                        ('2.2.2.2', 22, 'root')]

        connect_server_list = self.get_asset_info()
        system_user_list = self.get_system_user()

        for host in connect_server_list:
            ip = host[0]
            user = host[2]
            for data in system_user_list:
                mc = MyCryptV2()
                system_user = data.get('system_user')
                _public_key = mc.my_decrypt(data.get('id_rsa_pub'))  # 解密


                module_args = '{sudo} [ ! -d /home/{system_user}/.ssh ]&& ' \
                              '{sudo} mkdir /home/{system_user}/.ssh &&' \
                              '{sudo} chmod 700 /home/{system_user}/.ssh ; ' \
                              '{sudo} [ ! -f /home/{system_user}/.ssh/authorized_keys ]&& ' \
                              '{sudo} touch /home/{system_user}/.ssh/authorized_keys; ' \
                              '{sudo} chown -R {system_user}.{system_user} /home/{system_user}/.ssh ; ' \
                              '{sudo} grep -c "{public_key}" /home/{system_user}/.ssh/authorized_keys >> /dev/null && ' \
                              'echo "is exist public_key, auto pass...." || ' \
                              '{sudo} echo "{public_key}" >> /home/{system_user}/.ssh/authorized_keys && ' \
                              '{sudo} chmod 600 /home/{system_user}/.ssh/authorized_keys && ' \
                              'echo ok'.format(sudo=self.sudo, system_user=system_user, public_key=_public_key)
                # print(module_args)

                result = self.run("shell", module_args, ip, user)

                print(result)
                if result['dark']:
                    self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                    self.err_list.append(self.err_msg)

        if self.err_list:
            self.write_error_log()

    def configure_sudoers(self):
        """
        配置sudo权限
        :return:
        """
        # connect_server_list = [('172.16.0.93', 22, 'yanghongfei'), ('172.16.0.219', 22, 'root')]
        connect_server_list = self.get_asset_info()
        system_user_list = self.get_system_user()

        for host in connect_server_list:
            ip = host[0]
            user = host[2]

            # if user != 'root':
            #     print('配置sudo权限必须是ROOT才可以操作')
            #     return False
            for data in system_user_list:
                system_user = data.get('system_user')
                if system_user == 'root':
                    print('root属于系统内置用户，不能作为系统用户来推送')
                    return

                sudo_list = data.get('sudo_list')
                # 这里还缺少一个update要写，比如用户在前端修改了sudo内容，再次推送进来要更新进去。
                module_args = "{sudo} grep -r ^{system_user} /etc/sudoers  && echo 'is exist sudoers, auto pass... ' || {sudo} sed -i '$a\{system_user} ALL\=(ALL) NOPASSWD: {sudo_list}' /etc/sudoers".format(
                    sudo=self.sudo, system_user=system_user, sudo_list=sudo_list)
                # print(module_args)
                result = self.run("shell", module_args, ip, user)
                print(result)
                if result['dark']:
                    self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                    self.err_list.append(self.err_msg)
        if self.err_list:
            self.write_error_log()

    def update_user_sudo(self, system_user, sudo_list):
        """
        配置系统用户的sudoers，先删除，再添加
        :return:
        """
        # connect_server_list = [('172.16.0.93', 22, 'yanghongfei'), ('172.16.0.219', 22, 'root')]

        if  not self.delete_user_sudo(system_user):
            print('删除用户sudo失败')
            return False
        connect_server_list = self.get_asset_info()
        for host in connect_server_list:
            ip = host[0]
            user = host[2]

            if system_user == 'root':
                print('root属于系统内置用户，不能作为系统用户来推送')
                return False

            module_args = "{sudo} grep -r ^{system_user} /etc/sudoers  && echo 'is exist sudoers, auto pass... ' || {sudo} sed -i '$a\{system_user} ALL\=(ALL) NOPASSWD: {sudo_list}' /etc/sudoers".format(
                sudo=self.sudo, system_user=system_user, sudo_list=sudo_list)
            # print(module_args)
            result = self.run("shell", module_args, ip, user)
            print(result)
            if result['dark']:
                self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                self.err_list.append(self.err_msg)
        if self.err_list:
            self.write_error_log()

    def delete_system_user(self, system_user):
        """
        删除推送的系统用户，排除常见的用户：root ubuntu ec2-user centos admin等
        :return:
        """

        if system_user == 'root':
            msg = 'root用户不能被删除'
            print(msg)
            return msg

        exc_list = ['ubuntu', 'ec2-user', 'centos', 'admin']
        if system_user in exc_list:
            msg = '{}属于系统内置/危险用户，不能被删除'.format(system_user)
            print(msg)
            return msg

        print('start del user')
        connect_server_list = self.get_asset_info()
        # connect_server_list = [('172.16.0.93', 22, 'yanghongfei')]

        for host in connect_server_list:
            ip = host[0]
            user = host[2]
            if system_user == user:
                msg = '删除的用户不能是自己(管理用户)'
                print(msg)
                return msg

            module_args = '{sudo} grep -c "{system_user}" /etc/passwd >> /dev/null && {sudo} userdel -r {system_user} || echo "user is not exist, pass"'.format(
                sudo=self.sudo, system_user=system_user)  # 存在就删除
            result = self.run("shell", module_args, ip, user)
            print(result)
            if result['dark']:
                self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                self.err_list.append(self.err_msg)
        if self.err_list:
            self.write_error_log()
        return self.err_list

    def delete_user_sudo(self, system_user):
        """
        删除用户的sudo权限
        :return:
        """
        if system_user == 'root':
            msg = 'root用户不能被删除'
            print(msg)

            return msg

        exc_list = ['ubuntu', 'ec2-user', 'centos', 'admin']
        if system_user in exc_list:
            msg = '{}属于系统内置/危险用户，不能被删除'.format(system_user)
            print(msg)
            return msg

        print('start del user')
        connect_server_list = [('172.16.0.93', 22, 'yanghongfei')]

        for host in connect_server_list:
            ip = host[0]
            user = host[2]
            if system_user == user:
                msg = '删除的用户不能是自己(管理用户)'
                print(msg)
                return msg

            module_args = "{sudo} sed -i 's/^{system_user}.*//' /etc/sudoers".format(sudo=self.sudo,
                                                                                     system_user=system_user)
            print(module_args)
            result = self.run("shell", module_args, ip, user)
            print(result)
            if result['dark']:
                self.err_msg = {"status": False, "ip": ip, "msg": result['dark'][ip]['msg']}
                self.err_list.append(self.err_msg)
        if self.err_list:
            self.write_error_log()
        return self.err_list

    # def add_user(self):
    #     connect_server_list = [('172.16.0.93', 22, 'root'), ('2.2.2.2', 22, 'root')]
    #     for host in connect_server_list:
    #         ip = host[0]
    #         user = host[2]
    #         module_args1 = 'echo "" | sudo -S cat /etc/sudoers'
    #         module_args = 'name={} shell=/bin/bash'.format('testuser')
    #         result = self.run("shell", module_args,ip,user)
    #
    #         print(result)


def main():
    """
    这是二期规划，跳板用的
    :return:
    """
    obj = PushSystemUser()
    # obj.delete_system_user('sudo_test')
    # obj.delete_user_sudo('sudo_test')
    obj.create_system_user()
    obj.configure_keyless()
    obj.configure_sudoers()


if __name__ == '__main__':
    main()
