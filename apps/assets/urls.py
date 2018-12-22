#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: urls.py
@time: 18/11/19下午2:56
'''
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from assets.views.book import *
from assets.views.server import *

app_name = 'assets'

router = DefaultRouter()
router.register('server',ServerViewSet)
router.register('server_group',ServerGroupViewSet)
router.register('server_auth',ServerAuthViewSet)
router.register('server_log',ServerLogViewSet)
router.register('server_ttylog',ServerTtyLogViewSet)
router.register('tag',TagViewSet)
router.register('adm_user',AdminUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('publishers/',PublisherList.as_view(),name='publisher-list'),
    path('publishers/<int:pk>/', PublisherDetail.as_view(),name='publisher-detail'),
    path('server_list/',ServerList.as_view(),name='server_list'),  #给ss发布用
    path('server_update/',ServerUpdate.as_view(),name='server_update'),  #资产更新
    path('server_publickey/',ServerPublicKey.as_view(),name='server_publickey'),  #推送公钥
    path('server_recordlog/',ServerRecordLog.as_view(),name='server_recordlog'),  #回放日志
    path('server_multiadd/',ServerMultiAdd.as_view(),name='server_multiadd'),  #批量添加主机
    path('server_multidel/',ServerMultiDel.as_view(),name='server_multidel'),  #批量删除主机
    path('server_check_auth/',ServerCheckAuth.as_view(),name='server_check_auth'),      #主机登录认证
]

urlpatterns += router.urls