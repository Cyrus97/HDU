import logging
import smtplib
from email.mime.text import MIMEText

from utils import pyDes


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    fh = logging.FileHandler('hdu-log.log', encoding='utf-8')
    ch = logging.StreamHandler()
    formatter = logging.Formatter(fmt="[%(asctime)s %(levelname)s] %(name)s %(message)s", datefmt="%Y/%m/%d %X")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


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


def strenc(data, firstkey, secondkey, thirdKey):
    bts_data = extend_to_16bits(data)
    bts_firstkey = extend_to_16bits(firstkey)
    bts_secondkey = extend_to_16bits(secondkey)
    bts_thirdkey = extend_to_16bits(thirdKey)
    i = 0
    bts_result = []
    while i < len(bts_data):
        bts_temp = bts_data[i:i + 8]  # 将data分成每64位一段，分段加密
        j, k, z = 0, 0, 0
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


def extend_to_16bits(data):  # 将字符串的每个字符前插入 0，变成16位，并在后面补0，使其长度是64位整数倍
    bts = data.encode()
    filled_bts = []
    for each in bts:
        filled_bts.extend([0, each])  # 每个字符前插入 0
    while len(filled_bts) % 8 != 0:  # 长度扩展到8的倍数
        filled_bts.append(0)  # 不是8的倍数，后面添加0，便于DES加密时分组
    return filled_bts


if __name__ == '__main__':
    send_email(from_addr=None, psw=None, to_addr="974451090@qq.com", content="info")
