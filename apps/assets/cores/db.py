#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: db.py
@time: 2018-12-28 13:17
'''
from assets.models import db as models

class multiAddDB():
    def __init__(self,data):
        self.data = data
        self.Error_list = {}
    def start(self):
        for line in self.data:
            data = line.strip().split(' ')
            print(data)
            if len(data) >= 4:
                try:
                    models.DBServer.objects.create(
                        host=data[0],port=data[1],username=data[2],password=data[3])
                except Exception as e:
                    print(e)
                    self.Error_list[data[0]] = str(e)
            else:
                self.Error_list[data[0]] = '提交的格式不正确'
        print('err->',self.Error_list)