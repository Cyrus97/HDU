import logging
import time
import urllib.parse
from copy import copy
from io import BytesIO

from PIL import Image
from bs4 import BeautifulSoup

from utils.train import get_clf, recognize_img
from utils.util import get_logger, send_email

logger = get_logger(__name__)

ELECTIVE_URL = "http://jxgl.hdu.edu.cn/xf_xsqxxxk.aspx"  # 通识选修课
PTLLK_URL = "http://jxgl.hdu.edu.cn/xsxk.aspx"  # 普通理论课和实验课
VERIFY_CODE_URL = "http://jxgl.hdu.edu.cn/CheckCode.aspx"
DELAY = 5  # 查询延迟时间
RETRY_TIMES = 3  # 重试次数


class BaseService:
    def __init__(self, hdu, kwargs):
        self.username = hdu.username
        self.realname = hdu.realname
        self.session = hdu.session
        self.courses = kwargs.get('courses')
        self.clf = get_clf()
        self.from_email = kwargs.get('from_email', None)
        self.from_email_psw = kwargs.get('from_email_psw', None)
        self.to_email = kwargs.get('to_email', None)
        self.url = None
        self.delay = kwargs.get('delay', DELAY)
        self.courses_ok = list()

    def start(self):
        pass

    def select_course(self):
        pass

    def get_common_form_data(self):
        """获取共同需要的form data"""
        pass

    def get_form_data(self):
        """准备form_data"""
        pass

    def get_verify_code(self):
        while True:
            try:
                img = Image.open(BytesIO(self.session.get(VERIFY_CODE_URL).content))
            except:
                pass
            else:
                break
        # img.show()
        code = recognize_img(img, self.clf)
        logger.debug('验证码： %s', code)
        return code

    def update_form_data(self, page, form_data):
        try:
            VIEWSTATE = page.find('input', id='__VIEWSTATE')
            EVENTVALIDATION = page.find('input', id='__EVENTVALIDATION')

            form_data['__VIEWSTATE'] = VIEWSTATE.get('value', form_data['__VIEWSTATE']) if VIEWSTATE else form_data[
                '__VIEWSTATE']
            form_data['__EVENTVALIDATION'] = EVENTVALIDATION.get('value',
                                                                 form_data['__EVENTVALIDATION']) if EVENTVALIDATION else \
                form_data['__EVENTVALIDATION']
        except Exception as e:
            logging.exception(e)
            raise e

        return form_data

    def print_info(self):
        info = list()
        for cos in self.courses:
            info.append(cos.get('课程名称'))
        logger.info("待选课程：%s", info)

        info = list()
        for cos in self.courses_ok:
            info.append(cos.get('课程名称'))
        logger.info("已选课程：%s", info)

    def send_email(self, content):
        if self.from_email and self.from_email_psw and self.to_email:
            send_email(from_addr=self.from_email, psw=self.from_email_psw, to_addr=self.to_email, content=content)
        else:
            logger.warning('发送邮件失败，缺少相关数据。')


class ElectiveService(BaseService):
    """通识选修课程的选课server"""

    def start(self):
        """启动抢课"""
        logger.info('开始进行通识选修课程的选课...')
        params = {
            'xh': self.username,
            'xm': self.realname,
            'gnmkdm': 'N121113',
        }
        self.url = ELECTIVE_URL + '?{params}'.format(params=urllib.parse.urlencode(params))
        # 通识选修课入口 url = "http://jxgl.hdu.edu.cn/xf_xsqxxxk.aspx?xh=16051717&xm=%u5218%u5174%u7136&gnmkdm=N121113"

        form_data = self.get_form_data()
        counts = 0

        while True:
            if not self.courses:  # 为空 或者 如果全部都为 true，即全部都已经完成
                logger.info('恭喜，课程均已选完:)')
                break
            if counts % 100 == 0:
                self.print_info()
            logger.info('第 %s 次尝试...', counts)

            counts = counts + 1
            time.sleep(self.delay)

            try:
                page = self.session.post(self.url, data=form_data)
                soup = BeautifulSoup(page.text, 'lxml').find('form')
                # print(soup)
                form_data = self.update_form_data(soup, form_data)
                soup = soup.find('fieldset').find('table', class_='datelist')
                found_courses_list = soup.find_all('tr')[1:]
            except Exception as e:
                # 因为不更新form也可以查询，所以没有成功获取到的话，就重新来一次
                # 如果form没有更新成功的话，跳过下面的操作
                logging.exception(e)
                continue

            # self.delete_courses(form_data, 'DataGrid2$ctl03$ctl00')
            # exit(1)

            # 查询
            for course_info in found_courses_list:
                try:
                    td_list = course_info.find_all('td')
                    xuanke_code = td_list[0].find('input')['name']  # 选课代码，用于表单
                    courses_name = td_list[2].get_text()  # 课程名称
                    courses_code = td_list[3].get_text()  # 课程代码
                    teacher_name = td_list[4].get_text()  # 教师名称
                    courses_time = td_list[5].get_text()  # 上课时间
                    courses_place = td_list[6].get_text()  # 上课地点
                    courses_margin = td_list[11].get_text()  # 余量
                    courses_affiliation = td_list[12].get_text()  # 课程归属
                    courses_nature = td_list[13].get_text()  # 课程性质
                    # print(courses_name)
                    selected = []  # 要移除的课程
                    for cos in self.courses:
                        # TODO: 分析课程冲突
                        cos_name = cos.get('课程名称', None)
                        cos_code = cos.get('课程代码', None)
                        if cos_name == courses_name and cos_code == courses_code:
                            info = "课程代码: {code}，课程名称: {name}, 课程性质: {nature}, 教师名称: {teacher}, 上课时间: {time}".format(
                                code=courses_name, name=courses_name, nature=courses_nature, teacher=teacher_name,
                                time=courses_time)
                            logger.info("发现匹配课程：%s", info)
                            # 选课成功，发送邮件
                            # 使用 copy(form_data),为了时选课之后的表单数据依然是查询用的表单，不然会一直当作选课表单来用
                            if self.select_courses(copy(form_data), xuanke_code, courses_name, courses_code):
                                logger.info("选课成功：%s", cos)
                                selected.append(cos)
                                self.send_email(info)
                    # 把已经选择的课程移除
                    for cos in selected:
                        self.courses.remove(cos)
                        self.courses_ok.append(cos)
                except Exception:
                    continue

    def get_form_data(self):
        counts = 0
        VIEWSTATE = None
        EVENTVALIDATION = None
        hidXNXQ = None
        while True:
            try:
                counts = counts + 1
                page = self.session.get(self.url)
                soup = BeautifulSoup(page.text, 'lxml')
                VIEWSTATE = soup.find('form').find('input', id='__VIEWSTATE')['value']
                EVENTVALIDATION = soup.find('form').find('input', id='__EVENTVALIDATION')['value']
                hidXNXQ = soup.find('form').find('input', id='hidXNXQ')['value']
            except Exception:
                if counts >= RETRY_TIMES:
                    logger.error("出错了！")
                    exit(1)
            else:
                if VIEWSTATE and EVENTVALIDATION and hidXNXQ:
                    break

        form_data = {
            '__EVENTTARGET': '',  # 退课
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': VIEWSTATE,
            '__EVENTVALIDATION': EVENTVALIDATION,
            'ddl_kcxz': '',  # 课程性质 '人文经典与人文修养'.encode('gb2312')
            'ddl_ywyl': '有'.encode('gb2312'),  # 有无余量 (有，无，空)
            'ddl_kcgs': '',  # 课程归属 '通识选修一般课'.encode('gb2312')
            'ddl_xqbs': "1",  # 上课校区
            'ddl_sksj': '',  # 上课时间
            'TextBox1': '',  # 根据课程名称查询
            # 'Button1': '提交'.encode('gb2312'), # 选课确定按钮
            'Button2': '确定'.encode('gb2312'),  # 课程名称查询提交按钮
            'txtYz': '',  # 验证码
            'hidXNXQ': hidXNXQ,  # 学年学期
        }

        return form_data

    def select_courses(self, data, xuanke_code, courses_name, courses_code):
        """选课. Returns : Boolean object

        :param data: 表单数据.
        :param xuanke_code: 在网页中表示的选课代码.
        :param courses_name: 课程名称.
        :param courses_code: 课程代码.
        :return: Boolean object
        """
        # url = "http://jxgl.hdu.edu.cn/xf_xsqxxxk.aspx?xh=16051717&xm=%u5218%u5174%u7136&gnmkdm=N121113"

        data['txtYz'] = self.get_verify_code()
        if 'Button2' in data:
            data.pop('Button2')  # 删除Button2
        data['Button1'] = '  提交  '.encode('gb2312')
        data[xuanke_code] = 'on'

        page = None
        exist_courses = None
        try:
            # TODO: 对比已选课程，在课程里的不选课
            page = self.session.post(self.url, data=data)
            # 检查是不是已经选
            soup = BeautifulSoup(page.text, 'lxml').find('form').find_all('fieldset')[1].find('table',
                                                                                              class_='datelist')
            courses_list = soup.find_all('tr')[1:]
            exist_courses = []
            for courses in courses_list:
                td_list = courses.find_all('td')
                course_name = td_list[0].get_text()
                teacher_name = td_list[1].get_text()
                courses_time = td_list[6].get_text()
                courses_place = td_list[7].get_text()
                exist_courses.append(course_name)

            # print(courses_name + str(exist_courses))
        except Exception as e:
            logger.error('选课发生错误。')

        if page.status_code == 200 and courses_name in exist_courses:
            return True
        else:
            return False

    def delete_courses(self, form_data, code):
        buttons = ['Button1', 'Button2', 'Button3', 'Button4', ]
        for btn in buttons:
            if btn in form_data:
                form_data.pop(btn)
        form_data['__EVENTTARGET'] = code
        form_data['txtYz'] = self.get_verify_code()

        page = self.session.post(self.url, data=form_data)

    def check_courses(self, courses):
        """检查和纠正待抢课程"""
        self.courses = courses

    def query_courses(self, page, courses):
        pass


class SportService(BaseService):
    """体育课的选课"""
    pass
