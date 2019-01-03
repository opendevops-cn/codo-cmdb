#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: common.py
@time: 2018-12-2810:39
'''
from rest_framework.response import Response
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