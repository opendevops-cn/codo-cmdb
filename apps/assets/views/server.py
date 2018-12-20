#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午3:27
'''
from rest_framework import permissions
from assets.models import server as models
from assets.serializers import server as serializers
from rest_framework import viewsets
from rest_framework import generics
from django.db.models.query import QuerySet
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.assets.cores.server import getHostData,rsyncHostData,rsyncPublicKey,multiAddServer
import json
from libs.cores import initOSS_obj

from rest_framework.pagination import PageNumberPagination
class CustPagination(PageNumberPagination):
    '''自定义分页'''
    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'count': self.page.paginator.count,
        })
    page_size_query_param = 'pageSize'
    page_query_param = 'pageNum'

def paramsInit(params):
    '''params参数处理'''
    params.pop('pageNum',None)
    params.pop('pageSize',None)
    return params

class ServerViewSet(viewsets.ModelViewSet):
    '''主机Server API'''
    def get_queryset(self):
        queryset = self.queryset
        params = paramsInit(self.request.query_params.dict())
        if params:
            queryset = queryset.filter(**params)
        else:
            queryset = queryset.all()
        return queryset
    queryset = models.Server.objects.all()
    pagination_class = CustPagination               #自定义分页
    serializer_class = serializers.ServerSerializer
    permission_classes = (permissions.AllowAny,)    #允许所有访问,权限不在这里做

class ServerGroupViewSet(viewsets.ModelViewSet):
    '''主机组Server_Group API'''
    queryset = models.ServerGroup.objects.all()
    serializer_class = serializers.ServerGroupSerializer
    permission_classes = (permissions.AllowAny,)

class ServerAuthViewSet(viewsets.ModelViewSet):
    '''主机授权规则'''
    queryset = models.ServerAuthRule.objects.all()
    serializer_class = serializers.ServerAuthRuleSerializer
    permission_classes = (permissions.AllowAny,)

class ServerLogViewSet(viewsets.ModelViewSet):
    '''主机登录日志 API'''
    def get_queryset(self):
        queryset = self.queryset
        params = paramsInit(self.request.query_params.dict())
        if params:
            queryset = queryset.filter(**params)
        else:
            queryset = queryset.all()
        return queryset
    queryset = models.Log.objects.all()
    pagination_class = CustPagination
    serializer_class = serializers.ServerLogSerializer
    permission_classes = (permissions.AllowAny,)

class ServerTtyLogViewSet(viewsets.ModelViewSet):
    '''主机操作日志 API'''
    def get_queryset(self):
        log_id = self.request.query_params.get('log_id')
        queryset = self.queryset
        if log_id and isinstance(queryset, QuerySet):
            queryset = queryset.filter(log_id=log_id)
        else:
            queryset = queryset.all()
        return queryset
    queryset = models.TtyLog.objects.all()
    serializer_class = serializers.ServerTtyLogSerializer
    permission_classes = (permissions.AllowAny,)


class ServerRecordLog(APIView):
    '''主机操作回放日志 API'''
    def get(self, request ,format=None):
        log_id = request.query_params.get('log_id')
        ret = dict(status=False,msg=None,data=None)
        if log_id:
            log = models.Log.objects.get(id=log_id)
            if log.record_name:
                # 从OSS获取
                oss_obj = initOSS_obj()
                if oss_obj:
                    data = oss_obj.getObj(log.record_name)
                    ret['data'] = data
            else:
                # 从Mysql获取
                try:
                    data = models.RecorderLog.objects.get(log=log)
                    ret['data'] = data.data
                except Exception as e:
                    pass
            ret['status'] = True
            ret['msg'] = 'Success'
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)

class ServerMultiAdd(APIView):
    def post(self,request, format=None):
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            obj = multiAddServer(request.data)
            obj.start()
            if obj.Error_list:
                ret['msg'] = '%s'%obj.Error_list
            else:
                ret['status'] = True
                ret['msg'] = 'Success'
        else:
            ret['msg'] = 'args type is not list, Please Check!'
        return Response(ret)


class ServerMultiDel(APIView):
    '''批量删除主机'''
    def post(self, request, format=None):
        print(request.data)
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            try:
                models.Server.objects.filter(id__in=request.data).delete()
                ret['status'] = True
                ret['msg'] = 'Success'
            except Exception as e:
                print(e)
                ret['msg'] = str()
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)


class TagViewSet(viewsets.ModelViewSet):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = (permissions.AllowAny,)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = models.AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (permissions.AllowAny,)

class ServerList(generics.ListCreateAPIView):   #ListCreateAPIView get and post
    '''给SS发布用,仅get list需要的信息'''
    def get_queryset(self):
        #重写get_queryset函数,这里要自定义加一些参数
        group_name = self.request.query_params.get('group')
        queryset = self.queryset
        if group_name and isinstance(queryset, QuerySet):
            queryset = queryset.filter(group__name=group_name)
        else:
            #queryset = queryset.all()
            queryset = []
        return queryset

    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerListSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)   #只读

class ServerUpdate(APIView):
    '''资产更新'''
    def post(self, request, format=None):
        print(request.data)
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            hosts = models.Server.objects.filter(id__in=request.data).values('ip')
            ip_list = [item['ip'] for item in hosts]
            obj = getHostData(ip_list)
            if obj.check_file:
                stauts,msg = obj.get_host_data()
                if not stauts:
                    print(msg)
                    ret['msg'] = msg
                else:
                    rsync_cmdb = rsyncHostData(obj.data) #更新资产到CMDB库
                    if rsync_cmdb:
                        ret['msg'] = rsync_cmdb
                    else:
                        ret['status'] = True
                        ret['msg'] = 'Success'
                        ret['data'] = obj.data
            else:
                ret['msg'] = 'sysinfo.py Not Found'
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)


class ServerPublicKey(APIView):
    '''批量推送主机公钥 //需要改成异步非阻塞,不然其他请求会被阻塞,非常慢'''
    def post(self, request, format=None):
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            hosts = models.Server.objects.filter(id__in=request.data)
            obj = rsyncPublicKey(hosts)
            rsync = obj.start()
            if rsync:
                ret['msg'] = json.dumps(rsync,ensure_ascii=False)
            else:
                models.Server.objects.filter(id__in=request.data).update(public_key=True)
                ret['status'] = True
                ret['msg'] = 'Success'
                ret['data'] = request.data
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)




class ServerCheckAuth(APIView):
    '''主机登录认证'''
    def get(self, request ,format=None):
        username = request.query_params.get('username') #当前登录用户
        username = 'yangmingwei' if username == 'yangmv' else username
        sid = request.query_params.get('sid')           #要登录的资产ID
        ret = dict(status=False,msg=None,data=None)
        if username and sid:
            rule_obj = models.ServerAuthRule.objects.filter(user__contains=username)
            for rule in rule_obj:
                server_obj = rule.server.filter(id=sid)
                if server_obj:
                    ret['status'] = True
                    break
                group_obj = rule.servergroup.all()
                for group in group_obj:
                    host = group.server_set.filter(id=sid)
                    if host:
                        ret['status'] = True
                        break
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)