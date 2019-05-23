FROM centos:7
# 设置编码
ENV LANG en_US.UTF-8
# 同步时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 1. 安装基本依赖
RUN yum update -y && yum install epel-release -y && yum update -y && yum install wget unzip epel-release nginx  xz gcc automake zlib-devel openssl-devel supervisor  groupinstall development  libxslt-devel libxml2-devel libcurl-devel git -y
#WORKDIR /var/www/

# 2. 准备python
RUN wget https://www.python.org/ftp/python/3.6.6/Python-3.6.6.tar.xz
RUN xz -d Python-3.6.6.tar.xz && tar xvf Python-3.6.6.tar && cd Python-3.6.6 && ./configure && make && make install

# 3. 安装websdk
RUN pip3 install --upgrade pip
RUN pip3 install -U git+https://github.com/ss1917/ops_sdk.git
# 4. 复制代码
RUN mkdir -p /var/www/
ADD . /var/www/codo-cmdb/

# 5. 安装pip依赖
RUN pip3 install -r /var/www/codo-cmdb/doc/requirements.txt

# 6. 日志
VOLUME /var/log/

# 7. 准备文件
COPY doc/nginx_ops.conf /etc/nginx/conf.d/default.conf
COPY doc/supervisor_ops.conf  /etc/supervisord.conf

EXPOSE 80
CMD ["/usr/bin/supervisord"]