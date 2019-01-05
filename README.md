# HDU 选课

## 简介
这是一个适用于杭州电子科技大学选课系统的选课脚本。该脚本使用 Python 编写，目前支持通识选修课模块的选课功能，体育课和普通理论课的选课功能正在计划中。

## 环境依赖
- Python 3
- Git

## 安装
```
git clone https://github.com/Cyrus97/HDU.git
cd HDU
pip install -r ./requirements.txt
```

## 配置文件
使用之前需要配置好项目下的 [config.json](./config.json) 文件。

下面是对该配置文件的详细说明。

```
{
  "username": "学号",  // 数字杭电登录账号，即学号
  "password": "密码",  // 数字杭电密码
  // 把相关课程按照模板填入，课程名称和课程代码是必须要填的，其他的可以空着
  "courses": {
    "通识选修课": [
      {
        "课程名称": "国学雅集",
        "课程性质": "人文经典与人文修养",
        "课程归属": "通识选修一般课",
        "课程代码": "C1292016",
        "上课时间": ""
      },
      {
        "课程名称": "文学与人生",
        "课程性质": "人文经典与人文修养",
        "课程归属": "通识选修一般课",
        "课程代码": "C1292030",
        "上课时间": ""
      }
    ],
    "普通理论课": [
      {
        "课程名称": "编译原理",
        "课程性质": "专业必修",
        "课程代码": "A0504020",
        "上课时间": "",
        "教师名称": ""
      }
    ],
    "体育课": [
      {
        "课程名称": "羽毛球",
        "课程代码": "T1300020",
        "教师姓名": "",
        "上课时间": ""
      }
    ]
  },
  // 选课成功会发送邮件，如果留空则不会发送
  "from_email": "发送通知的邮箱",
  "from_email_psw": "发送通知的邮箱的密码",
  "to_email": "接收通知的邮箱",
  "delay": 5  // 选课频率，越小越快，无特殊要求不要更改
}   
```

## 快速开始
安装完成，配置完文件就可以愉快的运行了。

```
python ./run.py
```

## 问题
有任何问题请提 issue，或者发邮件至 `liuxingran97@gmail.com`。

## TODO
- [ ] 支持体育课，普通理论课
- [ ] 支持多进程，每个进程进行不同种类的课程的选课
