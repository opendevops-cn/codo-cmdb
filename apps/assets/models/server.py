#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午6:21
'''
from django.db import models

class Server(models.Model):
    PLATFORM_CHOICES = (
        ('Linux', 'Linux'),
        ('Windows', 'Windows'),
        ('Other', 'Other')
    )
    IDC_CHOICES = (
        ('qcloud', '腾讯云'),
        ('aliyun', '阿里云'),
        ('aws', 'AWS'),
        ('other', '其他')
    )
    hostname = models.CharField(unique=True, max_length=128)
    ip = models.CharField(max_length=32, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)

    idc = models.CharField('云厂商',max_length=16, choices=IDC_CHOICES, default='other')
    cpu = models.CharField('CPU',max_length=32, blank=True, null=True)
    memory = models.CharField('内存',max_length=32, blank=True, null=True)
    disk = models.CharField('硬盘',max_length=32, blank=True, null=True)

    os_platform = models.CharField('系统类型',max_length=32, choices=PLATFORM_CHOICES, default='Linux')
    os_distribution = models.CharField('OS厂商',max_length=32,blank=True,null=True)
    os_version = models.CharField('系统版本', max_length=32, null=True, blank=True)

    sn = models.CharField('SN编号',max_length=128, blank=True, null=True)
    comment = models.CharField('备注',max_length=128, blank=True, null=True)
    create_at = models.DateTimeField(blank=True, auto_now_add=True)
    update_at = models.DateTimeField(blank=True, auto_now=True)

    username = models.CharField(max_length=64,null=True, blank=True)
    password = models.CharField(max_length=128,null=True, blank=True)
    admin_user = models.ForeignKey('AdminUser', null=True, blank=True, on_delete=models.PROTECT)  # PROTECT删除关联数据,引发错误ProtectedError
    group = models.ManyToManyField('ServerGroup', null=True, blank=True)
    tag = models.ManyToManyField('Tag', null=True, blank=True)
    public_key = models.BooleanField(default=False,null=True, blank=True)
    def __str__(self):
        return self.hostname
    class Meta:
        verbose_name = '服务器'
        verbose_name_plural = '服务器'
        ordering = ['-id']

class ServerGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)
    #business = models.ForeignKey('所属业务',null=True,blank=True,on_delete=models.SET_NULL)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = '服务器组'
        verbose_name_plural = '服务器组'
        ordering = ['-id']

class ServerAuthRule(models.Model):
    '''资产授权规则'''
    name = models.CharField(max_length=32, unique=True)
    user = models.CharField(max_length=256) # '["yangmv","ss"]'
    server = models.ManyToManyField('Server', null=True, blank=True)
    servergroup = models.ManyToManyField('ServerGroup', null=True, blank=True)
    comment = models.CharField(max_length=160, blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = '资产授权规则'
        verbose_name_plural = '资产授权规则'
        ordering = ['-id']

class Tag(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = 'Tag标签'
        verbose_name_plural = 'Tag标签'
        ordering = ['-id']


class AdminUser(models.Model):
    name = models.CharField(max_length=32)
    username = models.CharField(default='root', max_length=64)
    password = models.CharField(default='', max_length=128)
    private_key = models.TextField(max_length=4096, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    create_at = models.DateTimeField(blank=True, auto_now_add=True)
    update_at = models.DateTimeField(blank=True, auto_now=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = '管理用户'
        verbose_name_plural = '管理用户'
        ordering = ['-id']

# class Business(models.Model):
#     name = models.CharField(max_length=80, unique=True)
#     comment = models.CharField(max_length=160, blank=True, null=True)
#     def __unicode__(self):
#         return self.name
#     class Meta:
#         verbose_name = '业务'
#         verbose_name_plural = '业务'


class Log(models.Model):
    LOGIN_CHOICES = (
        ('web', 'web'),
        ('ssh', 'ssh')
    )
    user = models.CharField('登录用户',max_length=16, null=True)
    host = models.CharField('登录主机',max_length=128, null=True)
    remote_ip = models.CharField('来源IP',max_length=16)
    login_type = models.CharField('登录方式',max_length=8,choices=LOGIN_CHOICES, default='web')
    start_time = models.DateTimeField('登录时间',blank=True, auto_now_add=True)
    end_time = models.DateTimeField('结束时间',null=True)
    record_name = models.CharField('对象存储Name',max_length=32,null=True,blank=True)
    def __str__(self):
        return '{0.host}:[{0.login_type}]'.format(self)
    class Meta:
        verbose_name = '登录日志'
        verbose_name_plural = '登录日志'
        ordering = ['-id']

class TtyLog(models.Model):
    log = models.ForeignKey(Log,null=True,blank=True,on_delete=models.SET_NULL)
    datetime = models.DateTimeField('命令执行时间',auto_now_add=True)
    cmd = models.CharField(max_length=200)
    def __str__(self):
        return self.cmd
    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'

class RecorderLog(models.Model):
    log = models.ForeignKey(Log,null=True,blank=True,on_delete=models.SET_NULL)
    data = models.TextField(null=True,blank=True)
    class Meta:
        verbose_name = '回放日志'
        verbose_name_plural = '回放日志'