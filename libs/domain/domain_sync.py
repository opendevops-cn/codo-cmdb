#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/5/13
Desc    : 
"""

import os
import time
import requests
import json

### 定义要同步配置的域名，如果为空就代表从系统获取
domain_name_list = []
### 定义API地址
api_url = 'https://demo.opendevops.cn/api/'
domain_uri = '/dns/v2/dns/bind/domain/'
zone_uri = '/dns/v2/dns/bind/zone/'
conf_uri = '/dns/v1/dns/bind/conf/'
auth_key = ''
###############

domain_conf_dir = '/var/named/chroot/etc/'
domain_zone_dir = '/var/named/chroot/var/named/'
domain_bak_dir = '/var/named/chroot/etc/backup'
domain_conf_file = '/var/named/chroot/etc/named.conf'
now_time = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))


def get_domain_list():
    try:
        res = requests.get(api_url + domain_uri, cookies=dict(auth_key=auth_key))
        ret = json.loads(res.content)
        if ret['code'] == 0: return ret['data']
    except Exception as e:
        print('[Error:] 接口连接失败，错误信息：{}'.format(e))
        exit(-2)


def get_zone_list(domain):
    try:
        _params = {'domain': domain}
        res = requests.get(api_url + zone_uri, params=_params, cookies=dict(auth_key=auth_key))
        ret = json.loads(res.content)
        if ret['code'] == 0: return ret['data']
    except Exception as e:
        print('[Error:] 接口连接失败，错误信息：{}'.format(e))
        exit(-2)


def get_conf_list():
    try:
        res = requests.get(api_url + conf_uri, cookies=dict(auth_key=auth_key))
        ret = json.loads(res.content)
        if ret['code'] == 0: return ret['data']
    except Exception as e:
        print('[Error:] 接口连接失败，错误信息：{}'.format(e))
        exit(-2)


def create_zone_default(domain):
    default_head = """\$ORIGIN {}.\n\$TTL 1D\n@ IN SOA  {}. admin.{}. (
                    20180529; serial
                    1D  ; refresh
                    1H  ; retry
                    1W  ; expire
                    3H  ; minimum \n)""".format(domain, domain, domain)
    return default_head


if __name__ == '__main__':
    ### 获取可用域名
    if not domain_name_list:
        domain_name_list = get_domain_list()

    if not domain_name_list:
        print('没有可用域名')
        exit(-1)

    ### 创建临时文件夹
    tmp_dir = '/tmp/domain_zone_file/{}/'.format(now_time)
    os.system('mkdir -p {}'.format(tmp_dir))

    os.system('mkdir -p {}'.format(domain_bak_dir))

    ### 获取配置
    conf_data = get_conf_list()
    conf_init = conf_data.get('conf_init')
    region_dict = conf_data.get('region_init')
    region_dict = json.loads(region_dict)

    if not conf_init or not region_dict:
        print('配置错误')
        exit(-1)

    ### named-checkconf -t /var/named/chroot /etc/named.conf
    named_conf_cmd = "echo '%s' >%s/named.conf" % (conf_init, tmp_dir)
    os.system(named_conf_cmd)

    ### 遍历域名 进行处理
    for domain in domain_name_list:
        ###
        zone_default = create_zone_default(domain)

        ### 生成临时文件
        zone_list = get_zone_list(domain)
        if zone_list:
            for k, v in region_dict.items():
                ### 添加头
                zone_file = "{}{}--{}.zone".format(tmp_dir, domain, v)
                default_cmd = 'echo "{}" > {}'.format(zone_default, zone_file)
                os.system(default_cmd)

                ### 添加主配置
                ### 然后同步过去
                cmd_sed1 = """sed -i  '/\/\/example_%s$/a\\    };' %s/named.conf""" % (v, tmp_dir)
                os.system(cmd_sed1)
                cmd_sed2 = """sed -i  '/\/\/example_%s$/a\\        allow-update { none; };' %snamed.conf""" % (
                    v, tmp_dir)
                os.system(cmd_sed2)

                cmd_sed3 = """sed -i  '/\/\/example_%s$/a\\        file "%s--%s.zone";' %snamed.conf""" % (
                    v, domain, v, tmp_dir)
                os.system(cmd_sed3)

                cmd_sed4 = """sed -i  '/\/\/example_%s$/a\\        type master;' %snamed.conf""" % (
                    v, tmp_dir)
                os.system(cmd_sed4)

                cmd_sed5 = """sed -i  '/\/\/example_%s$/a\\    zone "%s" IN {' %snamed.conf""" % (
                    v, domain, tmp_dir)
                os.system(cmd_sed5)

                ### 添加AAAA
                a_cmd = 'echo "\tIN\tAAAA\t::1" >> {}'.format(zone_file)
                os.system(a_cmd)

            for zone in zone_list:
                region = zone['region']
                region = region_dict.get(region, region)
                mx = zone.get('mx') if zone.get('mx') else ''
                host = zone.get('host') if zone.get('host') else ''
                if zone['type'] == 'NS':
                    cmd = """sed -i '/)/a\\\tIN\tNS\t{}'  {}{}--{}.zone""".format(zone['data'], tmp_dir, domain,
                                                                                  region)
                else:
                    cmd = 'echo "{}\t{}\tIN\t{}\t{}\t{}" >> {}{}--{}.zone'.format(host, zone['ttl'], zone['type'],
                                                                                  mx, zone['data'], tmp_dir,
                                                                                  domain, region)

                os.system(cmd)

    ### 同步主配置 并检查
    ### named-checkconf -t /var/named/chroot /etc/named.conf
    named_conf_cmd = "echo '%s' >%s/named.conf" % (conf_init, tmp_dir)
    os.system(named_conf_cmd)

    cmd_sync = '''/usr/bin/rsync -ahqzt {}named.conf {} -b --backup-dir={}/{} --include "*" '''.format(tmp_dir,
                                                                                                       domain_conf_file,
                                                                                                       domain_bak_dir,
                                                                                                       now_time)
    os.system(cmd_sync)

    #### 检查
    cmd_check_conf = "named-checkconf -t /var/named/chroot /etc/named.conf"
    check_code = os.system(cmd_check_conf)

    if check_code != 0:
        print('[ERROR]', '主配置文件错误')
        cmd_rollback = '''/usr/bin/rsync -ahqzt {}/{}/named.conf {} --include "*" '''.format(domain_bak_dir, now_time,
                                                                                             domain_conf_file)
        os.system(cmd_rollback)
        exit(-2)
    else:
        print('[SUCCESS]', '主配置文件检查完毕')

    ## 再次初始化主配置
    os.system(named_conf_cmd)

    zone_list = os.listdir(tmp_dir)
    for i in range(0, len(zone_list)):
        zone_file = os.path.join(tmp_dir, zone_list[i])
        if os.path.isfile(zone_file):
            zone_file_name = os.path.split(zone_file)[1]
            if zone_file_name != "named.conf":
                domain_name = zone_file_name.split('--')[0]
                cmd_check_zone = "named-checkzone  {}  {}".format(domain_name, zone_file)
                zone_code = os.system(cmd_check_zone)

                if zone_code != 0:
                    print('[ERROR]', cmd_check_zone)
                else:
                    print('[SUCCESS]', cmd_check_zone)
                    ### 添加主配置
                    ### 然后同步过去
                    zone_region = zone_file_name.split('--')[1]
                    zone_region = zone_region.split('.zone')[0]
                    cmd_sed1 = """sed -i  '/\/\/example_%s$/a\\    };' %s/named.conf""" % (zone_region, tmp_dir)
                    os.system(cmd_sed1)
                    cmd_sed2 = """sed -i  '/\/\/example_%s$/a\\        allow-update { none; };' %snamed.conf""" % (
                        zone_region, tmp_dir)
                    os.system(cmd_sed2)

                    cmd_sed3 = """sed -i  '/\/\/example_%s$/a\\        file "%s--%s.zone";' %snamed.conf""" % (
                        zone_region, domain_name, zone_region, tmp_dir)
                    os.system(cmd_sed3)

                    cmd_sed4 = """sed -i  '/\/\/example_%s$/a\\        type master;' %snamed.conf""" % (
                        zone_region, tmp_dir)
                    os.system(cmd_sed4)

                    cmd_sed5 = """sed -i  '/\/\/example_%s$/a\\    zone "%s" IN {' %snamed.conf""" % (
                        zone_region, domain_name, tmp_dir)
                    os.system(cmd_sed5)

                    copy_zone = '\cp -arp {} {}'.format(zone_file, domain_zone_dir)
                    os.system(copy_zone)

    ### 再次同步主配置 并检查
    ### named-checkconf -t /var/named/chroot /etc/named.conf
    cmd_sync = '''/usr/bin/rsync -ahqzt {}named.conf {} -b --backup-dir={}/{} --include "*" '''.format(tmp_dir,
                                                                                                       domain_conf_file,
                                                                                                       domain_bak_dir,
                                                                                                       now_time)
    os.system(cmd_sync)

    #### 检查
    cmd_check_conf = "named-checkconf -t /var/named/chroot /etc/named.conf"
    check_code = os.system(cmd_check_conf)

    if check_code != 0:
        print('[ERROR]', '主配置文件错误')
        cmd_rollback = '''/usr/bin/rsync -ahqzt {}/{}/named.conf {} --include "*" '''.format(domain_bak_dir,
                                                                                             now_time,
                                                                                             domain_conf_file)
        print(cmd_rollback)
        os.system(cmd_rollback)
        exit(-3)
    else:
        print('[SUCCESS]', '主配置文件检查完毕')

    os.system('systemctl reload named-chroot')
