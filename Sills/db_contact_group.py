"""
联系人组管理数据库操作模块
用于邮件任务管理中的联系人分组
"""
import sqlite3
import json
from datetime import datetime
from Sills.base import get_db_connection


def get_next_group_id():
    """获取下一个联系人组ID (GP+时间戳+随机数格式)"""
    import random
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    rand_suffix = random.randint(1000, 9999)
    return f"GP{timestamp}{rand_suffix}"


def get_group_list(page=1, page_size=20, search_kw=""):
    """获取联系人组列表"""
    offset = (page - 1) * page_size
    where_clause = ""
    params = []

    if search_kw:
        where_clause = "WHERE group_name LIKE ?"
        params = [f"%{search_kw}%"]

    query = f"""
    SELECT * FROM uni_contact_group
    {where_clause}
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
    """

    count_query = f"SELECT COUNT(*) FROM uni_contact_group {where_clause}"

    with get_db_connection() as conn:
        total = conn.execute(count_query, params).fetchone()[0]
        items = conn.execute(query, params + [page_size, offset]).fetchall()
        results = [
            {k: ("" if v is None else v) for k, v in dict(row).items()}
            for row in items
        ]
        return results, total


def get_group_by_id(group_id):
    """根据ID获取联系人组详情"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM uni_contact_group WHERE group_id = ?",
            (group_id,)
        ).fetchone()
        if row:
            return {k: ("" if v is None else v) for k, v in dict(row).items()}
        return None


def add_group(group_name, filter_criteria=None):
    """添加联系人组

    Args:
        group_name: 组名称
        filter_criteria: dict 筛选条件 {country, domain, is_bounced, has_cli}

    Returns:
        (success, message) tuple
    """
    try:
        if not group_name or not group_name.strip():
            return False, "组名称不能为空"

        group_id = get_next_group_id()
        criteria_json = json.dumps(filter_criteria) if filter_criteria else ""

        # 计算符合条件的联系人数量
        contact_count = count_contacts_by_criteria(filter_criteria)

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO uni_contact_group (group_id, group_name, filter_criteria, contact_count)
                VALUES (?, ?, ?, ?)
            """, (group_id, group_name.strip(), criteria_json, contact_count))
            conn.commit()

        return True, f"联系人组 {group_id} 创建成功，包含 {contact_count} 个联系人"
    except Exception as e:
        return False, str(e)


def update_group(group_id, group_name=None, filter_criteria=None):
    """更新联系人组"""
    try:
        updates = []
        params = []

        if group_name:
            updates.append("group_name = ?")
            params.append(group_name.strip())

        if filter_criteria is not None:
            updates.append("filter_criteria = ?")
            params.append(json.dumps(filter_criteria))
            # 重新计算联系人数量
            contact_count = count_contacts_by_criteria(filter_criteria)
            updates.append("contact_count = ?")
            params.append(contact_count)

        if not updates:
            return True, "无需更新"

        updates.append("updated_at = NOW()")
        params.append(group_id)

        sql = f"UPDATE uni_contact_group SET {', '.join(updates)} WHERE group_id = ?"

        with get_db_connection() as conn:
            conn.execute(sql, params)
            conn.commit()

        return True, "更新成功"
    except Exception as e:
        return False, str(e)


def delete_group(group_id):
    """删除联系人组"""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM uni_contact_group WHERE group_id = ?", (group_id,))
            conn.commit()
        return True, "删除成功"
    except Exception as e:
        return False, str(e)


def count_contacts_by_criteria(criteria):
    """根据筛选条件统计联系人数量

    Args:
        criteria: dict {country, countries, domain, cli_id, send_status, read_status, bounce_status, send_count, last_sent_days, has_cli}

    Returns:
        int 符合条件的联系人数
    """
    if not criteria:
        with get_db_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM uni_contact WHERE email IS NOT NULL AND email != ''").fetchone()[0]

    where_clauses = ["email IS NOT NULL AND email != ''"]
    params = []

    # 特定客户筛选（优先级最高）
    if criteria.get('cli_id'):
        where_clauses.append("cli_id = ?")
        params.append(criteria['cli_id'])

    # 是否关联客户（勾选）
    if criteria.get('has_cli'):
        where_clauses.append("cli_id IS NOT NULL AND cli_id != ''")

    # 国家筛选（支持单选和多选）
    # 国家筛选需要通过 uni_prospect 表关联，因为 uni_contact.country 都是空的
    country_filter = None
    if criteria.get('countries'):
        countries_list = criteria['countries']
        if isinstance(countries_list, list) and len(countries_list) > 0:
            country_filter = countries_list
    elif criteria.get('country'):
        country_filter = [criteria['country']]

    if country_filter:
        # 先从 uni_prospect 查找该国家对应的 domain
        with get_db_connection() as conn:
            placeholders = ','.join(['?' for _ in country_filter])
            domains = conn.execute(
                f"SELECT DISTINCT domain FROM uni_prospect WHERE country IN ({placeholders}) AND domain IS NOT NULL AND domain != ''",
                country_filter
            ).fetchall()
            domain_list = [d[0] for d in domains if d[0]]

        if domain_list:
            # 再从 uni_contact 查找匹配这些 domain 的联系人
            placeholders = ','.join(['?' for _ in domain_list])
            where_clauses.append(f"domain IN ({placeholders})")
            params.extend(domain_list)
        else:
            # 该国家没有对应的 domain，返回 0
            return 0

    if criteria.get('domain'):
        where_clauses.append("domain LIKE ?")
        params.append(f"%{criteria['domain']}%")

    # 发送状态
    if criteria.get('send_status') is not None:
        if criteria['send_status'] == 0:
            where_clauses.append("send_count = 0")
        else:
            where_clauses.append("send_count > 0")

    # 已读状态
    if criteria.get('read_status') is not None:
        where_clauses.append("is_read = ?")
        params.append(criteria['read_status'])

    # 退信状态
    if criteria.get('bounce_status') is not None:
        where_clauses.append("is_bounced = ?")
        params.append(criteria['bounce_status'])

    # 发送次数范围
    send_count_range = criteria.get('send_count')
    if send_count_range:
        if send_count_range == '0':
            where_clauses.append("send_count = 0")
        elif send_count_range == '1-3':
            where_clauses.append("send_count BETWEEN 1 AND 3")
        elif send_count_range == '4+':
            where_clauses.append("send_count >= 4")

    # 最后联系时间（X天内未联系）
    last_sent_days = criteria.get('last_sent_days')
    if last_sent_days:
        where_clauses.append(
            "(last_sent_at IS NULL OR datetime(last_sent_at) < datetime('now', 'localtime', '-{} days'))".format(last_sent_days)
        )

    where_sql = "WHERE " + " AND ".join(where_clauses)

    with get_db_connection() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM uni_contact {where_sql}", params).fetchone()[0]


def get_group_contacts(group_id, page=1, page_size=100):
    """获取联系人组内的联系人列表

    Args:
        group_id: 组ID
        page: 页码
        page_size: 每页数量

    Returns:
        (contacts_list, total) tuple
    """
    group = get_group_by_id(group_id)
    if not group:
        return [], 0

    criteria = json.loads(group.get('filter_criteria', '{}') or '{}')

    offset = (page - 1) * page_size
    where_clauses = ["c.email IS NOT NULL AND c.email != ''"]
    params = []

    # 特定客户筛选（优先级最高）
    if criteria.get('cli_id'):
        where_clauses.append("c.cli_id = ?")
        params.append(criteria['cli_id'])

    # 是否关联客户（勾选）
    if criteria.get('has_cli'):
        where_clauses.append("c.cli_id IS NOT NULL AND c.cli_id != ''")

    # 国家筛选（支持单选和多选）
    # 国家筛选需要通过 uni_prospect 表关联，因为 uni_contact.country 都是空的
    country_filter = None
    if criteria.get('countries'):
        countries_list = criteria['countries']
        if isinstance(countries_list, list) and len(countries_list) > 0:
            country_filter = countries_list
    elif criteria.get('country'):
        country_filter = [criteria['country']]

    if country_filter:
        # 先从 uni_prospect 查找该国家对应的 domain
        with get_db_connection() as conn:
            placeholders = ','.join(['?' for _ in country_filter])
            domains = conn.execute(
                f"SELECT DISTINCT domain FROM uni_prospect WHERE country IN ({placeholders}) AND domain IS NOT NULL AND domain != ''",
                country_filter
            ).fetchall()
            domain_list = [d[0] for d in domains if d[0]]

        if domain_list:
            # 再从 uni_contact 查找匹配这些 domain 的联系人
            placeholders = ','.join(['?' for _ in domain_list])
            where_clauses.append(f"c.domain IN ({placeholders})")
            params.extend(domain_list)
        else:
            # 该国家没有对应的 domain，返回空结果
            return [], 0

    if criteria.get('domain'):
        where_clauses.append("c.domain LIKE ?")
        params.append(f"%{criteria['domain']}%")

    # 发送状态
    if criteria.get('send_status') is not None:
        if criteria['send_status'] == 0:
            where_clauses.append("c.send_count = 0")
        else:
            where_clauses.append("c.send_count > 0")

    # 已读状态
    if criteria.get('read_status') is not None:
        where_clauses.append("c.is_read = ?")
        params.append(criteria['read_status'])

    # 退信状态
    if criteria.get('bounce_status') is not None:
        where_clauses.append("c.is_bounced = ?")
        params.append(criteria['bounce_status'])

    # 发送次数范围
    send_count_range = criteria.get('send_count')
    if send_count_range:
        if send_count_range == '0':
            where_clauses.append("c.send_count = 0")
        elif send_count_range == '1-3':
            where_clauses.append("c.send_count BETWEEN 1 AND 3")
        elif send_count_range == '4+':
            where_clauses.append("c.send_count >= 4")

    # 最后联系时间
    last_sent_days = criteria.get('last_sent_days')
    if last_sent_days:
        where_clauses.append(
            "(c.last_sent_at IS NULL OR datetime(c.last_sent_at) < datetime('now', 'localtime', '-{} days'))".format(last_sent_days)
        )

    where_sql = "WHERE " + " AND ".join(where_clauses)

    query = f"""
    SELECT c.contact_id, c.cli_id, c.email, c.domain, c.contact_name,
           CASE WHEN c.country IS NOT NULL AND c.country != '' THEN c.country ELSE p.country END as country,
           c.position, c.phone, c.company, c.is_bounced, c.is_read,
           c.send_count, c.bounce_count, c.read_count, c.last_sent_at, c.remark,
           p.prospect_name
    FROM uni_contact c
    LEFT JOIN uni_prospect p ON c.domain = p.domain
    {where_sql}
    ORDER BY c.email
    LIMIT ? OFFSET ?
    """

    count_query = f"SELECT COUNT(*) FROM uni_contact c {where_sql}"

    with get_db_connection() as conn:
        total = conn.execute(count_query, params).fetchone()[0]
        items = conn.execute(query, params + [page_size, offset]).fetchall()
        results = [
            {k: ("" if v is None else v) for k, v in dict(row).items()}
            for row in items
        ]
        return results, total


def get_all_groups_contacts(group_ids):
    """获取多个组的合并联系人列表(去重)

    Args:
        group_ids: list 组ID列表

    Returns:
        list 合并去重后的联系人列表
    """
    all_contacts = {}

    for group_id in group_ids:
        contacts, _ = get_group_contacts(group_id, page_size=1000)  # 获取全部
        for c in contacts:
            # 以email为key去重
            email = c.get('email', '').lower()
            if email and email not in all_contacts:
                all_contacts[email] = c

    return list(all_contacts.values())