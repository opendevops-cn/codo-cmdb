#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.DescribeDomainsRequest import DescribeDomainsRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordInfoRequest import DescribeDomainRecordInfoRequest
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DeleteDomainRecordRequest import DeleteDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRemarkRequest import UpdateDomainRecordRemarkRequest
from aliyunsdkalidns.request.v20150109.SetDomainRecordStatusRequest import SetDomainRecordStatusRequest


class AliYun:
    def __init__(self, **config):
        self.access_id = config.get('access_id')
        self.domain_name = config.get('domain_name')
        self.alias_name = config.get('alias_name')
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：500 默认值：20
        self.__client = AcsClient(self.access_id, config.get('access_key'), 'cn-hangzhou')

    def describe_record(self, *args, **kwargs):
        request = DescribeDomainRecordInfoRequest()
        request.set_accept_format('json')

        request.set_RecordId(kwargs.get('record_id'))
        response = self.__client.do_action_with_exception(request)
        return str(response, encoding='utf-8')

    def add_record(self, *args, **kwargs):
        request = AddDomainRecordRequest()
        request.set_accept_format('json')

        request.set_DomainName(kwargs.get('domain_name'))
        request.set_RR(kwargs.get('domain_rr'))
        request.set_Type(kwargs.get('domain_type'))
        request.set_Value(kwargs.get('domain_value'))
        request.set_TTL(kwargs.get('domain_ttl'))
        request.set_Line(kwargs.get('line'))
        response = self.__client.do_action_with_exception(request)
        return json.loads(str(response, encoding="utf8")).get('RecordId')

    def update_record(self, *args, **kwargs):
        request = UpdateDomainRecordRequest()
        request.set_accept_format('json')

        request.set_RecordId(kwargs.get('record_id'))
        request.set_RR(kwargs.get('domain_rr'))
        request.set_Type(kwargs.get('domain_type'))
        request.set_Value(kwargs.get('domain_value'))
        request.set_TTL(kwargs.get('domain_ttl'))
        request.set_Line(kwargs.get('line'))

        response = self.__client.do_action_with_exception(request)
        return json.loads(str(response, encoding="utf8")).get('RecordId')

    def remark(self, *args, **kwargs):
        request = UpdateDomainRecordRemarkRequest()
        request.set_accept_format('json')
        request.set_RecordId(kwargs.get('record_id'))
        request.set_Remark(kwargs.get('remark'))

        response = self.__client.do_action_with_exception(request)
        return str(response, encoding='utf-8')

    def set_record_status(self, *args, **kwargs):
        if kwargs.get('status') in ['开启', '启用', 'Enable', 'enable', 'ENABLE']:
            status = 'Enable'
        else:
            status = 'Disable'

        request = SetDomainRecordStatusRequest()
        request.set_accept_format('json')

        request.set_RecordId(kwargs.get('record_id'))
        request.set_Status(status)

        response = self.__client.do_action_with_exception(request)
        return json.loads(str(response, encoding="utf8")).get('RecordId')

    def del_record(self, *args, **kwargs):
        request = DeleteDomainRecordRequest()
        request.set_accept_format('json')
        request.set_RecordId(kwargs.get('record_id'))

        response = self.__client.do_action_with_exception(request)
        return str(response, encoding='utf-8')

    ######
    def get_domain_page(self, page_number=1):
        request = DescribeDomainsRequest()
        request.set_accept_format('json')
        request.set_PageNumber(page_number)
        request.set_PageSize(self.page_size)
        response = self.__client.do_action_with_exception(request)
        return json.loads(str(response, encoding="utf8"))['Domains']

    def get_all_domains(self):
        page_num = 1
        while True:
            data = self.get_domain_page(page_num)
            if not data or 'Domain' not in data: break
            if not data['Domain']: break
            page_num += 1
            row = data['Domain']
            if not row: break
            yield row

    def get_record_page(self, domain_name, page_number=1):
        request = DescribeDomainRecordsRequest()
        request.set_accept_format('json')
        request.set_PageNumber(page_number)
        request.set_PageSize(self.page_size)
        request.set_DomainName(domain_name)
        response = self.__client.do_action_with_exception(request)
        return json.loads(str(response, encoding="utf8"))['DomainRecords']

    def get_domain_records(self, domain_name):
        page_num = 1
        while True:
            data = self.get_record_page(domain_name, page_num)
            if not data or 'Record' not in data: break
            if not data['Record']: break
            page_num += 1
            row = data['Record']
            if not row: break
            yield row

    def describe_domains(self):
        domain_info_list = self.get_all_domains()
        if not domain_info_list: return False

        for data_set in domain_info_list:
            for domain in data_set:
                yield domain

    def record_generator(self, **domain):
        record_info_list = self.get_domain_records(domain.get('DomainName'))
        if not record_info_list: return False
        for record_list in record_info_list:
            for record in record_list:
                yield dict(domain_name=domain.get('DomainName'), data_dict=record)
