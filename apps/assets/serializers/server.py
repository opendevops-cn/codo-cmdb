#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午3:27
'''
from rest_framework import serializers
from assets.models.server import *
from assets.models.db import *
import time

class ServerSerializer(serializers.ModelSerializer):
    #group = serializers.StringRelatedField(many=True)                              #把grouID转换成对应的groupName
    #admin_user = serializers.StringRelatedField(source='admin_user.username')
    admin_user_name = serializers.StringRelatedField(source='admin_user.name')
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
    def get_adm_user(self,obj):
        try:
            return obj.id
        except Exception as e:
            return ''
    def to_representation(self, instance):
        '''重写to_representation方法'''
        ret = super(ServerSerializer, self).to_representation(instance)
        ret['group_name'] = self.get_group_name(instance.group.all())
        ret['tag_name'] = self.get_tag_name(instance.tag.all())
        ret['idc_name'] = instance.get_idc_display()
        #ret['admin_user'] = self.get_adm_user(instance.admin_user)
        return ret

    class Meta:
        model = Server
        #fields = ('id','title','publisher')
        fields = '__all__'

class ServerGroupSerializer(serializers.ModelSerializer):
    server_set = serializers.PrimaryKeyRelatedField(many=True,queryset=Server.objects.all())  #反向查询该Group被哪些Server做了关联,读写
    # server_set = serializers.StringRelatedField(many=True)  #反向查询该Group被哪些Server做了关联,只读
    dbserver_set = serializers.PrimaryKeyRelatedField(many=True,queryset=DBServer.objects.all())

    def get_server_name(self,obj):
        try:
            return [item.hostname for item in obj]
        except Exception as e:
            return []
    def get_db_name(self,obj):
        try:
            return [item.host for item in obj]
        except Exception as e:
            return []
    def to_representation(self, instance):
        ret = super(ServerGroupSerializer, self).to_representation(instance)
        ret['server_set_name'] = self.get_server_name(instance.server_set.all())
        ret['dbserver_set_name'] = self.get_db_name(instance.dbserver_set.all())
        return ret

    class Meta:
        model = ServerGroup
        fields = '__all__'

class ServerAuthRuleSerializer(serializers.ModelSerializer):
    def get_server_name(self,obj):
        try:
            return [item.hostname for item in obj]
        except Exception as e:
            return {}
    def get_group_name(self,obj):
        try:
            return [item.name for item in obj]
        except Exception as e:
            return {}
    def to_representation(self, instance):
        ret = super(ServerAuthRuleSerializer, self).to_representation(instance)
        ret['server_display'] = self.get_server_name(instance.server.all())
        ret['servergroup_display'] = self.get_group_name(instance.servergroup.all())
        return ret
    class Meta:
        model = ServerAuthRule
        fields = '__all__'

class ServerLogSerializer(serializers.ModelSerializer):
    start_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    end_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    def get_use_time(self,obj):
        try:
            start_time = time.mktime(obj.start_time.timetuple())
            stop_time = time.mktime(obj.end_time.timetuple())
            use_time = (stop_time-start_time)/60
            return '%.f分钟'%use_time
        except Exception as e:
            print(e)
            return ''
    def to_representation(self, instance):
        ret = super(ServerLogSerializer, self).to_representation(instance)
        ret['use_time'] = self.get_use_time(instance)
        return ret
    class Meta:
        model = Log
        fields = '__all__'

class ServerTtyLogSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    class Meta:
        model = TtyLog
        fields = '__all__'

class ServerRecordLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecorderLog
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    server_set = serializers.PrimaryKeyRelatedField(many=True,queryset=Server.objects.all())
    dbserver_set = serializers.PrimaryKeyRelatedField(many=True,queryset=DBServer.objects.all())
    class Meta:
        model = Tag
        fields = '__all__'

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = '__all__'

class ServerListSerializer(serializers.ModelSerializer):
    #admin_user = serializers.StringRelatedField(source='admin_user.username')
    def get_adm_user(self,obj):
        try:
            if obj.username:
                return obj.username
            else:
                return obj.admin_user.username
        except Exception as e:
            return ''
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
        ret = super(ServerListSerializer, self).to_representation(instance)
        ret['tag'] = self.get_tag_name(instance.tag.all())
        ret['group'] = self.get_group_name(instance.group.all())
        ret['username'] = self.get_adm_user(instance)
        return ret
    class Meta:
        model = Server
        fields = ('hostname','ip','port','username','tag','group')