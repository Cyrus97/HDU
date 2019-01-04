import logging
import re

import requests

from bs4 import BeautifulSoup

from utils import util, pyDes

HDU_LOGIN_URL = "https://cas.hdu.edu.cn/cas/login?service=https%3A%2F%2Fi.hdu.edu.cn%2Ftp_up%2F"
# 该链接直接通过 cas 认证转入选课链接
XUANKE_URL = "http://cas.hdu.edu.cn/cas/login?service=http://jxgl.hdu.edu.cn/index.aspx"


class HDU:
    def __init__(self, username, password, clf):
        self.username = username
        self.password = password
        self.realname = None
        self.session = requests.session()
        self.courses = []
        self.clf = clf

    def get_part_payload(self, url):
        response = self.session.get(url)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'lxml').find('script', id='password_template')
        soup = BeautifulSoup(soup.contents[0], 'lxml')
        lt = soup.find('input', id='lt')['value']
        execution = soup.find('input', attrs={'name': 'execution'})['value']
        _eventId = soup.find('input', attrs={'name': '_eventId'})['value']

        data = {
            'lt': lt,
            'execution': execution,
            '_eventId': _eventId,
        }
        return data
    
    def strenc(self, data, firstkey, secondkey, thirdKey):
        bts_data = self.extend_to_16bits(data)  # 将data长度扩展成64位的倍数
        bts_firstkey = self.extend_to_16bits(firstkey)  # 将 first_key 长度扩展成64位的倍数
        bts_secondkey = self.extend_to_16bits(secondkey)  # 将 second_key 长度扩展成64位的倍数
        bts_thirdkey = self.extend_to_16bits(thirdKey)
        i = 0
        bts_result = []
        while i < len(bts_data):
            bts_temp = bts_data[i:i + 8]  # 将data分成每64位一段，分段加密
            j, k, z= 0, 0, 0
            while j < len(bts_firstkey):
                des_k = pyDes.des(bts_firstkey[j: j + 8], pyDes.ECB)  # 分别取出 first_key 的64位作为密钥
                bts_temp = list(des_k.encrypt(bts_temp))
                j += 8
            while k < len(bts_secondkey):
                des_k = pyDes.des(bts_secondkey[k:k + 8], pyDes.ECB)  # 分别取出 second_key 的64位作为密钥
                bts_temp = list(des_k.encrypt(bts_temp))
                k += 8

            while z < len(bts_thirdkey):
                des_k = pyDes.des(bts_thirdkey[z:z + 8], pyDes.ECB)  # 分别取出 second_key 的64位作为密钥
                bts_temp = list(des_k.encrypt(bts_temp))
                z += 8

            bts_result.extend(bts_temp)
            i += 8
        str_result = ''
        for each in bts_result:
            str_result += '%02X' % each  # 分别加密data的各段，串联成字符串
        return str_result
 
    def extend_to_16bits(self, data):  # 将字符串的每个字符前插入 0，变成16位，并在后面补0，使其长度是64位整数倍
        bts = data.encode()
        filled_bts = []
        for each in bts:
            filled_bts.extend([0, each])  # 每个字符前插入 0
        while len(filled_bts) % 8 != 0:  # 长度扩展到8的倍数
            filled_bts.append(0)  # 不是8的倍数，后面添加0，便于DES加密时分组
        return filled_bts

    def login(self):
        """登录数字杭电，然后转跳到教务系统。"""
        data = self.get_part_payload(XUANKE_URL)
        rsa = self.strenc(self.username + self.password + data.get('lt'), '1', '2', '3')

        payload = {
            'rsa': rsa,
            'ul': len(self.username),
            'pl': len(self.password),
            # 'lt': '',
            # 'execution': ,
            # '_eventId': ,
        }
        payload.update(data)

        headers = {
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            'accept-encoding': "gzip, deflate, br",
            'accept-language': "zh-CN,zh;q=0.9,en;q=0.8",
            'cache-control': "max-age=0",
            'connection': "keep-alive",
            'content-type': "application/x-www-form-urlencoded",
            'host': "cas.hdu.edu.cn",
            'origin': "http://cas.hdu.edu.cn",
            'referer': "http://cas.hdu.edu.cn/cas/login?service=http://jxgl.hdu.edu.cn/index.aspx",
            'upgrade-insecure-requests': "1",
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        }


        # 通过智慧杭电认证
        try:
            print('hit %s \n' % XUANKE_URL)
            rsp = self.session.post(
                XUANKE_URL, data=payload, headers=headers, allow_redirects=False)
            
            # print(rsp.headers)
            # print(requests.utils.dict_from_cookiejar(self.session.cookies))
        except Exception as e:
            print('认证失败！可能是账户或密码有误。')
            logging.exception(e)
            exit(1)

        # 选课系统转跳
        try:
            next_url = rsp.headers['Location']
            print('hit %s \n' % next_url)
            rsp = self.session.get(next_url, allow_redirects=False)
        except Exception as e:
            print('登录选课系统失败！请重试。')
            logging.exception(e)
            exit(1)

        # 转跳完毕，进入主界面
        home_url = 'http://jxgl.hdu.edu.cn/xs_main.aspx?xh={xh}'.format(
            xh=self.username)
        print('hit %s' % home_url)
        self.do_goto_home(home_url)
        print('登录成功！你好' + self.realname + '\n')


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
