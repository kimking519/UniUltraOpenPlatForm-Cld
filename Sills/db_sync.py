"""
联系人数据同步模块
实现 Prospect <-> Contact <-> uni_mail 三方数据同步
"""
import os
import threading
from datetime import datetime
from Sills.base import get_db_connection

# 同步状态控制（使用线程安全的Event和Lock）
_sync_stop_event = threading.Event()  # 用于停止信号
_sync_lock = threading.Lock()  # 用于状态锁
_sync_thread = None
_sync_progress = {
    'step': '',
    'current': 0,
    'total': 0,
    'message': ''
}


def is_sync_running():
    """检查同步是否正在运行"""
    return _sync_thread is not None and _sync_thread.is_alive() and not _sync_stop_event.is_set()


def get_sync_status():
    """获取同步状态"""
    with _sync_lock:
        running = is_sync_running()
        progress = _sync_progress.copy()
    return {
        'running': running,
        'progress': progress
    }


def stop_sync():
    """停止同步"""
    _sync_stop_event.set()  # 设置停止信号
    return True


def should_stop():
    """检查是否应该停止"""
    return _sync_stop_event.is_set()


def update_progress(step=None, current=None, total=None, message=None):
    """更新进度（线程安全）"""
    with _sync_lock:
        if step:
            _sync_progress['step'] = step
        if current is not None:
            _sync_progress['current'] = current
        if total is not None:
            _sync_progress['total'] = total
        if message:
            _sync_progress['message'] = message


def sync_all_data():
    """
    执行完整同步流程（3步骤）
    1. Prospect → Contact: 同步 prospect_name, country
    2. Contact → Prospect: 统计联系人数量
    3. uni_mail → Contact: 统计邮件发送/退信/已读
    """
    # 重置停止信号
    _sync_stop_event.clear()

    with _sync_lock:
        _sync_progress = {'step': '准备开始', 'current': 0, 'total': 0, 'message': ''}

    try:
        # Step 1: Prospect → Contact
        if should_stop():
            return False, '同步已停止'

        update_progress(step='Step 1: Prospect → Contact', message='同步Prospect名称和国家到联系人')
        step1_result = sync_prospect_to_contact()
        if not step1_result:
            return False, 'Step 1 同步已停止'

        # Step 2: Contact → Prospect
        if should_stop():
            return False, '同步已停止'

        update_progress(step='Step 2: Contact → Prospect', message='统计联系人数量')
        step2_result = sync_contact_count_to_prospect()
        if not step2_result:
            return False, 'Step 2 同步已停止'

        # Step 3: uni_mail → Contact
        if should_stop():
            return False, '同步已停止'

        update_progress(step='Step 3: uni_mail → Contact', message='统计邮件发送数据')
        step3_result = sync_mail_stats_to_contact()
        if not step3_result:
            return False, 'Step 3 同步已停止'

        update_progress(step='完成', message='同步完成')
        return True, '同步完成'

    except Exception as e:
        update_progress(step='错误', message=str(e))
        return False, str(e)


def sync_prospect_to_contact():
    """Step 1: Prospect → Contact 通过domain同步prospect_name和country"""
    with get_db_connection() as conn:
        # 获取所有Prospect
        prospects = conn.execute(
            "SELECT prospect_id, prospect_name, domain, country FROM uni_prospect"
        ).fetchall()

        update_progress(total=len(prospects))
        updated_count = 0

        for i, p in enumerate(prospects):
            if should_stop():
                return False

            update_progress(current=i + 1, message=f'同步: {p["prospect_name"]}')

            if p['domain']:
                # 更新匹配domain的Contact
                conn.execute("""
                    UPDATE uni_contact
                    SET prospect_name = ?, country = COALESCE(country, ?)
                    WHERE domain = ?
                """, (p['prospect_name'], p['country'], p['domain']))
                updated_count += 1

        conn.commit()

    return True


def sync_contact_count_to_prospect():
    """Step 2: Contact → Prospect 统计每个Prospect的联系人数量"""
    with get_db_connection() as conn:
        # 获取所有Prospect
        prospects = conn.execute(
            "SELECT prospect_id, domain FROM uni_prospect"
        ).fetchall()

        update_progress(total=len(prospects), current=0)

        for i, p in enumerate(prospects):
            if should_stop():
                return False

            update_progress(current=i + 1)

            if p['domain']:
                # 统计匹配domain的Contact数量
                count = conn.execute(
                    "SELECT COUNT(*) FROM uni_contact WHERE domain = ?",
                    (p['domain'],)
                ).fetchone()[0]

                conn.execute(
                    "UPDATE uni_prospect SET contact_count = ? WHERE prospect_id = ?",
                    (count, p['prospect_id'])
                )

        conn.commit()

    return True


def sync_mail_stats_to_contact():
    """Step 3: uni_mail → Contact 统计邮件发送/退信/已读数据

    统计逻辑：
    - send_count = 成功发送邮件 + 退信邮件（所有发送尝试）
    - bounce_count = mail_type=3 的退信邮件（使用original_recipient匹配）
    - read_count = mail_type=1 已读回执 + 无回执信息的邮件（视为已读）
    - unread_count = mail_type=2 未读回执邮件（收件人信息在content字段）
    """
    from urllib.parse import unquote
    import re

    def purify_email(email):
        """邮箱提纯：URL解码、正则提取"""
        if not email:
            return ''
        decoded = unquote(email)
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, decoded)
        if match:
            return match.group(0).lower().strip()
        return ''

    def extract_recipient_from_content(content, sender_email='joy@unicornsemi.com'):
        """从邮件内容提取真正的收件人邮箱（用于未读回执）"""
        if not content:
            return ''
        # 提取所有邮箱
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, content.lower())
        # 过滤掉发送方邮箱，返回第一个非发送方的邮箱
        for email in emails:
            if email != sender_email:
                return email
        return ''

    with get_db_connection() as conn:
        # Step 3.1: 统计发送次数（成功发送的邮件，to_addr匹配）
        if should_stop():
            return False

        update_progress(step='Step 3: 统计发送次数', message='批量统计邮件发送数据...')

        # 成功发送的邮件（is_sent=1，非退信邮件）
        sent_stats = conn.execute("""
            SELECT to_addr, COUNT(*) as cnt
            FROM uni_mail
            WHERE is_sent = 1 AND mail_type != 3
            GROUP BY to_addr
        """).fetchall()

        send_map = {}
        for row in sent_stats:
            if should_stop():
                return False
            emails = extract_emails_from_addr(row['to_addr'])
            for email in emails:
                send_map[email] = send_map.get(email, 0) + row['cnt']

        update_progress(current=20)

        # Step 3.2: 统计退信次数（使用original_recipient）
        # 同时将退信计入send_count（因为这也是发送尝试）
        if should_stop():
            return False

        update_progress(step='Step 3: 统计退信次数', message='批量统计退信数据...')

        bounce_stats = conn.execute("""
            SELECT original_recipient, COUNT(*) as cnt
            FROM uni_mail
            WHERE mail_type = 3 AND original_recipient IS NOT NULL AND original_recipient != ''
            GROUP BY original_recipient
        """).fetchall()

        bounce_map = {}
        for row in bounce_stats:
            if should_stop():
                return False
            emails = extract_emails_from_addr(row['original_recipient'])
            for email in emails:
                bounce_map[email] = bounce_map.get(email, 0) + row['cnt']
                # 退信也计入发送次数（发送尝试）
                send_map[email] = send_map.get(email, 0) + row['cnt']

        update_progress(current=40)

        # Step 3.3: 统计已读回执次数（mail_type=1）
        # 已读回执的to_addr是发送方，实际收件人需从content提取
        if should_stop():
            return False

        update_progress(step='Step 3: 统计已读回执', message='批量统计已读回执数据...')

        read_receipt_mails = conn.execute("""
            SELECT content, COUNT(*) as cnt
            FROM uni_mail
            WHERE mail_type = 1 AND content IS NOT NULL AND content != ''
            GROUP BY content
        """).fetchall()

        read_map = {}
        for row in read_receipt_mails:
            if should_stop():
                return False
            # 从content提取实际收件人
            recipient = extract_recipient_from_content(row['content'])
            if recipient:
                read_map[recipient] = read_map.get(recipient, 0) + row['cnt']

        update_progress(current=60)

        # Step 3.4: 统计未读回执次数（mail_type=2）
        # 未读回执的to_addr是发送方，实际收件人需从content提取
        if should_stop():
            return False

        update_progress(step='Step 3: 统计未读回执', message='批量统计未读回执数据...')

        unread_receipt_mails = conn.execute("""
            SELECT content, COUNT(*) as cnt
            FROM uni_mail
            WHERE mail_type = 2 AND content IS NOT NULL AND content != ''
            GROUP BY content
        """).fetchall()

        unread_map = {}
        for row in unread_receipt_mails:
            if should_stop():
                return False
            # 从content提取实际收件人
            recipient = extract_recipient_from_content(row['content'])
            if recipient:
                unread_map[recipient] = unread_map.get(recipient, 0) + row['cnt']

        update_progress(current=80, total=100)

        # Step 3.5: 批量更新联系人
        if should_stop():
            return False

        update_progress(step='Step 3: 更新联系人', message='批量更新联系人数据...')

        contacts = conn.execute(
            "SELECT contact_id, email FROM uni_contact WHERE email IS NOT NULL AND email != ''"
        ).fetchall()

        updated_count = 0
        for c in contacts:
            if should_stop():
                conn.commit()
                update_progress(message=f'已停止，更新了 {updated_count} 个联系人')
                return False

            email = purify_email(c['email'])
            send_count = send_map.get(email, 0)
            bounce_count = bounce_map.get(email, 0)
            read_receipt_count = read_map.get(email, 0)  # mail_type=1 已读回执数
            unread_receipt_count = unread_map.get(email, 0)  # mail_type=2 未读回执数

            # 已读包含：已读回执 + 无回执的邮件（未知状态视为已读）
            # 无回执邮件数 = 发送数 - 退信数 - 已读回执数 - 未读回执数
            unknown_count = max(0, send_count - bounce_count - read_receipt_count - unread_receipt_count)
            total_read = read_receipt_count + unknown_count

            conn.execute("""
                UPDATE uni_contact
                SET send_count = ?, bounce_count = ?, read_count = ?,
                    is_bounced = CASE WHEN ? > 0 THEN 1 ELSE 0 END,
                    is_read = CASE WHEN ? > 0 THEN 1 ELSE 0 END
                WHERE contact_id = ?
            """, (send_count, bounce_count, total_read, bounce_count, total_read, c['contact_id']))
            updated_count += 1

        conn.commit()
        update_progress(current=100, message=f'已更新 {updated_count} 个联系人')

    return True


def extract_emails_from_addr(addr):
    """从地址字段提取所有邮箱地址"""
    if not addr:
        return []

    import re
    from urllib.parse import unquote

    # URL解码
    decoded = unquote(addr)

    # 匹配邮箱格式
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, decoded.lower())
    return emails


def run_sync_async():
    """异步执行同步（用于后台任务）"""
    global _sync_thread

    if is_sync_running():
        return False, '同步任务正在运行中'

    _sync_thread = threading.Thread(target=sync_all_data)
    _sync_thread.start()
    return True, '同步任务已启动'