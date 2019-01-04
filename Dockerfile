FROM centos:7
# 设置编码
ENV LANG en_US.UTF-8

# 同步时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 1. 安装基本依赖
RUN yum update -y && yum install epel-release -y && yum update -y && yum install wget unzip epel-release nginx  xz gcc automake zlib-devel openssl-devel supervisor  net-tools mariadb-devel groupinstall development  libxslt-devel libxml2-devel libcurl-devel git -y

# 2. 准备python
RUN wget https://www.python.org/ftp/python/3.6.6/Python-3.6.6.tar.xz
RUN xz -d Python-3.6.6.tar.xz && tar xvf Python-3.6.6.tar && cd Python-3.6.6 && ./configure && make && make install

# 3. 复制代码
RUN mkdir -p /var/www/
ADD . /var/www/CMDB/

# 4. 安装pip依赖
RUN pip3 install --user --upgrade pip
RUN pip3 install -r /var/www/CMDB/requirements.txt

# 5.准备配置文件
RUN cp /var/www/CMDB/cmdb-example.conf /var/www/CMDB/cmdb.conf

# 6. 数据初始化
# RUN python3 /var/www/CMDB/manage.py makemigrations
# RUN python3 /var/www/CMDB/manage.py migrate

# 7. 日志
VOLUME /var/log/

# 8. 准备文件
COPY docs/supervisor_cmdb.conf  /etc/supervisord.conf
COPY docs/nginx_cmdb.conf /etc/nginx/conf.d/

EXPOSE 80
CMD ["/usr/bin/supervisord"]

##### build测试
# docker build -t cmdb .