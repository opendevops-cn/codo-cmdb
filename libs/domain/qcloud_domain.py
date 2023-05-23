#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
# from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.dnspod.v20210323 import dnspod_client, models


####
class QCloud:
    def __init__(self, **config):
        self.domain_name = config.get('domain_name')
        self.name = config.get('name')
        self.limit = 3000
        cred = credential.Credential(config.get('access_id'), config.get('access_key'))
        httpProfile = HttpProfile()
        httpProfile.endpoint = "dnspod.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        self.client = dnspod_client.DnspodClient(cred, "", clientProfile)

    def get_domain_records(self, domain_name):
        req = models.DescribeRecordListRequest()
        params = {
            "Domain": domain_name,
            "Limit": self.limit
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个DescribeRecordListResponse的实例，与请求对象对应
        resp = self.client.DescribeRecordList(req)
        return resp.RecordList

    def record_generator(self, domain):
        domain_name = domain.Name
        record_list = self.get_domain_records(domain_name)
        if not record_list: return False
        for record in record_list:
            yield dict(domain_name=domain_name, data_dict=record)

    def add_record(self, *args, **kwargs):
        #
        req = models.CreateRecordRequest()
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        elif kwargs.get('line') in ['oversea', 'Oversea', '境外']:
            line = '境外'
        else:
            line = kwargs.get('line')
        params = {
            "Domain": kwargs.get('domain_name'),
            "SubDomain": kwargs.get('domain_rr'),
            "RecordType": kwargs.get('domain_type'),
            "RecordLine": line,
            "Value": kwargs.get('domain_value'),
            "Weight": kwargs.get('weight'),
            "TTL": int(kwargs.get('domain_ttl', 600)),
            "MX": int(kwargs.get('domain_mx', 0))
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个CreateRecordResponse的实例，与请求对象对应
        resp = self.client.CreateRecord(req)
        # 输出json格式的字符串回包
        if resp.RecordId and isinstance(resp.RecordId, int):
            return str(resp.RecordId)
        else:
            return False

    def update_record(self, *args, **kwargs):
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        elif kwargs.get('line') in ['oversea', 'Oversea', '境外']:
            line = '境外'
        else:
            line = kwargs.get('line')
        params = {
            "Domain": kwargs.get('domain_name'),
            "SubDomain": kwargs.get('domain_rr'),
            "RecordType": kwargs.get('domain_type'),
            "RecordLine": line,
            "Value": kwargs.get('domain_value'),
            "Weight": kwargs.get('weight'),
            "TTL": int(kwargs.get('domain_ttl', 600)),
            "MX": int(kwargs.get('domain_mx', 0)),
            "RecordId": int(kwargs.get('record_id'))
        }
        # print(params)
        req = models.ModifyRecordRequest()
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个ModifyRecordResponse的实例，与请求对象对应
        resp = self.client.ModifyRecord(req)
        if resp.RecordId and isinstance(resp.RecordId, int):
            return True
        else:
            return False

    def remark(self, *args, **kwargs):
        req = models.ModifyRecordRemarkRequest()
        params = {
            "Domain": kwargs.get('domain_name'),
            "RecordId": int(kwargs.get('record_id')),
            "Remark": kwargs.get('remark')
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个ModifyRecordRemarkResponse的实例，与请求对象对应
        resp = self.client.ModifyRecordRemark(req)
        # 输出json格式的字符串回包
        print(resp.to_json_string())
        return True

    def set_record_status(self, *args, **kwargs):
        if kwargs.get('status') in ['开启', '启用', 'Enable', 'enable', 'ENABLE']:
            status = 'ENABLE'
        else:
            status = 'DISABLE'
        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.ModifyRecordStatusRequest()
        params = {
            "Domain": kwargs.get('domain_name'),
            "RecordId": int(kwargs.get('record_id')),
            "Status": status
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个ModifyRecordStatusResponse的实例，与请求对象对应
        resp = self.client.ModifyRecordStatus(req)
        print(resp.to_json_string())
        # 输出json格式的字符串回包
        if resp.RecordId and isinstance(resp.RecordId, int):
            return True
        else:
            return False

    def del_record(self, *args, **kwargs):
        req = models.DeleteRecordRequest()
        params = {
            "Domain": kwargs.get('domain_name'),
            "RecordId": int(kwargs.get('record_id')),
        }
        req.from_json_string(json.dumps(params))
        # 返回的resp是一个DeleteRecordResponse的实例，与请求对象对应
        resp = self.client.DeleteRecord(req)
        print(resp.to_json_string())
        # 输出json格式的字符串回包
        return True

    def describe_domains(self):
        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.DescribeDomainListRequest()
        params = {
            "Limit": self.limit
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个DescribeDomainListResponse的实例，与请求对象对应
        resp = self.client.DescribeDomainList(req)
        return resp.DomainList
