#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: urls.py
@time: 18/11/19下午2:56
'''
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from assets.views.server import *
from assets.views.db import *

app_name = 'assets'

router = DefaultRouter()
router.register('server',ServerViewSet)
router.register('server_group',ServerGroupViewSet)
router.register('server_auth',ServerAuthViewSet)
router.register('server_log',ServerLogViewSet)
router.register('server_ttylog',ServerTtyLogViewSet)
router.register('adm_user',AdminUserViewSet)
router.register('db',DBViewSet)
router.register('tag',TagViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('server_update/',ServerUpdate.as_view(),name='server_update'),  #资产更新
    path('server_publickey/',ServerPublicKey.as_view(),name='server_publickey'),  #推送公钥
    path('server_recordlog/',ServerRecordLog.as_view(),name='server_recordlog'),  #回放日志
    path('server_multiadd/',ServerMultiAdd.as_view(),name='server_multiadd'),  #批量添加主机
    path('server_multidel/',ServerMultiDel.as_view(),name='server_multidel'),  #批量删除主机
    path('server_check_auth/',ServerCheckAuth.as_view(),name='server_check_auth'),      #主机登录认证
    path('db_multiadd/',DBMultiAdd.as_view(),name='db_multiadd'),  #批量添加DB
    path('db_multidel/',DBMultiDel.as_view(),name='db_multidel'),  #批量删除DB

    path('server_list/',ServerList.as_view(),name='server_list'),
    path('db_list/',DBList.as_view(),name='db_list'),
    path('all_server/',AllServerList.as_view(),name='all_server'), #获取Server和DB,发布专用
]

urlpatterns += router.urls