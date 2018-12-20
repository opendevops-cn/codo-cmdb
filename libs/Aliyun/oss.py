#!/usr/bin/env python
#encoding:utf-8
'''
@author: yangmv
@file: oss_test.py
@time: 18/12/13上午10:17
'''

import oss2
import datetime
import shortuuid

class OSSApi():
    def __init__(self,key,secret,region,bucket_name,base_dir):
        self.key = key
        self.secret = secret
        self.region = 'http://oss-%s.aliyuncs.com'%region
        self.bucket_name = bucket_name
        self.base_dir = base_dir
        self.date = datetime.datetime.now().strftime('%Y%m%d')
        self.conn()

    def conn(self):
        auth = oss2.Auth(self.key,self.secret)
        self.bucket = oss2.Bucket(auth,self.region,self.bucket_name)


    def setObj(self,data):
        '''存储str对象'''
        filename = shortuuid.uuid()
        try:
            result = self.bucket.put_object('%s/%s/%s'%(self.base_dir,self.date,filename), data)
            if result.status == 200:
                #print('[Success] Put obj success!')
                return filename
            else:
                print('[Faild] Put obj Faild!')
        except oss2.exceptions.ServerError as e:
            print('[Error] 服务器拒绝, 请检查[KEY][SECRET][存储桶]是否正确!')
        except oss2.exceptions.AccessDenied as e:
            print('[Error] 操作拒绝,请检查key是否有权限上传!')
        except Exception as e:
            print(e)

    def getObj(self,filename):
        '''获取str对象'''
        try:
            object_stream = self.bucket.get_object('%s/%s/%s'%(self.base_dir,self.date,filename))
            #print('[Success] Get obj success!')
            return object_stream.read().decode()
        except oss2.exceptions.NoSuchKey as e:
            print('[Error] 文件不存在!')
        except oss2.exceptions.ServerError as e:
            print('[Error] 服务器拒绝, 请检查[KEY][SECRET][存储桶]是否正确!')
        except oss2.exceptions.AccessDenied as e:
            print('[Error] 操作拒绝,请检查key是否有权限上传!')
        except Exception as e:
            print(e)

if __name__ == '__main__':
    oss_config = {
        "STORAGE_REGION":"cn-shanghai",
        "STORAGE_NAME":"shinezone-opendevops",
        "STORAGE_PATH":"record",
        "STORAGE_KEY_ID":"LTAIRiWZ3L2W7NQc",
        "STORAGE_KEY_SECRET":"vjUr6a6YcWlUqKO8WEJFLdINCdG42e"
    }

    data = '{"name":"yangmv","age":18}'
    obj = OSSApi(
        oss_config.get('STORAGE_KEY_ID'),oss_config.get('STORAGE_KEY_SECRET'),oss_config.get('STORAGE_REGION'),
        oss_config.get('STORAGE_NAME'),oss_config.get('STORAGE_PATH'))
    #obj.setObj(data)
    data = obj.getObj('vTPywdUPtEAZpMVc9facQJ')


