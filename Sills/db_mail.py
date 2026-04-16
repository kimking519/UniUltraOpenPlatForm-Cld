"""
邮件数据库操作层 - 汇总导入入口
将各功能模块统一导出，保持向后兼容性
"""

# 核心操作模块
from Sills.db_mail_core import (
    get_mail_list, get_mail_by_id, get_trash_list,
    save_email, batch_save_emails,
    delete_email, restore_email, permanently_delete_email,
    empty_trash, get_trash_count,
    batch_delete_emails, batch_permanently_delete_emails, batch_restore_emails,
    mark_email_read,
    save_draft, get_draft_list, get_draft_by_id, update_draft, delete_draft, get_draft_count,
    create_mail_relation, get_mail_relations, remove_mail_relation, remove_mail_relations_by_ref,
    get_latest_mail_time, get_local_uids, get_local_message_ids,
    cleanup_duplicate_emails, clear_account_emails
)

# 账户管理模块
from Sills.db_mail_account import (
    get_mail_config, get_all_mail_accounts, get_mail_account_by_id,
    add_mail_account, update_mail_account, switch_current_account, delete_mail_account
)

# 同步控制模块
from Sills.db_mail_sync import (
    update_mail_sync_status, acquire_sync_lock, update_sync_progress, get_sync_progress,
    release_sync_lock, is_sync_locked, recover_orphaned_syncs,
    get_sync_interval, set_sync_interval, get_sync_days, set_sync_days,
    get_undo_send_seconds, set_undo_send_seconds,
    get_folder_last_uid, update_folder_last_uid, get_all_folder_last_uids,
    get_signature, set_signature,
    get_sync_date_range, set_sync_date_range, clear_sync_date_range,
    record_synced_uid, batch_record_synced_uids, get_synced_uids, is_uid_synced,
    get_sync_deleted_setting, set_sync_deleted_setting
)

# 文件夹管理模块
from Sills.db_mail_folder import (
    get_folders, get_folder_by_id,
    get_or_create_sent_folder, get_or_create_draft_folder, get_or_create_spam_folder,
    get_or_create_system_folder, get_or_create_blacklist_folder,
    add_folder, update_folder, delete_folder, get_mail_count_by_folder,
    get_filter_rules, add_filter_rule, update_filter_rule, delete_filter_rule,
    auto_classify_emails, get_mails_by_folder,
    get_spam_list, get_spam_count,
    move_email_to_folder, move_emails_to_folder
)

# 黑名单管理模块
from Sills.db_mail_blacklist import (
    add_to_blacklist, remove_from_blacklist, get_blacklist_list, is_in_blacklist,
    get_blacklisted_list, get_blacklisted_count,
    mark_email_as_blacklisted, unmark_email_as_blacklisted,
    auto_classify_blacklist, get_unread_count
)

# 分类模块
from Sills.db_mail_classify import (
    MAIL_TYPE_KEYWORDS, BOUNCE_RECIPIENT_PATTERNS,
    extract_original_recipient, classify_mail_by_subject, classify_mails
)

# 为了兼容性，保留 _clean_text 函数
def _clean_text(text):
    """
    清理文本中的 NUL 字符（PostgreSQL 不支持字符串中的 NUL 字符）
    """
    if text is None:
        return None
    if isinstance(text, str):
        return text.replace('\x00', '')
    return text