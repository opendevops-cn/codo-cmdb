FROM python:3.6-slim-buster
# 设置编码
ENV LANG en_US.UTF-8
# 同步时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 1. 安装基础环境
RUN apt update &&\
    apt install -y --no-install-recommends \
      supervisor \
      nginx \
      git \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 python 依赖
RUN pip3 install --no-cache-dir -U git+https://github.com/ss1917/ops_sdk.git
COPY doc/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 3. 复制代码
RUN mkdir -p /var/www/
ADD . /var/www/codo-cmdb


# 4. 初始化生成表结构
#RUN python3 /var/www/kerrigan/db_sync.py

# 5. 日志
VOLUME /var/log/

# 4. 准备文件
COPY doc/nginx_ops.conf /etc/nginx/conf.d/default.conf
COPY doc/supervisor_ops.conf  /etc/supervisord.conf

EXPOSE 80
CMD ["/usr/bin/supervisord"]
