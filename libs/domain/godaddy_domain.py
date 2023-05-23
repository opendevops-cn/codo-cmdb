#!/usr/bin/env python
# -*- coding: utf-8 -*-

### pip install godaddypy
from shortuuid import uuid
from godaddypy import Client, Account


class GoDaddy:
    def __init__(self, **config):
        self.domain_name = config.get('domain_name')
        self.alias_name = config.get('alias_name')
        self.__access_id = config.get('access_id')
        self.acct = Account(api_key=self.__access_id, api_secret=config.get('access_key'))
        self.__client = Client(self.acct)

    def describe_record(self, *args, **kwargs):
        return self.__client.get_records(kwargs.get('domain_name'), record_type=kwargs.get('domain_type'),
                                         name=kwargs.get('domain_rr'))

    def add_record(self, *args, **kwargs):
        params = dict(
            name=kwargs.get('domain_rr'),
            data=kwargs.get('domain_value'),
            type=kwargs.get('domain_type'),
            ttl=int(kwargs.get('domain_ttl'))
        )

        result_data = self.__client.add_record(kwargs.get('domain_name'), params)
        if result_data is True:
            result_data = str(uuid())
        return result_data

    def update_record(self, *args, **kwargs):
        params = dict(
            name=kwargs.get('domain_rr'),
            data=kwargs.get('domain_value'),
            type=kwargs.get('domain_type'),
            ttl=int(kwargs.get('domain_ttl'))
        )
        result_data = self.__client.update_record(kwargs.get('domain_name'), params)
        return result_data

    def remark(self, *args, **kwargs):
        return dict(code=0, msg='GoDaddy不支持修改')

    def set_record_status(self, *args, **kwargs):
        if kwargs.get('status') in ['开启', '启用', 'Enable', 'enable', 'ENABLE']:
            self.add_record(**kwargs)
        elif kwargs.get('status') in ['暂停', '禁用', 'disable']:
            self.del_record(**kwargs)
        else:
            return False
        return True

    def del_record(self, *args, **kwargs):
        domain_name = kwargs.get('domain_name')
        name = kwargs.get('domain_rr')
        record_type = kwargs.get('domain_type')
        result_data = self.__client.delete_records(domain_name, name, record_type=record_type)
        return result_data

    def describe_domains(self):
        domain_list = self.__client.get_domains()
        if not domain_list: return False
        for domain in domain_list:
            domain_info_list = self.__client.get_domain_info(domain)
            domain_info_list['records'] = len(self.__client.get_records(domain))
            yield domain_info_list

    def record_generator(self, **domain):
        record_info_list = self.__client.get_records(domain.get('domain'))
        if not record_info_list: return False
        for record in record_info_list:
            yield dict(domain_name=domain.get('domain'), data_dict=record)
