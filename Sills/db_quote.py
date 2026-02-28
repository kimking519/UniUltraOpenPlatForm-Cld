import sqlite3
import uuid
from datetime import datetime
from Sills.base import get_db_connection

def get_quote_list(page=1, page_size=10, search_kw="", start_date="", end_date="", cli_id="", status="", is_transferred=""):
    offset = (page - 1) * page_size
    
    base_query = """
    FROM uni_quote q
    LEFT JOIN uni_cli c ON q.cli_id = c.cli_id
    WHERE (q.inquiry_mpn LIKE ? OR q.quote_id LIKE ? OR c.cli_name LIKE ?)
    """
    params = [f"%{search_kw}%", f"%{search_kw}%", f"%{search_kw}%"]
    
    if start_date:
        base_query += " AND q.quote_date >= ?"
        params.append(start_date)
    if end_date:
        base_query += " AND q.quote_date <= ?"
        params.append(end_date)
    if cli_id:
        base_query += " AND q.cli_id = ?"
        params.append(cli_id)
    if status:
        base_query += " AND q.status = ?"
        params.append(status)
    if is_transferred:
        base_query += " AND q.is_transferred = ?"
        params.append(is_transferred)
        
    query = f"""
    SELECT q.*, c.cli_name, 
           (COALESCE(q.quoted_mpn, '') || ' | ' || 
            COALESCE(q.inquiry_brand, '') || ' | ' || 
            COALESCE(CAST(q.inquiry_qty AS TEXT), '') || ' pcs | ' ||
            COALESCE(q.date_code, '') || ' | ' ||
            COALESCE(q.delivery_date, '') || ' | ' ||
            COALESCE(q.is_transferred, '未转') || ' | ' || 
            COALESCE(q.remark, '')) as combined_info
    {base_query}
    ORDER BY q.created_at DESC
    LIMIT ? OFFSET ?
    """
    
    count_query = f"SELECT COUNT(*) {base_query}"
    
    with get_db_connection() as conn:
        total = conn.execute(count_query, params).fetchone()[0]
        items = conn.execute(query, params + [page_size, offset]).fetchall()
        
        results = [
            {k: ("" if v is None else v) for k, v in dict(row).items()}
            for row in items
        ]
        return results, total

def add_quote(data):
    try:
        quote_id = "Q" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4]
        quote_date = datetime.now().strftime("%Y-%m-%d")
        sql = """
        INSERT INTO uni_quote (quote_id, quote_date, cli_id, inquiry_mpn, quoted_mpn, inquiry_brand, inquiry_qty, target_price_rmb, cost_price_rmb, date_code, delivery_date, status, remark, is_transferred)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '未转')
        """
        params = (
            quote_id,
            quote_date,
            data.get('cli_id'),
            data.get('inquiry_mpn'),
            data.get('quoted_mpn', ''),
            data.get('inquiry_brand', ''),
            data.get('inquiry_qty', 0),
            data.get('target_price_rmb', 0.0),
            data.get('cost_price_rmb', 0.0),
            data.get('date_code', ''),
            data.get('delivery_date', ''),
            data.get('status', '询价中'),
            data.get('remark', '')
        )
        with get_db_connection() as conn:
            conn.execute(sql, params)
            conn.commit()
            return True, f"需求 {quote_id} 创建成功"
    except Exception as e:
        return False, str(e)

def batch_import_quote_text(text):
    lines = text.strip().split('\n')
    success_count = 0
    errors = []
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 1: continue
        
        try:
            data = {
                "cli_id": parts[0],
                "inquiry_mpn": parts[1] if len(parts) > 1 else "",
                "quoted_mpn": parts[2] if len(parts) > 2 else "",
                "inquiry_brand": parts[3] if len(parts) > 3 else "",
                "inquiry_qty": int(parts[4]) if len(parts) > 4 and parts[4] else 0,
                "target_price_rmb": float(parts[5]) if len(parts) > 5 and parts[5] else 0.0,
                "cost_price_rmb": float(parts[6]) if len(parts) > 6 and parts[6] else 0.0,
                "date_code": parts[7] if len(parts) > 7 else "",
                "delivery_date": parts[8] if len(parts) > 8 else "",
                "status": parts[9] if len(parts) > 9 else "询价中",
                "remark": parts[10] if len(parts) > 10 else ""
            }
            if not data["cli_id"] or not data["inquiry_mpn"]:
                errors.append(f"{line}: 缺少必填的客户或型号")
                continue
                
            ok, msg = add_quote(data)
            if ok: success_count += 1
            else: errors.append(f"{parts[1]}: {msg}")
        except Exception as e:
            errors.append(f"{line}: 数据格式解析失败 ({str(e)})")
            
    return success_count, errors

def update_quote(quote_id, data):
    try:
        set_cols = []
        params = []
        for k, v in data.items():
            set_cols.append(f"{k} = ?")
            params.append(v)
        if not set_cols: return True, "No changes"
        
        sql = f"UPDATE uni_quote SET {', '.join(set_cols)} WHERE quote_id = ?"
        params.append(quote_id)
        
        with get_db_connection() as conn:
            conn.execute(sql, params)
            conn.commit()
            return True, "更新成功"
    except Exception as e:
        return False, str(e)

def delete_quote(quote_id):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM uni_quote WHERE quote_id = ?", (quote_id,))
            conn.commit()
            return True, "删除成功"
    except Exception as e:
        return False, str(e)

def batch_delete_quote(quote_ids):
    if not quote_ids: return True, "无选中记录"
    try:
        with get_db_connection() as conn:
            placeholders = ','.join(['?'] * len(quote_ids))
            conn.execute(f"DELETE FROM uni_quote WHERE quote_id IN ({placeholders})", quote_ids)
            conn.commit()
            return True, "批量删除成功"
    except Exception as e:
        if "FOREIGN KEY constraint failed" in str(e):
            return False, "删除失败：部分记录已被[报价订单]引用，请先删除对应的报价。"
        return False, str(e)

def batch_copy_quote(quote_ids):
    if not quote_ids: return True, "无选中记录"
    try:
        with get_db_connection() as conn:
            placeholders = ','.join(['?'] * len(quote_ids))
            rows = conn.execute(f"SELECT * FROM uni_quote WHERE quote_id IN ({placeholders})", quote_ids).fetchall()
            
            for row in rows:
                import uuid
                from datetime import datetime
                new_id = "Q" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4]
                sql = """
                INSERT INTO uni_quote (quote_id, quote_date, cli_id, inquiry_mpn, quoted_mpn, inquiry_brand, inquiry_qty, target_price_rmb, cost_price_rmb, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                conn.execute(sql, (
                    new_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    row['cli_id'],
                    row['inquiry_mpn'],
                    row['quoted_mpn'],
                    row['inquiry_brand'],
                    row['inquiry_qty'],
                    row['target_price_rmb'],
                    row['cost_price_rmb'],
                    row['remark']
                ))
            conn.commit()
            return True, "批量复制成功"
    except Exception as e:
        return False, str(e)

def batch_copy_quote(quote_ids):
    try:
        if not quote_ids: return True, "未选择数据"
        with get_db_connection() as conn:
            success_count = 0
            for q_id in quote_ids:
                row = conn.execute("SELECT * FROM uni_quote WHERE quote_id=?", (q_id,)).fetchone()
                if row:
                    new_id = "Q" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4]
                    d = dict(row)
                    sql = """
                    INSERT INTO uni_quote (quote_id, quote_date, cli_id, inquiry_mpn, quoted_mpn, inquiry_brand, inquiry_qty, target_price_rmb, cost_price_rmb, date_code, delivery_date, status, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        new_id,
                        datetime.now().strftime("%Y-%m-%d"),
                        d.get('cli_id'),
                        d.get('inquiry_mpn'),
                        d.get('quoted_mpn'),
                        d.get('inquiry_brand'),
                        d.get('inquiry_qty'),
                        d.get('target_price_rmb'),
                        d.get('cost_price_rmb'),
                        d.get('date_code'),
                        d.get('delivery_date'),
                        d.get('status'),
                        d.get('remark')
                    )
                    conn.execute(sql, params)
                    success_count += 1
            conn.commit()
            return True, f"成功复制 {success_count} 条记录"
    except Exception as e:
        return False, str(e)
