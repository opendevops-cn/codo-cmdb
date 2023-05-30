from cryptography.fernet import Fernet
import base64


class MyCrypt:
    """
    usage: mc = MyCrypt()               实例化
        mc.my_encrypt('ceshi')          对字符串ceshi进行加密
        mc.my_decrypt('')               对密文进行解密
    """

    def __init__(self, key: str = 'u121e37bb6523ac9f6a'):
        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度
        if not isinstance(key, bytes): key = key.encode('utf-8')
        if len(key) > 32:
            key = key[0:32]
        else:
            key = key.rjust(32, b'0')

        self.key = base64.urlsafe_b64encode(key)
        self.f = Fernet(self.key)

    @property
    def create_key(self):
        return Fernet.generate_key()

    def my_encrypt(self, text: str):
        if isinstance(text, str): text = text.encode('utf-8')
        return self.f.encrypt(text).decode('utf-8')

    def my_decrypt(self, text: str):
        if isinstance(text, str): text = text.encode('utf-8')
        return self.f.decrypt(text).decode('utf-8')


import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class AESCryptoV1(object):
    """
    Agent server 通信使用AES CBC加密
    message = "hello cryptokit"
    msg_crypto = AESMsgCrypto()
    aaa = msg_crypto.cbc_encrypt_base64(message)
    bbb = base64.b64decode(aaa)
    print(msg_crypto.cbc_decrypt(bbb))
    """

    def __init__(self, aes_key="121e37bb6523ac9f"):
        if not isinstance(aes_key, bytes): aes_key = aes_key.encode('utf-8')
        if len(aes_key) > 16:
            aes_key = aes_key[0:16]
        else:
            aes_key = aes_key.rjust(16, b'0')

        self.AES_KEY = aes_key
        self.AES_IV = aes_key

    @staticmethod
    def pkcs7_padding(data):
        if not isinstance(data, bytes): data = data.encode()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        return padded_data

    def cbc_encrypt_base64(self, data):
        if not isinstance(data, bytes): data = data.encode()
        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV), backend=default_backend())
        encryptor = cipher.encryptor()
        padded_data = encryptor.update(self.pkcs7_padding(data))
        return base64.b64encode(padded_data).decode()

    def cbc_decrypt(self, data):
        if not isinstance(data, bytes): data = data.encode()

        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV), backend=default_backend())
        decryptor = cipher.decryptor()

        uppaded_data = self.pkcs7_unpadding(decryptor.update(data))

        uppaded_data = uppaded_data.decode()
        return uppaded_data

    @staticmethod
    def pkcs7_unpadding(padded_data):
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data)

        try:
            uppadded_data = data + unpadder.finalize()
        except ValueError:
            raise Exception('无效的加密信息!')
        else:
            return uppadded_data


message = "hello cryptokit"
mc = AESCryptoV1(aes_key='test! 121e37bb6523ac9f')
aaa = mc.cbc_encrypt_base64(message)
bbb = base64.b64decode(aaa)
print(mc.cbc_decrypt(bbb))

# data = '#test %data _code$@这是一个简单的测试示例===*******~！@#￥%test! keyaaaaaaaaaaa……&*（）——+test! keyaaaaaaaaaaa'
# mkey = 'test! keyaaa'
# cc = MyCrypt(key=mkey)
# endata = cc.my_encrypt(data)
# print(endata)
