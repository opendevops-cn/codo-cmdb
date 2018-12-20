#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: book.py
@time: 18/11/19下午4:14
'''
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    '''自定义权限，只有创建者才能编辑'''
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求
        # 所以总是允许GET,HEAD或OPTIONS请求
        if request.method in permissions.SAFE_METHODS:
            return True
        # 只有该出版社的录入者才允许写权限
        return obj.operator == request.user