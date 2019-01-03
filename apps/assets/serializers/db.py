#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: db.py
@time: 2018-12-28 10:41
'''
from rest_framework import serializers
from assets.models.db import *

class DBSerializer(serializers.ModelSerializer):
    def get_group_name(self,obj):
        try:
            return [item.name for item in obj]
        except Exception as e:
            return {}
    def get_tag_name(self,obj):
        try:
            return [item.name for item in obj]
        except Exception as e:
            return {}
    def to_representation(self, instance):
        '''重写to_representation方法'''
        ret = super(DBSerializer, self).to_representation(instance)
        ret['group_name'] = self.get_group_name(instance.group.all())
        ret['tag_name'] = self.get_tag_name(instance.tag.all())
        ret['idc_name'] = instance.get_idc_display()
        ret['role_name'] = instance.get_role_display()
        return ret
    class Meta:
        model = DBServer
        fields = '__all__'

class DBListSerializer(serializers.ModelSerializer):
    def get_tag_name(self,obj):
        try:
            return [item.name for item in obj]
        except Exception as e:
            return {}
    def get_group_name(self,obj):
        try:
            return [item.name for item in obj]
        except Exception as e:
            return {}
    def to_representation(self, instance):
        ret = super(DBListSerializer, self).to_representation(instance)
        ret['tag'] = self.get_tag_name(instance.tag.all())
        ret['group'] = self.get_group_name(instance.group.all())
        return ret
    class Meta:
        model = DBServer
        fields = ('host','port','username','tag',)