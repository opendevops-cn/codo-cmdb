### 更新

- beta0.3.1 支持了华为云资产获取

```
前端更换成最新的前端、更改表结构即可
ALTER TABLE `asset_configs` ADD `project_id` VARCHAR(120) NOT NULL ;
ALTER TABLE `asset_configs` ADD `huawei_cloud` VARCHAR(120) NOT NULL ;
ALTER TABLE `asset_configs` ADD `huawei_instance_id` VARCHAR(120) NOT NULL ;

#若是不想更改表结构、或者是第一次部署的同学，默认docker exec -ti cmdb_codo_cmdb_1 /usr/local/bin/python3 /var/www/codo-cmdb/db_sync.py 初始化表结构即可
```
