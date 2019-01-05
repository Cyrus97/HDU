import json
import os
from io import BytesIO

import requests
from PIL import Image

from crawler_hdu.login import HDU
from crawler_hdu.service import ElectiveService
from crawler_hdu.service import VERIFY_CODE_URL
from utils.train import get_clf, recognize_img


def main():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    config = None
    try:
        with open(config_file, 'r', encoding="utf-8") as f:
            config = json.load(f)
    except IOError:
        print('没有找到配置文件，请先配置好再重试。')
        exit(1)

    elective_courses = config.get('courses', None).get('通识选修课', None)
    kwargs = dict()
    kwargs['from_email'] = config.get('from_email', None)
    kwargs['from_email_psw'] = config.get('from_email_psw', None)
    kwargs['to_email'] = config.get('to_email', None)
    kwargs['delay'] = config.get('delay', None)

    # 获取验证码分类器
    img_path = os.path.abspath('pics/')
    clf = get_clf(img_path)

    hdu = HDU(username=config.get('username', None), password=config.get('password', None), clf=clf)
    hdu.login()
    # 启动选课服务
    e_s = ElectiveService(hdu, clf, elective_courses, **kwargs)
    e_s.start()


def test_clf(clf):
    while True:
        try:
            img = Image.open(BytesIO(requests.get(VERIFY_CODE_URL).content))
        except:
            pass
        else:
            break
    img.show()
    print('测试结果为 ' + recognize_img(img, clf))


if __name__ == '__main__':
    main()
