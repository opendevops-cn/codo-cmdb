#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午3:27
'''
from rest_framework import permissions
from assets.models import server as models
from assets.models.db import DBServer
from assets.serializers import server as serializers
from rest_framework import viewsets
from rest_framework import generics
from django.db.models.query import QuerySet
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.assets.cores.server import getHostData,rsyncHostData,rsyncPublicKey,multiAddServer
import json
import jwt
from libs.cores import initOSS_obj
from assets.cores.common import CustPagination,paramsInit

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
    filter_backends = (DjangoFilterBackend,)    # 使用过滤器
    filter_fields = ('name',)

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
                    record_date = log.start_time.strftime('%Y%m%d')
                    data = oss_obj.getObj(log.record_name,record_date)
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
    '''批量添加主机'''
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
    filter_backends = (DjangoFilterBackend,)    # 使用过滤器
    filter_fields = ('name',)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = models.AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (permissions.AllowAny,)

class ServerList(generics.ListCreateAPIView):   #ListCreateAPIView get and post
    '''给SS发布用,仅get list需要的信息'''
    def get_queryset(self):
        #重写get_queryset函数,这里要自定义加一些参数
        group_name = self.request.query_params.get('group')
        tag_name = self.request.query_params.get('tag')
        queryset = self.queryset
        if group_name and isinstance(queryset, QuerySet):
            queryset = queryset.filter(group__name=group_name)
        elif tag_name and isinstance(queryset, QuerySet):
            queryset = queryset.filter(tag__name=tag_name)
        else:
            #queryset = queryset.all()
            queryset = []
        return queryset

    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerListSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)   #只读


class AllServerList(APIView):
    '''根据 tag或group查询所有Server包含DBServer'''
    def get(self, request):
        ret = dict(status='-1',msg=None,data=None)
        group = request.GET.get('group')
        tag = request.GET.get('tag')
        if group or tag:
            if group:
                server_obj = models.Server.objects.filter(group__name=group)
                db_obj = DBServer.objects.filter(group__name=group)
            else:
                server_obj = models.Server.objects.filter(tag__name=group)
                db_obj = DBServer.objects.filter(tag__name=group)
            server_list = [item.model_to_dict() for item in server_obj]
            db_list = [item.model_to_dict() for item in db_obj]
            ret['data'] = {
                'server_list': server_list,
                'db_list': db_list
            }
            ret['status'] = 0
            ret['msg'] = '数据获取成功'
        else:
            ret['msg'] = '请输入必要参数'
        return Response(ret)

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
            if obj.check_rsa:
                rsync = obj.start()
                if rsync:
                    ret['msg'] = json.dumps(rsync,ensure_ascii=False)
                else:
                    models.Server.objects.filter(id__in=request.data).update(public_key=True)
                    ret['status'] = True
                    ret['msg'] = 'Success'
                    ret['data'] = request.data
            else:
                ret['msg'] = '秘钥对生成失败,请手工生成秘钥对'
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)




class ServerCheckAuth(APIView):
    '''主机登录认证'''
    def get(self, request ,format=None):
        sid = request.query_params.get('sid')           #要登录的资产ID
        ret = dict(status=False,msg=None,data=None)
        if sid:
            # username = request.query_params.get('username')
            # 改用后端验证登录用户信息
            auth_key = request.COOKIES.get('auth_key', None)
            # print(auth_key)
            if not auth_key:return Response('未登陆',status=401)
            user_info = jwt.decode(auth_key, verify=False)
            username = user_info['data']['username'] if 'data' in user_info else 'guest'
            username = 'yangmingwei' if username == 'yangmv' else username
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
        print(ret)
        return Response(ret)