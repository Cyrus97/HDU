import logging
import re

import requests
from bs4 import BeautifulSoup

from utils import util

HDU_LOGIN_URL = "http://cas.hdu.edu.cn/cas/login"
XUANKE_URL = "http://jxgl.hdu.edu.cn/index.aspx"


class HDU:
    def __init__(self, username, password, clf):
        self.username = username
        self.password = password
        self.realname = None
        self.session = requests.session()
        self.courses = []
        self.clf = clf

    def login(self):
        """登录数字杭电，然后转跳到教务系统。"""
        # url = 'http://cas.hdu.edu.cn/cas/login'
        lt = util.get_lt(HDU_LOGIN_URL)
        password = util.md5_password(self.password)
        form_data = {
            'username': self.username,
            'password': password,
            'service': 'http://i.hdu.edu.cn/dcp/index.jsp',
            'encodedService': 'http%3a%2f%2fi.hdu.edu.cn%2fdcp%2findex.jsp',
            'serviceName': 'null',
            'loginErrCnt': '1',
            'lt': lt,
        }
        headers = {
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            'accept-encoding': "gzip, deflate",
            'accept-language': "en-US,en;q=0.5",
            'cache-control': "no-cache",
            'connection': "keep-alive",
            'content-length': "357",
            'content-type': "application/x-www-form-urlencoded",
            'host': "cas.hdu.edu.cn",
            'origin': "http://cas.hdu.edu.cn",
            'referer': "http://cas.hdu.edu.cn/cas/login?service=http%3A%2F%2Fi.hdu.edu.cn%2Fdcp%2Fforward.action%3Fpath%3D%2Fportal%2Fportal%26p%3DwkHomePage",
            'upgrade-insecure-requests': "1",
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        }

        # 登录数字杭电
        try:
            print('hit %s \n' % HDU_LOGIN_URL)
            rs = self.session.post(
                HDU_LOGIN_URL, data=form_data, headers=headers)
            soup = BeautifulSoup(rs.text, 'lxml')
            next_url = soup.find('p').find('a')['href']
            print('hit %s \n' % next_url)
            rs = self.session.get(next_url)  # 模拟cas转跳
            # url = 'http://i.hdu.edu.cn/dcp/forward.action?path=/portal/portal&p=wkHomePage'  # 跳转数字杭电主页
            # self.session.get(url)
        except Exception as e:
            print('登录数字杭电失败！可能是账户或密码有误。')
            logging.exception(e)
            exit(1)

        # 选课系统转跳
        # 最多3次尝试机会
        max_retry = 3
        while True:
            try:
                max_retry = max_retry - 1

                print('hit %s \n' % XUANKE_URL)
                next_url = self.get_cas_url(XUANKE_URL)
                # next_url = self.get_cas_url(XUANKE_LOGIN_URL)
                # 发现只要一次获取cas页面就可以
                rs = self.session.get(next_url)
            except Exception as e:
                if max_retry == 0:
                    print('登录选课系统失败！请重试。')
                    logging.exception(e)
                    exit(1)
            else:
                break

        # 转跳完毕，进入主界面
        home_url = 'http://jxgl.hdu.edu.cn/xs_main.aspx?xh={xh}'.format(
            xh=self.username)
        print('hit %s' % home_url)
        self.do_goto_home(home_url)
        print('登录成功！你好' + self.realname + '\n')

    def get_cas_url(self, url):
        """从cas认证页面获取下一个转跳url"""
        rs = self.session.get(url)
        soup = BeautifulSoup(rs.text, 'lxml')
        # print(soup)
        next_url = soup.find('a')['href']
        if not self.is_valid_url(next_url):
            raise Exception('转跳失败。')

        return next_url

    def is_valid_url(self, url):
        reg = r'^http[s]*://.+$'
        return re.match(reg, url)

    def do_goto_home(self, home_url):
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
            'li').find('span').get_text().replace('同学', '')
