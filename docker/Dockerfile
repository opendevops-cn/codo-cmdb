FROM registry.cn-hangzhou.aliyuncs.com/sourcegarden/python:centos7-3.6

RUN mkdir -p /var/www/
ADD ../ /var/www/codo-cmdb/

RUN pip3 install -r /var/www/codo-cmdb/doc/requirements.txt

VOLUME /var/log/

COPY nginx_ops.conf /etc/nginx/conf.d/default.conf
COPY supervisor_ops.conf  /etc/supervisord.conf

EXPOSE 80
CMD ["/usr/bin/supervisord"]