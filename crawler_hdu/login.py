import json
import os
import re

import requests
from bs4 import BeautifulSoup

from utils.util import get_logger, strenc

logger = get_logger(__name__)

HDU_LOGIN_URL = "https://cas.hdu.edu.cn/cas/login?service=https%3A%2F%2Fi.hdu.edu.cn%2Ftp_up%2F"
# 该链接直接通过 cas 认证转入选课链接
CAS_XUANKE_URL = "http://cas.hdu.edu.cn/cas/login?service=http://jxgl.hdu.edu.cn/index.aspx"
# 保存 cookie 的文件
COOKIES_FILE = 'cookies.txt'
# 登录重试次数
RETRY = 3


class IHDU:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.realname = None
        self.session = requests.session()
        self.home_url = 'http://jxgl.hdu.edu.cn/xs_main.aspx?xh={xh}'.format(xh=username)

    def login(self):
        retry = 0
        while retry < RETRY:
            retry += 1
            logger.info('尝试第 %s 次登录', retry)
            # 只使用一次：从本地文件读取cookie
            if retry == 1 and os.path.exists(COOKIES_FILE):
                logger.info('从本地文件读取 cookies')
                with open(COOKIES_FILE, 'r') as f:
                    self.session.cookies.update(json.loads(f.read()))
            else:
                self._do_login()

            # 更新使用于选课系统的 headers
            headers = {
                'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                'accept-encoding': "gzip, deflate",
                'accept-language': "zh-CN,zh;q=0.9",
                'connection': "keep-alive",
                'host': "jxgl.hdu.edu.cn",
                'referer': self.home_url,
                'upgrade-insecure-requests': "1",
                'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                'cache-control': "no-cache",
            }
            self.session.headers.update(headers)  # 更新 headers

            if self._check_sess_vaild():
                logger.info('登录成功！你好%s！', self.realname)
                with open(COOKIES_FILE, 'w') as f:
                    f.write(json.dumps(self.session.cookies.get_dict()))
                break
            else:
                logger.error('登录选课系统失败！请重试。')
                # self.session.cookies.clear()  # 直接清除 cookie 有点问题
                self.session = requests.session()

    def _do_login(self):
        """登录数字杭电，然后转跳到教务系统。"""
        headers = {
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            'accept-encoding': "gzip, deflate, br",
            'accept-language': "zh-CN,zh;q=0.9,en;q=0.8",
            'cache-control': "max-age=0",
            'connection': "keep-alive",
            'content-type': "application/x-www-form-urlencoded",
            'host': "cas.hdu.edu.cn",
            'origin': "http://cas.hdu.edu.cn",
            'upgrade-insecure-requests': "1",
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        }
        payload = self._get_payload(CAS_XUANKE_URL)

        # 通过智慧杭电认证
        try:
            logger.info("Hit %s", CAS_XUANKE_URL)
            rsp = self.session.post(CAS_XUANKE_URL, data=payload, headers=headers, allow_redirects=False)
        except Exception:
            logger.error('认证失败！可能是账户或密码有误。')
            return

        # 选课系统转跳
        try:
            next_url = rsp.headers['Location']
            logger.info("Hit %s", next_url)
            rsp = self.session.get(next_url, allow_redirects=False)
        except Exception:
            logger.error('登录选课系统失败！请重试。')
            return

    def _get_payload(self, url):
        rsp = self.session.get(url)
        if rsp.status_code != 200:
            return None
        soup = BeautifulSoup(rsp.text, 'lxml').find('script', id='password_template')
        soup = BeautifulSoup(soup.contents[0], 'lxml')
        lt = soup.find('input', id='lt')['value']
        execution = soup.find('input', attrs={'name': 'execution'})['value']
        _eventId = soup.find('input', attrs={'name': '_eventId'})['value']
        rsa = strenc(self.username + self.password + lt, '1', '2', '3')
        payload = {
            'rsa': rsa,
            'ul': len(self.username),
            'pl': len(self.password),
            'lt': lt,
            'execution': execution,
            '_eventId': _eventId,
        }

        return payload

    def is_valid_url(self, url):
        reg = r'^http[s]*://.+$'
        return re.match(reg, url)

    def _check_sess_vaild(self):
        cookies_keys = list(self.session.cookies.get_dict().keys())
        if 'ASP.NET_SessionId' in cookies_keys and 'route' in cookies_keys:
            rsp = self.session.get(self.home_url)
            if 'Object moved' not in rsp.text:
                soup = BeautifulSoup(rsp.text, 'lxml')
                try:
                    self.realname = soup.find('form').find('div', class_='info').find('span', id='xhxm').get_text()
                except:
                    logger.error('获取名字失败')
                    return False
                return True

        return False

    def extract(self):
        hdu = {
            'username': self.username,
            'realname': self.realname,
            'session': self.session,
        }
        return hdu
