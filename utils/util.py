import hashlib
import re
import smtplib
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup


# 获取LT值
def get_lt(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, 'lxml')
    lt = soup.find('input', value=re.compile(r'LT-\w*'))['value']
    return lt


def md5_password(password):
    m = hashlib.md5()
    m.update(password.encode('utf-8'))
    return m.hexdigest()


def send_email(from_addr, psw, to_addr, content):
    msg = MIMEText(''.join(content), 'plain', 'utf-8')
    msg['From'] = 'HDU-Notify<{sender}>'.format(sender=from_addr)
    msg['To'] = '<{to_addr}>'.format(to_addr=to_addr)
    msg['Subject'] = '课程通知-已监控到你要的课程'

    server = smtplib.SMTP_SSL('smtp.qq.com', 465)
    # server.set_debuglevel(1)
    server.login(from_addr, psw)
    server.sendmail(from_addr, [to_addr], msg.as_string())
    server.quit()


if __name__ == '__main__':
    send_email(from_addr=None, psw=None, to_addr="974451090@qq.com", content="info")
