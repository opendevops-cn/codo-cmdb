#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: db.py
@time: 2018-12-28 10:37
'''
from rest_framework import permissions
from assets.models import db as models
from assets.serializers import db as serializers
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework import generics
from django.db.models.query import QuerySet
from rest_framework.response import Response
from assets.cores.common import CustPagination,paramsInit
from apps.assets.cores.db import multiAddDB
from django_filters.rest_framework import DjangoFilterBackend

class DBViewSet(viewsets.ModelViewSet):
    '''数据库Server API'''
    def get_queryset(self):
        queryset = self.queryset
        params = paramsInit(self.request.query_params.dict())
        if params:
            queryset = queryset.filter(**params)
        else:
            queryset = queryset.all()
        return queryset
    queryset = models.DBServer.objects.all()
    pagination_class = CustPagination
    serializer_class = serializers.DBSerializer
    filter_backends = (DjangoFilterBackend,)    # 使用过滤器
    filter_fields = ('host',)

class DBMultiAdd(APIView):
    '''批量添加DB'''
    def post(self,request, format=None):
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            obj = multiAddDB(request.data)
            obj.start()
            if obj.Error_list:
                ret['msg'] = '%s'%obj.Error_list
            else:
                ret['status'] = True
                ret['msg'] = 'Success'
        else:
            ret['msg'] = 'args type is not list, Please Check!'
        return Response(ret)

class DBMultiDel(APIView):
    '''批量删除主机'''
    def post(self, request, format=None):
        ret = dict(status=False,msg=None,data=None)
        if request.data and type(request.data) == list:
            try:
                models.DBServer.objects.filter(id__in=request.data).delete()
                ret['status'] = True
                ret['msg'] = 'Success'
            except Exception as e:
                print(e)
                ret['msg'] = str()
        else:
            ret['msg'] = 'args is None, Please Check!'
        return Response(ret)


class DBList(generics.ListCreateAPIView):   #ListCreateAPIView get and post
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

    queryset = models.DBServer.objects.all()
    serializer_class = serializers.DBListSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)