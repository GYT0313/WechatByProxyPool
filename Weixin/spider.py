from requests import Session
from Weixin.config import *
from Weixin.db import RedisQueue
from Weixin.mysql import MySQL
from Weixin.request import WeixinRequest
from urllib.parse import urlencode
import requests
from pyquery import PyQuery as pq
from requests import ReadTimeout, ConnectionError
class Spider():
    base_url = 'http://weixin.sogou.com/weixin'
    keyword = 'nba'
    # 在浏览器登录微型账号，复制头信息
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': 'SUV=00741786767159115B14EF6482F65698; IPLOC=CN5101; SUID=0F5971765018910A000000005B8502EA; ABTEST=0|1538190819|v1; weixinIndexVisited=1; SNUID=8997BFB8CECAB92ED3379270CF210494; ppinf=5|1539179396|1540388996|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToxODolRTUlQTQlOEYlRTglODclQjN8Y3J0OjEwOjE1MzkxNzkzOTZ8cmVmbmljazoxODolRTUlQTQlOEYlRTglODclQjN8dXNlcmlkOjQ0Om85dDJsdUpsbXpKbTMwbnBLR3dpZS04UHJiRTRAd2VpeGluLnNvaHUuY29tfA; pprdig=n3vIwZsDxGrwHD64wmdU5_9FuuC2JMW1YCfC3XgJAfCrsZfWPSwlJgI533gVFOFV8sAgKeSGVJGDtAtTLPp7ogpzTsmgDGxeSKOAHgx5Nzl7Cv2a8wcBH-0X10PL_989q-EaCvOMxI7_v4r2vyof7SWRpeUiW1_Jy4HhpJThW5k; sgid=13-37441915-AVuibA4T1jrnQU1Ky0B6JlaE; sct=4; ppmdig=1539333916000000c4962c2bc3acca5e7d2f1b84e62852ca',
        'Host': 'weixin.sogou.com',
        'Referer': 'https://www.baidu.com/link?url=FtXl1lPtCqfCQ2cUkZqZ0EGI9czAQ-XhjP9obI3xyd5r30swjgJT5JFRUTn7-BhU&wd=&eqid=aceee16a0006289f000000055bc05f1a',
        'Upgrade-Insecure-Requests': 1,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'
    }
    session = Session()
    queue = RedisQueue()
    mysql = MySQL()

    def get_proxy(self):
        """[summary]
        
        从代理池获取代理
        """
        try:
            response = requests.get(PROXY_POOL_URL)
            if response.status_code == 200:
                print('Get Proxy ', response.text)
                return response.text
        except requests.ConnectionError:
            return None

    def start(self):
        """[summary]
        
        初始化工作
        """
        # 全局更新headers
        self.session.headers.update(self.headers)
        start_url = self.base_url + '?' + urlencode({'type':2, 'query': self.keyword})
        # 创建一个request对象
        weixin_request = WeixinRequest(url=start_url, callback=self.parse_index, need_proxy=True)
        # 调度第一个请求
        self.queue.add(weixin_request)

    def parse_index(self, response):
        """[summary]
        
        解析索引页
        1. 提取本页所有文章的链接
        2. 提取下一页的链接
        Arguments:
            response {[type]} -- 响应
        """
        doc = pq(response.text)
        # 解析标题，获取url
        items = doc('.new-box .news-list li .txt-box h3 a').items()
        for item in items:
            url = item.attr('href')
            # 根据获取的url创建新的request对象
            weixin_request = WeixinRequest(url=url, callback=self.parse_detail)
            yield weixin_request
        # 获取下一页链接
        next = doc('#sogou_next').attr('href')
        if next:
            # 将下一页链接完整拼接
            url = self.base_url + str(next)
            weixin_request = WeixinRequest(url=url, callback=self.parse_index, need_proxy=True)
            yield weixin_request

    def parse_detail(self, response):
        """[summary]
        
        解析详情页
        
        Arguments:
            response {[type]} -- 响应
        """
        doc = pq(response)
        # 提取标题，正文，发布日期，发布人，微信公众号
        data = {
            'title': doc('rich_media_title').text(),
            'content': doc('rich_media_content ').text(),
            'date': doc('#publish_time').text(),
            'nickname': doc('#js_profile_qrcode > div > strong').text(),
            'wechat': doc('#js_profile_qrcode > div > p:nth-child(1) >span')
        }
        yield data

    def request(self, weixin_request):
        """[summary]
        
        执行请求
        
        Arguments:
            weixin_request {[type]} -- 请求
        """
        try:
            if weixin_request.need_proxy:
                proxy = self.get_proxy()
                if proxy:
                    proxies = {
                        'http': 'http://' + proxy
                    }
                    # 需要代理, prepare()将请求转换为Prepared Request
                    # return self.session.send(weixin_request.prepare(), timeout =weixin_request.timeout, allow_redirects=False, proxies=proxies)
                    return self.session.send(weixin_request.prepare(),timeout=weixin_request.timeout, allow_redirects=False, proxies=proxies)
                # 不需要代理
                return self.session.send(weixin_request.prepare(), timeout=weixin_request.timeout, allow_redirects=False)
        except (ConnectionError, ReadTimeout) as e:
            print(e.args)
            return False

    def error(self, weixin_request):
        """[summary]
        
        错误处理
        
        Arguments:
            weixin_request {[type]} -- 请求
        """
        weixin_request.fail_time = weixin_request.fail_time + 1
        print('Request Faild ', weixin_request.fail_time, ' Times ', weixin_request.url)
        # 失败未达最大值则加入队列
        if weixin_request.fail_time < MAX_FAILED_TIME:
            self.queue.add(weixin_request)

    def schedule(self):
        """[summary]
        
        调度请求
        """
        # 当队列不为空
        while not self.queue.empty():
            weixin_request = self.queue.pop()
            # 获得回调函数
            callback = weixin_request.callback
            print('Schedule ', weixin_request.url)
            response = self.request(weixin_request) # 调用request方法
            if response and response.status_code in VALID_STATUSES:
                # 如何响应合法，则调用回调函数进行解析(1.解析出新的requests对象，2.解析出文章内容)
                results = list(callback(response))
                if results:
                    for result in results:
                        print('-'*100)
                        print('New Result ', result)
                        # 返回结果是request对象就加入队列
                        if isinstance(result, WeixinRequest):
                            self.queue.add(result)
                        # 返回结果是文章内容就存入mysql
                        if isinstance(result, dict):
                            self.mysql.insert('articles', result)
                else:
                    self.error(weixin_request)
            else:
                self.error(weixin_request)

    def run(self):
        """[summary]
        
        入口
        """
        self.start()
        self.schedule()

if __name__ == '__main__':
    spider = Spider()
    spider.run()
