#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: book.py
@time: 18/11/19下午3:46
'''

from django.db import models
class Publisher(models.Model):
    '''出版社信息'''
    name = models.CharField('名称',max_length=32,unique=True)
    address = models.CharField('地址',max_length=128)
    operator = models.ForeignKey('auth.User',null=True,blank=True,on_delete=models.SET_NULL)   #操作人
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = '出版社'
        verbose_name_plural = '出版社'

class Book(models.Model):
    title = models.CharField('名称',max_length=32)
    publisher = models.ForeignKey('Publisher',null=True,blank=True,on_delete=models.SET_NULL)
    def __str__(self):
        return self.title
    class Meta:
        verbose_name = '书'
        verbose_name_plural = '书'