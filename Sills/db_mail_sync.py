"""
邮件数据库操作层 - 同步控制模块
包含：同步锁、进度管理、UID记录、日期范围设置、签名
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from Sills.base import get_db_connection
from Sills.db_config import get_datetime_now


def update_mail_sync_status(mail_id: int, status: str, error: str = None) -> bool:
    """
    更新邮件同步状态

    Args:
        mail_id: 邮件ID
        status: 状态 ('pending', 'completed', 'failed')
        error: 错误信息（可选）

    Returns:
        是否更新成功
    """
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE uni_mail SET sync_status = ?, sync_error = ? WHERE id = ?
        """, (status, error, mail_id))
        conn.commit()
        return True


def acquire_sync_lock(lock_id: str) -> bool:
    """
    获取同步锁

    Args:
        lock_id: 锁标识符（进程/线程ID）

    Returns:
        True=获取成功，False=已被锁定
    """
    now = datetime.now()
    expires_at = now + timedelta(minutes=60)  # 60分钟超时，支持大批量同步

    with get_db_connection() as conn:
        # 检查是否存在过期锁
        row = conn.execute("SELECT * FROM mail_sync_lock WHERE id = 1").fetchone()
        if row:
            lock = dict(row)
            if lock.get('expires_at'):
                # PostgreSQL 返回 datetime 对象，SQLite 返回字符串
                expires = lock['expires_at']
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                if expires > now:
                    return False  # 锁仍然有效

        # 获取或更新锁（包含进度字段）
        conn.execute("""
            INSERT INTO mail_sync_lock (id, locked_at, locked_by, expires_at, progress_total, progress_current, progress_message)
            VALUES (1, ?, ?, ?, 0, 0, '初始化中...')
            ON CONFLICT(id) DO UPDATE SET
                locked_at = excluded.locked_at,
                locked_by = excluded.locked_by,
                expires_at = excluded.expires_at,
                progress_total = 0,
                progress_current = 0,
                progress_message = '初始化中...'
        """, (now.isoformat(), lock_id, expires_at.isoformat()))
        conn.commit()
        return True


def update_sync_progress(current: int, total: int, message: str = "",
                          sync_start_date: str = None, sync_end_date: str = None,
                          total_emails: int = None, synced_emails: int = None) -> bool:
    """
    更新同步进度
    """
    with get_db_connection() as conn:
        # 构建动态更新语句
        updates = ["progress_current = ?", "progress_total = ?", "progress_message = ?"]
        params = [current, total, message]

        if sync_start_date is not None:
            updates.append("sync_start_date = ?")
            params.append(sync_start_date)
        if sync_end_date is not None:
            updates.append("sync_end_date = ?")
            params.append(sync_end_date)
        if total_emails is not None:
            updates.append("total_emails = ?")
            params.append(total_emails)
        if synced_emails is not None:
            updates.append("synced_emails = ?")
            params.append(synced_emails)

        sql = f"UPDATE mail_sync_lock SET {', '.join(updates)} WHERE id = 1"
        conn.execute(sql, params)
        conn.commit()
        return True


def get_sync_progress() -> Dict[str, Any]:
    """
    获取同步进度
    """
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM mail_sync_lock WHERE id = 1").fetchone()
        if row:
            lock = dict(row)
            if lock.get('expires_at'):
                expires = lock['expires_at']
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                if expires > datetime.now():
                    total_emails = lock.get('total_emails', 0) or 0
                    synced_emails = lock.get('synced_emails', 0) or 0
                    percent = int((synced_emails / total_emails) * 100) if total_emails > 0 else 0
                    return {
                        "syncing": True,
                        "current": lock.get('progress_current', 0) or 0,
                        "total": lock.get('progress_total', 0) or 0,
                        "message": lock.get('progress_message', '') or '',
                        "status": "syncing",
                        "sync_start_date": lock.get('sync_start_date', '') or '',
                        "sync_end_date": lock.get('sync_end_date', '') or '',
                        "total_emails": total_emails,
                        "synced_emails": synced_emails,
                        "percent": percent
                    }
    return {
        "syncing": False,
        "current": 0,
        "total": 0,
        "message": "",
        "status": "idle",
        "sync_start_date": "",
        "sync_end_date": "",
        "total_emails": 0,
        "synced_emails": 0,
        "percent": 0
    }


def release_sync_lock() -> bool:
    """释放同步锁"""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM mail_sync_lock WHERE id = 1")
        conn.commit()
        return True


def is_sync_locked() -> bool:
    """检查同步锁是否有效"""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM mail_sync_lock WHERE id = 1").fetchone()
        if row:
            lock = dict(row)
            if lock.get('expires_at'):
                expires = lock['expires_at']
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                return expires > datetime.now()
    return False


def recover_orphaned_syncs() -> int:
    """
    恢复孤立的同步记录（标记超过5分钟的pending为failed）
    """
    cutoff = datetime.now() - timedelta(minutes=5)

    with get_db_connection() as conn:
        result = conn.execute("""
            UPDATE uni_mail
            SET sync_status = 'failed', sync_error = 'Sync timeout - orphaned task'
            WHERE sync_status = 'pending'
            AND created_at < ?
        """, (cutoff.isoformat(),))
        conn.commit()
        return result.rowcount


def get_sync_interval() -> int:
    """获取同步间隔（分钟）"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'sync_interval'"
        ).fetchone()
        if row:
            return int(row[0])
    return 30  # 默认30分钟


def set_sync_interval(minutes: int) -> bool:
    """设置同步间隔（分钟）"""
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('sync_interval', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (str(minutes),))
        conn.commit()
        return True


def get_sync_days() -> int:
    """获取同步时间范围（天）"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'sync_days'"
        ).fetchone()
        if row:
            return int(row[0])
    return 90  # 默认90天


def set_sync_days(days: int) -> bool:
    """设置同步时间范围（天）"""
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('sync_days', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (str(days),))
        conn.commit()
        return True


def get_undo_send_seconds() -> int:
    """获取发送撤销时间（秒）"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'undo_send_seconds'"
        ).fetchone()
        if row:
            return int(row[0])
    return 5  # 默认5秒


def set_undo_send_seconds(seconds: int) -> bool:
    """设置发送撤销时间（秒）"""
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('undo_send_seconds', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (str(seconds),))
        conn.commit()
        return True


def get_folder_last_uid(account_id: int, folder_name: str) -> int:
    """
    获取文件夹最后同步的UID
    """
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT last_uid FROM mail_folder_sync_progress WHERE account_id = ? AND folder_name = ?",
            (account_id, folder_name)
        ).fetchone()
        return row[0] if row else 0


def update_folder_last_uid(account_id: int, folder_name: str, last_uid: int) -> bool:
    """
    更新文件夹最后同步的UID
    """
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO mail_folder_sync_progress (account_id, folder_name, last_uid, last_sync_at)
            VALUES (?, ?, ?, {dt_now})
            ON CONFLICT(account_id, folder_name) DO UPDATE SET
                last_uid = excluded.last_uid,
                last_sync_at = excluded.last_sync_at
        """, (account_id, folder_name, last_uid))
        conn.commit()
        return True


def get_all_folder_last_uids(account_id: int) -> dict:
    """
    获取所有文件夹的最后同步UID
    """
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT folder_name, last_uid FROM mail_folder_sync_progress WHERE account_id = ?",
            (account_id,)
        ).fetchall()
        return {row[0]: row[1] for row in rows}


def get_signature() -> str:
    """获取邮件签名"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'email_signature'"
        ).fetchone()
        if row:
            return row[0] or ''
    return ''


def set_signature(signature: str) -> bool:
    """设置邮件签名"""
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('email_signature', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (signature,))
        conn.commit()
        return True


def get_sync_date_range() -> tuple:
    """
    获取自定义同步日期范围
    """
    with get_db_connection() as conn:
        start_row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'sync_start_date'"
        ).fetchone()
        end_row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'sync_end_date'"
        ).fetchone()
        if start_row and end_row:
            return (start_row[0], end_row[0])
    return (None, None)


def set_sync_date_range(start_date: str, end_date: str) -> bool:
    """
    设置自定义同步日期范围
    """
    dt_now = get_datetime_now()
    with get_db_connection() as conn:
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('sync_start_date', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (start_date,))
        conn.execute(f"""
            INSERT INTO global_settings (key, value, updated_at)
            VALUES ('sync_end_date', ?, {dt_now})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (end_date,))
        conn.commit()
        return True


def clear_sync_date_range() -> bool:
    """清除自定义同步日期范围"""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM global_settings WHERE key IN ('sync_start_date', 'sync_end_date')")
        conn.commit()
        return True


# ==================== 已同步UID记录 ====================

def record_synced_uid(account_id: int, imap_uid: int, imap_folder: str) -> bool:
    """
    记录已同步的邮件UID
    """
    with get_db_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO uni_mail_synced_uid (account_id, imap_uid, imap_folder)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id, imap_uid, imap_folder) DO NOTHING
            """, (account_id, imap_uid, imap_folder))
            conn.commit()
            return True
        except Exception as e:
            print(f"Record synced UID error: {e}")
            return False


def batch_record_synced_uids(account_id: int, uid_folder_pairs: list) -> bool:
    """
    批量记录已同步的邮件UID
    """
    if not uid_folder_pairs:
        return True

    with get_db_connection() as conn:
        try:
            for uid, folder in uid_folder_pairs:
                conn.execute("""
                    INSERT INTO uni_mail_synced_uid (account_id, imap_uid, imap_folder)
                    VALUES (?, ?, ?)
                    ON CONFLICT(account_id, imap_uid, imap_folder) DO NOTHING
                """, (account_id, uid, folder))
            conn.commit()
            return True
        except Exception as e:
            print(f"Batch record synced UIDs error: {e}")
            return False


def get_synced_uids(account_id: int, folder: str = None) -> set:
    """
    获取已同步的UID集合
    """
    with get_db_connection() as conn:
        if folder:
            rows = conn.execute(
                "SELECT imap_uid FROM uni_mail_synced_uid WHERE account_id = ? AND imap_folder = ?",
                (account_id, folder)
            ).fetchall()
            return {row[0] for row in rows}
        else:
            rows = conn.execute(
                "SELECT imap_uid, imap_folder FROM uni_mail_synced_uid WHERE account_id = ?",
                (account_id,)
            ).fetchall()
            return {(row[0], row[1]) for row in rows}


def is_uid_synced(account_id: int, imap_uid: int, imap_folder: str) -> bool:
    """
    检查UID是否已同步过
    """
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT 1 FROM uni_mail_synced_uid
            WHERE account_id = ? AND imap_uid = ? AND imap_folder = ?
        """, (account_id, imap_uid, imap_folder)).fetchone()
        return row is not None


def get_sync_deleted_setting() -> bool:
    """
    获取"同步已删除邮件"开关设置
    """
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM global_settings WHERE key = 'sync_deleted_emails'"
        ).fetchone()
        # 默认开启（True）
        if row is None:
            return True
        return row[0].lower() in ('true', '1', 'yes')


def set_sync_deleted_setting(enabled: bool) -> bool:
    """
    设置"同步已删除邮件"开关
    """
    with get_db_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO global_settings (key, value, updated_at)
                VALUES ('sync_deleted_emails', ?, NOW())
                ON CONFLICT (key) DO UPDATE SET value = ?, updated_at = NOW()
            """, (str(enabled).lower(), str(enabled).lower()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Set sync deleted setting error: {e}")
            return False