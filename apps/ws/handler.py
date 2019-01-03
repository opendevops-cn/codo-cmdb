#!/usr/bin/env python
#encoding:utf-8

import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketClosedError
import json
import threading
from apps.ws.cores.webcon import Tty,Server,TermLogRecorder
from apps.ws.cores.api import get_object
import select
import sys
import datetime
from assets.models.server import Log,TtyLog
import jwt

class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            super(MyThread, self).run()
        except WebSocketClosedError:
            pass

class WebTty(Tty):
    def __init__(self, *args, **kwargs):
        super(WebTty, self).__init__(*args, **kwargs)
        self.ws = None
        self.data = ''
        self.input_mode = False

class WebTerminalHandler(tornado.websocket.WebSocketHandler):
    '''webTerminal主程序'''
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.term = None
        self.id = 0
        self.user = None
        self.ssh = None
        self.channel = None
        self.log = None
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        asset_id = self.get_argument('id',9999)
        print('asset_id--->',asset_id)

        asset = get_object(Server, id=asset_id)
        #print('asset---->',asset)

        auth_key = self.get_cookie('auth_key', None)
        user_info = jwt.decode(auth_key, verify=False)
        username = user_info['data']['nickname'] if 'data' in user_info else 'yangmv'

        self.term = WebTty(asset)
        self.ssh = self.term.get_connection(self)

        if self.ssh:
            remote_ip_list = self.request.headers.get("X-Forwarded-For")
            #remote_ip_real = self.request.headers.get("X-Real-IP")
            if remote_ip_list:
                remote_ip = remote_ip_list.split(',')[0]
            else:
                remote_ip = self.request.remote_ip
            self.log = Log(user=username, host=asset.hostname, remote_ip=remote_ip, login_type='web')
            self.log.save()
            self.termlog = TermLogRecorder(log=self.log)

            self.channel = self.ssh.invoke_shell(term='xterm')
            WebTerminalHandler.tasks.append(MyThread(target=self.forward_outbound))
            WebTerminalHandler.clients.append(self)
            for t in WebTerminalHandler.tasks:
                if t.is_alive():    #判断进程是否处于活动状态
                    continue
                try:
                    t.setDaemon(True)   #守护进程
                    t.start()
                except RuntimeError:
                    pass

    def on_message(self, message):
        #print('message--->',message)
        data = message
        self.term.input_mode = True
        if data in ['\r', '\n', '\r\n']:       #如果用户按了回车
            # print('self.term.data=======>',self.term.data)
            result = self.term.data
            # print('result_len--->',len(result))
            if len(result) > 0:
                TtyLog(log=self.log, datetime=datetime.datetime.now(), cmd=result).save()   #记录操作命令
            self.term.vim_data = ''
            self.term.data = ''
            self.term.input_mode = False
        self.channel.send(data)     #1 把用户发送过来的数据,发送给self.channle

    def on_close(self):
        print('Websocket: Close request')
        if self in WebTerminalHandler.clients:
            WebTerminalHandler.clients.remove(self)
        try:
            self.log.end_time = datetime.datetime.now()
            self.log.save()
            self.termlog.save()
            self.ssh.close()
            self.close()
        except AttributeError:
            pass

    def forward_outbound(self):
        try:
            data = ''
            while True:
                r, w, e = select.select([self.channel, sys.stdin], [], [])
                if self.channel in r:
                    # 获取用户输入的内容
                    recv = self.channel.recv(1024)
                    #print('recv===>',recv)      #2 接收on_message向我发送过来的数据
                    if not len(recv):
                        return
                    #recv = recv.decode(encoding="utf-8", errors="replace")
                    recv = recv.decode()
                    data += recv
                    self.term.vim_data += recv
                    try:
                        #print('data--->',data)
                        self.write_message(data) #内容给web,进行显示
                        self.termlog.write(data) #内容保存一份到日志,用于回放

                        if self.term.input_mode:
                            self.term.data += data
                        data = ''
                    except UnicodeDecodeError:
                        pass
        except IndexError:
            pass


from tornado import httpclient
class WsTest(tornado.web.RequestHandler):
    async def get(self, *args, **kwargs):
        http_client = httpclient.AsyncHTTPClient()

        #登录
        json_data = json.dumps(
            dict(
                username='yangmingwei',
                password='123456',
                dynamic=''
            )
        )
        response = await http_client.fetch('http://gw.aaa.net.cn/accounts/login/',raise_error=False,method='POST',body=json_data,headers=self.request.headers)
        print(response.body)
        auth_key = json.loads(response.body).get('auth_key')
        self.set_cookie("auth_key","%s"%auth_key)
        print(self.request.headers)

        response = await http_client.fetch('http://gw.aaa.net.cn/mg/v2/sysconfig/settings/STORAGE/', raise_error=False,headers=self.request.headers)
        print(1111)
        print(response.body)
        ret = {'status':True,'message':None}

        self.write(json.dumps(ret))

ws_urls = [
    ('/ws/test', WsTest),
    ('/v1/cmdb/ws/terminal', WebTerminalHandler)
]


