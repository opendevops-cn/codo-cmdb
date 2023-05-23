#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dnspod import apicn


class DNSPod:
    def __init__(self, **config):
        self.domain_id = config.get('domain_id')
        self.domain_name = config.get('domain_name')
        self.__access_id = config.get('access_id')
        self.__login_token = "{},{}".format(self.__access_id, config.get('access_key'))

    def add_record(self, *args, **kwargs):
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        else:
            line = kwargs.get('line')

        response = apicn.RecordCreate(kwargs.get('domain_rr'), kwargs.get('domain_type'), line,
                                      kwargs.get('domain_value'),
                                      kwargs.get('domain_ttl', 600), mx=int(kwargs.get('domain_mx', 0)),
                                      domain_id=self.domain_id, login_token=self.__login_token)()

        record = response.get("record", {})
        return record.get("id")

    def update_record(self, *args, **kwargs):
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        else:
            line = kwargs.get('line')

        response = apicn.RecordModify(kwargs.get('record_id'), sub_domain=kwargs.get('domain_rr'),
                                      record_type=kwargs.get('domain_type'),
                                      record_line=line, value=kwargs.get('domain_value'),
                                      ttl=int(kwargs.get('domain_ttl', 600)), mx=int(kwargs.get('domain_mx', 0)),
                                      domain_id=self.domain_id, login_token=self.__login_token)()
        return response

    def remark(self, *args, **kwargs):
        return dict(code=0, msg='DNSPod不支持修改')

    def set_record_status(self, *args, **kwargs):
        if kwargs.get('status') in ['开启', '启用', 'Enable', 'enable', 'ENABLE']:
            status = 'enable'
        else:
            status = 'disable'

        response = apicn.RecordStatus(status, record_id=kwargs.get('record_id'), domain_id=self.domain_id,
                                      login_token=self.__login_token)()
        return response

    def del_record(self, *args, **kwargs):
        response = apicn.RecordRemove(record_id=kwargs.get('record_id'), domain_id=self.domain_id,
                                      login_token=self.__login_token)()
        return response

    ######
    def describe_domains(self, *args, **kwargs):
        response = apicn.DomainList(login_token=self.__login_token)()
        return response.get('domains')

    def describe_records(self, *args, **kwargs):
        response = apicn.RecordList(kwargs.get('domain_id'), login_token=self.__login_token)()
        return response.get("records")

    def record_generator(self, **domain):
        record_info_list = self.describe_records(domain_id=domain.get('id'))
        if not record_info_list: return False
        for record in record_info_list:
            yield dict(domain_name=domain.get('name'), data_dict=record)
