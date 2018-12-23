## CMDB 介绍

- 资产录入,查询,管理
- 资产信息自动搜集
- Web Terminal登录
- 操作审计,录像回放

## 组件栈
- python3.7
- Tornado4.5
- DRF3.9
- MYSQL


## 部署

#### 一 安装依赖
```
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

#### 二 配置
- 配置文件 cmdb.conf
- 配置数据库信息

#### 三 同步数据库
```
mysql -h 127.0.0.1 -u root -p123456 -e "create database cmdb default character set utf8mb4 collate utf8mb4_unicode_ci;"
python3 manage.py makemigrations
python3 manage.py migrate
```

#### 四 Supervisor
```
cat >> /etc/supervisord.conf <<EOF
[program:cmdb]
command=python3 startup.py --port=90%(process_num)02d
process_name=%(program_name)s_%(process_num)02d
numprocs=3
directory=/var/www/CMDB
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/cmdb.log
loglevel=info
logfile_maxbytes=100MB
logfile_backups=3
EOF

supervisorctl update
supervisorctl reload
```

#### 五 Nginx配置
```
upstream  cmdb{
    server  127.0.0.1:9000;
    server  127.0.0.1:9001;
    server  127.0.0.1:9002;
}

location /v1/cmdb/ws/ {
        #proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_pass http://cmdb;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
}

location /api/cmdb/ {
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_pass http://cmdb;
}
```

## 六 前台展示
#### 主机管理
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/01.png)

#### WebTerminal
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/04.png)

#### 授权规则
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/02.png)
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/03.png)

#### 登录日志
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/05.png)

#### 命令统计
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/06.png)

#### 录像回放
![image](https://raw.githubusercontent.com/yangmv/SuperCMDB/master/static/images/07.png)


## License

Everything is [GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html).