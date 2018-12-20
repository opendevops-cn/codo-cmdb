#_*_coding:utf-8_*_
'''收集linux系统信息'''
import subprocess
import json

def exec_shell(cmd):
    '''执行shell命令函数'''
    sub2 = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = sub2.communicate()
    ret = sub2.returncode
    if ret == 0:
        return stdout.decode('utf-8').strip()
    else:
        return None

def yum_check():
    yum_list = ['python-devel','redhat-lsb','dmidecode']
    for i in yum_list:
        cmd = "rpm -qa | grep %s ; [ $? -ne '0' ] &&  yum install -y %s && echo '%s install ok'"%(i,i,i)
        exec_shell(cmd)

def collect():
    data = {}
    data['sn'] = get_sn()
    data['hostname'] = exec_shell("hostname")
    data['os_distribution'] = get_os_distributor()
    data['os_version'] = exec_shell("cat /etc/redhat-release")

    data['cpu'] = psutil.cpu_count()
    data['memory'] = int(psutil.virtual_memory().total)  / 1024 /1024 /1024 +1
    data['disk'] = get_disk()

    return json.dumps(data)

def get_sn():
    '''获取SN'''
    cmd_res = exec_shell("dmidecode -t system|grep 'Serial Number'")
    cmd_res = cmd_res.strip()
    res_to_list = cmd_res.split(':')
    if len(res_to_list)> 1:#the second one is wanted string
        return res_to_list[1].strip()
    else:
        return ''

def get_os_distributor():
    distributor = exec_shell("lsb_release -a|grep 'Distributor ID'").split(":")
    return distributor[1].strip() if len(distributor)>1 else None

def get_disk():
    size = 0
    all = psutil.disk_partitions()
    for line in all:
        size += psutil.disk_usage(line.mountpoint).total
    return int(size/1024/1024/1024) +2


if __name__=="__main__":
    yum_check()
    try:
        import psutil
    except Exception as e:
        cmd = "which pip ; [ $? -ne '0' ] &&  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python get-pip.py"
        exec_shell(cmd)
        exec_shell('pip install psutil')
        import psutil
    print(collect())
