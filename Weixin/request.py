from Weixin.config import *
from requests import Request

class WeixinRequest(Request):
    """[summary]
    
    基于Request的新数据结构
    
    Extends:
        Request
    """
    def __init__(self, url, callback, method='GET', headers=None, need_proxy=False, fail_time=0, timeout=TIMEOUT):
        Request.__init__(self, method, url, headers)
        self.callback = callback
        self.need_proxy = need_proxy
        self.fail_time = fail_time #失败次数
        self.timeout = timeout