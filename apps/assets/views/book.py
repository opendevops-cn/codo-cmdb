#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午3:27
'''
from rest_framework import generics
from rest_framework import permissions
from assets.models import book as models
from assets.serializers import book as serializers
from assets.permissions import IsOwnerOrReadOnly
from rest_framework import viewsets

########################### 通用混合类 #######################################
class PublisherList(generics.ListCreateAPIView):
    '''列出所有出版社,或者新增出版社'''
    queryset = models.Publisher.objects.all()
    serializer_class = serializers.PublisherSerializer
    #permission_classes = ()     #permission_classes留空的话,用户不登录也可以进行访问
    #permission_classes = (permissions.IsAuthenticated)     #基础认证,必须登录才可以访问
    permission_classes = (permissions.IsAuthenticated,IsOwnerOrReadOnly)    #自定义认证,只有录入者才允许写入
    def perform_create(self,serializer):
        #因为post的时候没有operator字段,所以这里要把operator和user关联起来
        serializer.save(operator=self.request.user)

class PublisherDetail(generics.RetrieveUpdateDestroyAPIView):
    '''出版社详情列出,修改,删除'''
    queryset = models.Publisher.objects.all()
    serializer_class = serializers.PublisherSerializer
    permission_classes = (permissions.IsAuthenticated,IsOwnerOrReadOnly)


# class BookList(generics.ListCreateAPIView):
#     '''列出所有书,或者新增书'''
#     queryset = models.Book.objects.all()
#     serializer_class = serializers.BookSerializer
#     permission_classes = (permissions.IsAuthenticatedOrReadOnly,)   #此处一定要有逗号
#
# class BookDetail(generics.RetrieveUpdateDestroyAPIView):
#     '''书籍详情列出,修改,删除'''
#     queryset = models.Book.objects.all()
#     serializer_class = serializers.BookSerializer
#     permission_classes = (permissions.IsAuthenticatedOrReadOnly,)   #此处一定要有逗号



########################### ViewSet #######################################
class BookViewSet(viewsets.ModelViewSet):
    queryset = models.Book.objects.all()
    serializer_class = serializers.BookSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)