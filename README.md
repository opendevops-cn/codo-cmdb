# CMDB 项目
## 系统依赖
|软件|版本|
|--| --|
|python| >=3.9.5|
|mysql | >=5.7 |
|redis | >=6.2|

## 本地快速上手
### 本地保存如下`docker-compose-local.yml文件`
```
version: '3'
networks:
    codo:
services:
    mysql:
        container_name: mysql
        restart: always
        image: mysql:5.7
        environment:
          MYSQL_ROOT_PASSWORD: codo-cmdb
        ports:
          - 3306:3306

    redis:
        container_name: redis
        image: redis:3.2.11
        command: redis-server --requirepass codo-cmdb
        ports:
          - 6379:6379
```

### 增加本地开发配置`local_settings.py`
```
DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '127.0.0.1')  # 修改
DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', '3306')  # 修改
DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', 'root')  # 修改
DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', 'codo-cmdb')  # 修改
DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', 'codo_cmdb')  # 默认

# 这是从库，读， 一般情况下是一个数据库即可，需要主从读写分离的，请自行建立好服务
READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '127.0.0.1')  # 修改
READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', '3306')  # 修改
READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', 'root')  # 修改
READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', 'codo-cmdb')  # 修改
READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', 'codo_cmdb')  # 默认

# 这是Redis配置信息，默认情况下和codo-admin里面的配置一致
DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', 'localhost')  # 修改
DEFAULT_REDIS_PORT = os.getenv('DEFAULT_REDIS_PORT', '6379')  # 修改
DEFAULT_REDIS_DB = os.getenv('DEFAULT_REDIS_DB', 9)
DEFAULT_REDIS_AUTH = os.getenv('DEFAULT_REDIS_AUTH', True)
DEFAULT_REDIS_CHARSET = os.getenv('DEFAULT_REDIS_CHARSET', 'utf-8')
DEFAULT_REDIS_PASSWORD = os.getenv('DEFAULT_REDIS_PASSWORD', 'codo-cmdb')  # 修改

# consul 为Prometheus提供数据 选填
DEFAULT_CONSUL_HOST = os.getenv('DEFAULT_CONSUL_HOST', '')  # 修改
DEFAULT_CONSUL_PORT = os.getenv('DEFAULT_CONSUL_PORT', 8500)  # 修改
DEFAULT_CONSUL_TOKEN = os.getenv('DEFAULT_CONSUL_TOKEN', None)  # 修改
DEFAULT_CONSUL_SCHEME = os.getenv('DEFAULT_CONSUL_SCHEME', 'http')  # 修改
```
### 安装依赖包
```
pip install -r requirements.txt
pip install -U git+https://github.com/ss1917/codo_sdk.git
```

### 初始化建立数据库
`注意数据库的编码，否则初始化表结构时候会出现编码错误`
```
mysql -h 127.0.0.1 -u root -pcodo-cmdb
>CREATE DATABASE codo_cmdb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```
### 初始化数据库表结构

```
python3 db_sync.py
```

### 启动服务
```
python3 startup.py --service=cmdb --port=8899
```