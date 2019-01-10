#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: db.py
@time: 2018-12-28 09:56
'''
from django.db import models
import base64

class DBServer(models.Model):
    TYPE_CHOICES = (
        ('MySQL', 'MySQL'),
        ('MariaDB', 'MariaDB'),
        ('MongoDB', 'MongoDB'),
        ('Redis', 'Redis'),
        ('Memcache', 'Memcache'),
        ('Other', 'Other')
    )
    IDC_CHOICES = (
        ('qcloud', '腾讯云'),
        ('aliyun', '阿里云'),
        ('aws', 'AWS'),
        ('other', '其他')
    )
    ROLE_CHOICES = (
        ('master', '主'),
        ('slave', '从'),
        ('backup', '备')
    )
    host = models.CharField(unique=True, max_length=128)
    port = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=64,null=True, blank=True)
    password = models.CharField(max_length=128,null=True, blank=True)

    idc = models.CharField('云厂商',max_length=16, choices=IDC_CHOICES, default='other')
    region = models.CharField('区域',max_length=16, blank=True, null=True)
    db_type = models.CharField('数据库类型',max_length=32, choices=TYPE_CHOICES, default='MySQL')
    db_version = models.CharField('数据库版本', max_length=32, null=True, blank=True)
    comment = models.CharField('备注',max_length=128, blank=True, null=True)

    group = models.ManyToManyField('ServerGroup', null=True, blank=True)
    tag = models.ManyToManyField('Tag', null=True, blank=True)
    role = models.CharField('角色',max_length=16, choices=ROLE_CHOICES, default='master')

    def model_to_dict(self):
        db_info = '%s,,,%s,,,%s,,,%s'%(self.host,self.port,self.username,self.password)
        info = {
            'db_type': self.db_type,
            'db_role': self.role,
            'db_info': base64.b64encode(db_info.encode('utf-8')),
            'db_idc': self.idc,
            'db_region': self.region
        }
        return info

    def __str__(self):
        return self.host
    class Meta:
        verbose_name = '数据库'
        verbose_name_plural = '数据库'
        ordering = ['-id']