"""
邮件发送核心模块
实现SMTP邮件发送、后台Worker、进度追踪等功能
"""
import smtplib
import threading
import time
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

from Sills.db_email_task import (
    get_task_by_id, get_task_contacts, update_task_progress,
    is_cancel_requested, complete_task, error_task
)
from Sills.db_email_log import add_log
from Sills.db_email_account import (
    get_account_by_id, can_send_today, increment_sent_count
)
from Sills.crypto_utils import decrypt_password as aes_decrypt


# 固定CC收件人
FIXED_CC_EMAIL = "jinzheng519@163.com"
# 报告接收邮箱
REPORT_EMAIL = "joy@unicornsemi.com"


class EmailSenderWorker:
    """邮件发送Worker类"""

    def __init__(self, task_id):
        self.task_id = task_id
        self.task = None
        self.account = None
        self.contacts = []
        self.stop_flag = False
        self.thread = None

    def load_task_data(self):
        """加载任务数据"""
        self.task = get_task_by_id(self.task_id)
        if not self.task:
            raise ValueError(f"任务 {self.task_id} 不存在")

        # 获取发件人账号
        self.account = get_account_by_id(self.task['account_id'])
        if not self.account:
            raise ValueError(f"发件人账号 {self.task['account_id']} 不存在")

        # 解密密码
        if self.account.get('password'):
            try:
                self.account['password'] = aes_decrypt(self.account['password'])
            except:
                pass

        # 获取联系人列表
        self.contacts = get_task_contacts(self.task_id)

    def connect_smtp(self):
        """连接SMTP服务器"""
        email = self.account['email']
        password = self.account['password']
        smtp_server = self.account.get('smtp_server', 'smtp.163.com')

        # 清除代理环境变量(避免代理拦截SMTP SSL连接)
        proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        proxy_backup = {k: os.environ.pop(k) for k in proxy_keys if k in os.environ}

        try:
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=20)
            server.login(email.strip(), password.strip())
            return server
        finally:
            os.environ.update(proxy_backup)

    def send_single_email(self, server, to_email, company_name=""):
        """发送单封邮件"""
        email = self.account['email']
        subject = self.task['subject']
        body = self.task['body']

        # 替换占位符
        subject = subject.replace('{公司名}', company_name)
        body = body.replace('{公司名}', company_name)

        message = MIMEMultipart()
        html_part = MIMEText(body, 'html', 'utf-8')
        message.attach(html_part)

        message['Subject'] = subject
        message['From'] = email
        message['To'] = to_email
        message['Cc'] = FIXED_CC_EMAIL

        # 发送邮件
        server.sendmail(email, to_email, message.as_string())

    def is_in_schedule_time(self):
        """检查当前是否在发送时间段内"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')

        schedule_start = self.task.get('schedule_start', '')
        schedule_end = self.task.get('schedule_end', '')

        if not schedule_start or not schedule_end:
            return True  # 无时间段限制

        return schedule_start <= current_time <= schedule_end

    def run(self):
        """Worker主循环"""
        sent_count = 0
        failed_count = 0

        try:
            self.load_task_data()

            # 连接SMTP
            server = self.connect_smtp()

            total = len(self.contacts)

            for idx, contact in enumerate(self.contacts):
                # 检查取消请求
                if is_cancel_requested(self.task_id):
                    self.stop_flag = True
                    break

                # 检查时间段
                while not self.is_in_schedule_time():
                    if is_cancel_requested(self.task_id):
                        self.stop_flag = True
                        break
                    time.sleep(60)  # 每分钟检查一次

                if self.stop_flag:
                    break

                # 检查日限
                can_send, remaining = can_send_today(self.task['account_id'])
                if not can_send:
                    # 达到日限,等待到第二天
                    print(f"[Worker] 达到日限,等待到第二天继续")
                    # 保存当前进度并暂停
                    update_task_progress(self.task_id, sent_count, failed_count)
                    # 这里需要更复杂的跨日逻辑,简化处理:标记为paused
                    error_task(self.task_id, "达到日发送限制,等待第二天继续")
                    server.quit()
                    return

                email = contact.get('email', '')
                contact_id = contact.get('contact_id', '')
                company_name = contact.get('company', '')

                if not email:
                    continue

                try:
                    self.send_single_email(server, email, company_name)
                    add_log(self.task_id, contact_id, email, company_name, 'sent')
                    sent_count += 1
                    increment_sent_count(self.task['account_id'])

                    # 更新进度
                    update_task_progress(self.task_id, sent_count, failed_count)

                    print(f"[Worker] 已发送 {sent_count}/{total} 到 {email}")

                    # 发送间隔(避免过快)
                    time.sleep(2)

                except Exception as e:
                    error_msg = str(e)
                    add_log(self.task_id, contact_id, email, company_name, 'failed', error_msg)
                    failed_count += 1
                    update_task_progress(self.task_id, sent_count, failed_count)
                    print(f"[Worker] 发送失败 {email}: {error_msg}")
                    # 继续发送下一个

            # 断开连接
            server.quit()

            # 完成任务
            if not self.stop_flag:
                complete_task(self.task_id, failed_count)

            # 发送报告邮件
            self.send_report_email(sent_count, failed_count)

        except Exception as e:
            error_task(self.task_id, str(e))
            print(f"[Worker] 任务出错: {e}")

    def send_report_email(self, sent_count, failed_count):
        """发送任务完成报告"""
        try:
            server = self.connect_smtp()

            subject = f"[开发信管理] 任务完成报告 - {self.task['task_name']}"
            body = f"""
            <html>
            <body>
            <h2>邮件任务完成报告</h2>
            <p><strong>任务名称:</strong> {self.task['task_name']}</p>
            <p><strong>发件人:</strong> {self.account['email']}</p>
            <p><strong>发送时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <p><strong>总收件人:</strong> {len(self.contacts)}</p>
            <p><strong style="color: green;">成功发送:</strong> {sent_count}</p>
            <p><strong style="color: red;">发送失败:</strong> {failed_count}</p>
            <hr>
            <p><em>此报告由系统自动发送</em></p>
            </body>
            </html>
            """

            message = MIMEMultipart()
            html_part = MIMEText(body, 'html', 'utf-8')
            message.attach(html_part)
            message['Subject'] = subject
            message['From'] = self.account['email']
            message['To'] = REPORT_EMAIL

            server.sendmail(self.account['email'], REPORT_EMAIL, message.as_string())
            server.quit()

            print(f"[Worker] 报告已发送到 {REPORT_EMAIL}")

        except Exception as e:
            print(f"[Worker] 发送报告失败: {e}")

    def start(self):
        """启动Worker线程"""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止Worker"""
        self.stop_flag = True


def start_email_worker(task_id):
    """启动邮件发送Worker

    Args:
        task_id: 任务ID

    Returns:
        EmailSenderWorker instance
    """
    worker = EmailSenderWorker(task_id)
    worker.start()
    return worker


def send_test_email(account_id, to_email, subject="测试邮件", body="<p>这是一封测试邮件</p>"):
    """发送测试邮件

    Args:
        account_id: 发件人账号ID
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容

    Returns:
        (success, message) tuple
    """
    try:
        account = get_account_by_id(account_id)
        if not account:
            return False, "发件人账号不存在"

        email = account['email']
        password = account['password']
        smtp_server = account.get('smtp_server', 'smtp.163.com')

        # 清除代理
        proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        proxy_backup = {k: os.environ.pop(k) for k in proxy_keys if k in os.environ}

        try:
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=20)
            server.login(email.strip(), password.strip())
        finally:
            os.environ.update(proxy_backup)

        message = MIMEMultipart()
        html_part = MIMEText(body, 'html', 'utf-8')
        message.attach(html_part)
        message['Subject'] = subject
        message['From'] = email
        message['To'] = to_email
        message['Cc'] = FIXED_CC_EMAIL

        server.sendmail(email, to_email, message.as_string())
        server.quit()

        return True, f"测试邮件已发送到 {to_email}"
    except Exception as e:
        return False, str(e)