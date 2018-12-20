## CMDB API介绍

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
python3 manage.py makemigrations
python3 manage.py migrate
```

#### 四 Supervisor
```
cat >> /etc/supervisord.conf <<EOF
[program:cmdb]
process_name=cmdb
command=python3 run_server.py
directory=/var/www/CMDB
user=root
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/cmdb.log
loglevel=info
logfile_maxbytes=100MB
EOF

supervisorctl update
supervisorctl reload
```

#### 五 Nginx配置
```
upstream  cmdb{
        server  127.0.0.1:8000;
}

location /api/cmdb/ {
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_pass http://cmdb;
}
```