import re

import requests
from bs4 import BeautifulSoup

from utils.util import get_logger, strenc

logger = get_logger(__name__)

HDU_LOGIN_URL = "https://cas.hdu.edu.cn/cas/login?service=https%3A%2F%2Fi.hdu.edu.cn%2Ftp_up%2F"
# 该链接直接通过 cas 认证转入选课链接
CAS_XUANKE_URL = "http://cas.hdu.edu.cn/cas/login?service=http://jxgl.hdu.edu.cn/index.aspx"


class IHDU:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.realname = None
        self.session = requests.session()

    def login(self):
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
            # print(rsp.headers)
            # print(requests.utils.dict_from_cookiejar(self.session.cookies))
        except Exception:
            logger.error('认证失败！可能是账户或密码有误。')
            exit(1)

        # 选课系统转跳
        try:
            next_url = rsp.headers['Location']
            logger.info("Hit %s", next_url)
            rsp = self.session.get(next_url, allow_redirects=False)
        except Exception:
            logger.error('登录选课系统失败！请重试。')
            exit(1)

        # 转跳完毕，进入主界面
        home_url = 'http://jxgl.hdu.edu.cn/xs_main.aspx?xh={xh}'.format(xh=self.username)
        logger.info("Hit %s", home_url)
        self._do_goto_home(home_url)

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

    def _do_goto_home(self, home_url):
        """进入选课主页面，完成相关数据的更新"""
        # 用于在选课系统里的headers
        headers = {
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            'accept-encoding': "gzip, deflate",
            'accept-language': "zh-CN,zh;q=0.9",
            'connection': "keep-alive",
            'host': "jxgl.hdu.edu.cn",
            'referer': home_url,
            'upgrade-insecure-requests': "1",
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            'cache-control': "no-cache",
        }
        self.session.headers.update(headers)  # 更新headers
        page = self.session.get(home_url)
        soup = BeautifulSoup(page.text, 'lxml')
        self.realname = soup.find('form').find('div', class_='info').find(
            'li').find('span').get_text()

        logger.info('登录成功！你好%s！', self.realname)
