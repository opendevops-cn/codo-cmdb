#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: asset.py
@time: 18/11/19下午3:27
'''
from rest_framework import serializers
from assets.models.book import Book,Publisher

class PublisherSerializer(serializers.ModelSerializer):
    operator = serializers.ReadOnlyField(source='operator.username')
    class Meta:
        model = Publisher
        fields = ('id','name','address','operator')
        #fields = '__all__'

class BookSerializer(serializers.ModelSerializer):
    # publisher = serializers.StringRelatedField(source='publisher.name')                              #把出版社ID转换成对应的出版社名字
    # publisher = serializers.HyperlinkedIdentityField(view_name='publisher-detail', format='html')      #超链接的形式展示出版社信息
    class Meta:
        model = Book
        fields = ('id','title','publisher')
        #fields = '__all__'
