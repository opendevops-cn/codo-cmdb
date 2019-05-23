#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/10 13:14
# @Author  : Fred Yangxiaofei
# @File    : ansible_setup.py
# @Role    : 获取资产测试


from libs.ansibleAPI.runner import Runner
from libs.common import M2human, exec_thread


def get_host_info(server_list):
    if not isinstance(server_list, list):
        raise ValueError()

    for host in server_list:
        ip = host[0]
        user = host[2]

        runner = Runner(
            module_name="setup",
            module_args="",
            remote_user=user,
            pattern="all",
            hosts=ip
        )

        result = runner.run()

        if result['dark']:
            msg = {
                ip: {
                    'status': False,
                    'msg': result['dark'][ip]['msg']
                }
            }
            return msg

        else:
            asset_data = {
                ip: {
                    'status': True,
                    'msg': '获取资产成功',
                }
            }  # ip为key 数据为value
            # print(result['contacted'][ip])
            # 资产信息

            # SN
            try:
                sn = result['contacted'][ip]['ansible_facts']['ansible_product_serial']
            except KeyError:
                sn = 'Null'
            # 主机名
            try:
                host_name = result['contacted'][ip]['ansible_facts']['ansible_hostname']
            except KeyError:
                host_name = 'Null'

            # cpu型号
            try:
                cpu = result['contacted'][ip]['ansible_facts']['ansible_processor'][-1]
            except KeyError:
                cpu = 'Null'

            # CPU核心数
            try:
                cpu_cores = result['contacted'][ip]['ansible_facts']['ansible_processor_vcpus']
            except KeyError:
                cpu_cores = 'Null'

            # 物理内存容量
            try:
                memory = result['contacted'][ip]['ansible_facts']['ansible_memtotal_mb']
            except KeyError:
                memory = 'Null'

            # 磁盘容量
            try:
                disk = sum([int(result['contacted'][ip]['ansible_facts']["ansible_devices"][i]["sectors"]) * \
                                  int(result['contacted'][ip]['ansible_facts']["ansible_devices"][i][
                                          "sectorsize"]) / 1024 / 1024 / 1024 \
                                  for i in result['contacted'][ip]['ansible_facts']["ansible_devices"] if
                                  i[0:2] in ("sd", "ss", "vd", "xv")])
            except KeyError:
                disk = 'Null'

            # 磁盘mount
            # disk_mount = str(
            #     [{"mount": i["mount"], "size": i["size_total"] / 1024 / 1024 / 1024} for i in result['contacted'][ip]['ansible_facts']["ansible_mounts"]])
            #
            # print(disk_mount)

            # 服务器类型
            try:
                os_type = " ".join((result['contacted'][ip]['ansible_facts']["ansible_distribution"],
                                    result['contacted'][ip]['ansible_facts']["ansible_distribution_version"]))
            except KeyError:
                os_type = 'Null'

            try:

                os_kernel = result['contacted'][ip]['ansible_facts']['ansible_kernel']
            except KeyError:
                os_kernel = 'Null'

            asset_data[ip]['sn'] = sn
            asset_data[ip]['host_name'] = host_name
            asset_data[ip]['cpu'] = cpu
            asset_data[ip]['cpu_cores'] = cpu_cores
            asset_data[ip]['memory'] = M2human(memory)
            asset_data[ip]['disk'] = '{disk}G'.format(disk=disk)
            asset_data[ip]['os_type'] = os_type
            asset_data[ip]['os_kernel'] = os_kernel

        print(asset_data)
        return asset_data

def get_server_sysinfo(server_list):
    """
    多进程采集机器信息
    :param server_list: 主机列表
    :return:
    """
    # print(list(exec_thread(func=get_host_info, iterable1=server_list)))
    return list(exec_thread(func=get_host_info, iterable1=server_list))


if __name__ == '__main__':
    server_list = [[('111.231.79.132', 22, 'root')], [('172.16.0.234', 22, 'root')]]
    get_server_sysinfo(server_list)
