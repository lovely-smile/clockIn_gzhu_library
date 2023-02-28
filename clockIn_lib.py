import datetime
import json
import os
import platform
import time
import traceback

import requests
import selenium.webdriver
from func_timeout import func_set_timeout
from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class clockIn():
    def __init__(self):

        self.xuhao = str(os.environ['XUHAO'])
        self.mima = str(os.environ['MIMA'])
        self.SEATNO = str(os.environ['SEATNO'])
        self.pushplus = str(os.environ['PUSHPLUS'])

        if self.SEATNO == '':
            exit('请在Github Secrets中设置SEATNO')
        if self.xuhao == '':
            exit('请在Github Secrets中设置XUHAO')
        if self.mima == '':
            exit('请在Github Secrets中设置MIMA')

        # 加载配置
        options = Options()
        optionsList = [
            "--headless",
            # "--disable-gpu",
            "--lang=zh-CN",
            "--enable-javascript",
            "start-maximized",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-browser-side-navigation",
            "--disable-dev-shm-usage"
        ]

        for option in optionsList:
            options.add_argument(option)

        options.page_load_strategy = 'none'
        options.add_experimental_option(
            "excludeSwitches",
            ["ignore-certificate-errors", "enable-automation"])
        options.keep_alive = True



        self.driver = selenium.webdriver.Chrome(options=options)

        self.wdwait = WebDriverWait(self.driver, 30)
        self.titlewait = WebDriverWait(self.driver, 20)

        # self.page用来表示当前页面标题，0表示初始页面
        self.page = 0

        # self.fail表示打卡失败与否
        self.fail = False

    def __call__(self):
        for retries in range(4):
            try:
                logger.info(f"第{retries + 1}次运行")
                if retries:
                    # 恢复状态，让它重来
                    self.page = 0
                    self.fail = False

                self.step0()
                self.step1()
                self.step2()
                self.step3()

                # if self.page == 0:
                #     self.step0()
                #
                # if self.page in [0, 1]:
                #     self.step1()
                #
                # if self.page in [0, 1, 2]:
                #     self.step2()
                #
                # if self.page in [0, 1, 2, 3]:
                #     self.step3()

            except Exception:
                logger.error(traceback.format_exc())
                try:
                    if not self.driver.title:
                        logger.error(f'第{retries + 1}次运行失败，当前页面标题为空')
                    else:
                        logger.error(
                            f'第{retries + 1}次运行失败，当前页面标题为：{self.driver.title}')
                except Exception:
                    logger.error(f'第{retries + 1}次运行失败，获取当前页面标题失败')

                if retries == 3:
                    self.fail = True
                    logger.error("图书馆预定失败")

        self.driver.quit()
        # self.notify()

    def step0(self):
        """转到图书馆界面
        """
        logger.info('step0 正在转到转到图书馆界面')

        self.driver.get('''
                https://newcas.gzhu.edu.cn/cas/login?service=http://libbooking.gzhu.edu.cn/#/ic/home
                ''')

        if self.driver.title == 'Information Commons':
            # 说明验证通过，直接进入了界面
            return self.step3()

        logger.info('标题1: ' + self.driver.title)

        # 计算时间

        start = datetime.datetime.now()

        # 获取当前的操作系统
        system = platform.system()
        # 如果是Ubuntu
        if system == 'Linux':
            logger.info("当前操作系统为Linux")
            self.titlewait.until(EC.title_contains("Unified Identity Authentication"))
        else:
            logger.info("当前操作系统为非Linux")
            self.titlewait.until(EC.title_contains("统一身份认证"))


        # time.sleep(10)

        end = datetime.datetime.now()
        logger.info('等待时间: ' + str((end - start).seconds))



        logger.info('标题2: ' + self.driver.title)

    def step1(self):
        """登录融合门户
        """

        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='robot-mag-win small-big-small']")))

        logger.info('step1 正在尝试登陆统一身份认证')
        logger.info('标题: ' + self.driver.title)

        for script in [
            f"document.getElementById('un').value='{self.xuhao}'",
            f"document.getElementById('pd').value='{self.mima}'",
            "document.getElementById('index_login_btn').click()"
        ]:
            self.driver.execute_script(script)

    def step2(self):
        """正在转到图书馆界面
        """
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.title_contains("Information Commons"))

        logger.info('step2 正在转到图书馆界面')
        logger.info('标题: ' + self.driver.title)

    def step3(self):
        logger.info('step3 准备进行图书馆预定座位操作')
        logger.info('标题: ' + self.driver.title)

        cookie = self.get_cookie()

        if cookie == '':
            logger.info('没找到cookie')

            # 尝试访问
            self.driver.get("http://libbooking.gzhu.edu.cn/#/ic/home")

            # 计算时间
            start = datetime.datetime.now()
            time.sleep(5)
            end = datetime.datetime.now()
            logger.info('等待时间: ' + str((end - start).seconds))

            self.step3()
            return

        logger.info('primary cookie: ' + cookie)

        # 计算明天的日期，yyyy-MM-dd
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow = tomorrow.strftime('%Y-%m-%d')

        # 将下面的值转换成json格式
        reserve1 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '9:00:00', '12:00:00'))
        reserve2 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '14:00:00', '18:00:00'))

        logger.info(reserve1)
        logger.info(reserve2)

        message = f'''{tomorrow} 座位101-{self.SEATNO}，上午预定：{'预约成功' if reserve1.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
            {tomorrow} 座位101-{self.SEATNO}，下午预定：{'预约成功' if reserve2.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
        '''

        logger.info(message)

        # 发送消息
        self.notify(message)

        # 发送请求成功，可以结束程序了
        self.fail = False
        self.driver.quit()
        exit(0)

    def reserve_lib_seat(self, cookie, tomorrow, startTime, endTime):
        url = "http://libbooking.gzhu.edu.cn/ic-web/reserve"

        payload = json.dumps({
            "sysKind": 8,
            "appAccNo": 101598216,
            "memberKind": 1,
            "resvMember": [
                101598216
            ],
            "resvBeginTime": f"{tomorrow} {startTime}",
            "resvEndTime": f"{tomorrow} {endTime}",
            "testName": "",
            "captcha": "",
            "resvProperty": 0,
            "resvDev": [
                self.calc_dev_no(int(self.SEATNO))
            ],
            "memo": ""
        })
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.41',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        return response.text

    def calc_dev_no(self, no):
        return 101266684 + no - 1

    def decalc_devno(self, no):
        return no - 101266684 + 1

    def get_cookie(self):
        # 获取Cookie字符串

        ans = self.driver.get_cookies()
        logger.info('cookies' + str(ans))

        if len(ans) != 0:
            logger.info(ans[0])
            logger.info(ans[0].get('name'))
            return ans[0].get('name') + "=" + ans[0].get('value')

        return ''

    def notify(self, content):
        """图书馆预约信息
        """
        if self.pushplus:
            data = {"token": self.pushplus, "title": "图书馆预约信息", "content": content}
            url = "http://www.pushplus.plus/send/"
            logger.info(requests.post(url, data=data).text)


# 限制10分钟内，必须运行完成，否则失败处理
@func_set_timeout(60 * 3)
def main():
    cl = clockIn()
    cl()


if __name__ == "__main__":
    main()
