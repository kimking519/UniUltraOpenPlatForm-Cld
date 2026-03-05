"""
order-pi-generator: 根据销售订单生成 Proforma Invoice (PI) 文件
用法:
  python make_pi.py --order_ids "d00001"
  python make_pi.py --order_ids "d00001,d00002,d00003"

创建时间: 2026-03-05
"""

import sqlite3
import sys
import os
import json
import argparse
from datetime import datetime
from copy import copy

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
except ImportError:
    print("错误: 请先安装 openpyxl -> pip install openpyxl")
    sys.exit(1)


# ============================================================
# 配置加载
# ============================================================

def load_config():
    """加载配置文件"""
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config"
    )

    config_path = None
    if os.path.isdir(config_dir):
        for f in sorted(os.listdir(config_dir), reverse=True):
            if f.endswith(".json"):
                config_path = os.path.join(config_dir, f)
                break

    if not config_path or not os.path.exists(config_path):
        print("错误: 配置文件不存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_db_path(config):
    """获取数据库路径"""
    env_path = os.environ.get("ORDER_PI_DB_PATH", "")
    if env_path and os.path.exists(env_path):
        return env_path

    if sys.platform == "win32":
        return config.get("db_path_windows", "")
    else:
        return config.get("db_path_wsl", "")


def get_output_base(config):
    """获取输出目录基础路径"""
    if sys.platform == "win32":
        return config.get("output_base_windows", "")
    else:
        return config.get("output_base_wsl", "")


# ============================================================
# 查询订单数据
# ============================================================

def query_orders(conn, order_ids):
    """查询订单记录及其关联的客户、报价信息"""
    placeholders = ','.join(['?'] * len(order_ids))
    sql = f"""
    SELECT
        o.order_id, o.order_no, o.order_date, o.cli_id,
        o.inquiry_mpn, o.inquiry_brand, o.price_rmb, o.price_kwr, o.price_usd,
        o.offer_id,
        c.cli_name, c.cli_name_en, c.contact_name, c.address, c.email, c.phone,
        off.quoted_qty, off.date_code, off.delivery_date, off.inquiry_qty
    FROM uni_order o
    LEFT JOIN uni_cli c ON o.cli_id = c.cli_id
    LEFT JOIN uni_offer off ON o.offer_id = off.offer_id
    WHERE o.order_id IN ({placeholders})
    ORDER BY o.order_id
    """
    rows = conn.execute(sql, order_ids).fetchall()
    return [dict(r) for r in rows]


# ============================================================
# 复制单元格样式
# ============================================================

def copy_cell_style(source_cell, target_cell):
    """复制单元格的样式"""
    if source_cell.font:
        target_cell.font = copy(source_cell.font)
    if source_cell.border:
        target_cell.border = copy(source_cell.border)
    if source_cell.fill:
        target_cell.fill = copy(source_cell.fill)
    if source_cell.alignment:
        target_cell.alignment = copy(source_cell.alignment)
    if source_cell.number_format:
        target_cell.number_format = source_cell.number_format


# ============================================================
# 生成PI文件
# ============================================================

def generate_pi(orders, template_path, output_path, invoice_no, cli_name):
    """
    基于模板生成PI Excel文件

    模板结构:
      R1-R15 = 头部信息
      R16 = 表头
      R17-R19 = 数据行
      R20 = 合计行
      R21-R35 = 固定内容(TERMS & CONDITIONS等)
    """
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    now = datetime.now()
    data_count = len(orders)

    if data_count == 0:
        return None

    # 获取第一个订单的客户信息
    first_order = orders[0]

    # ---- 1. 填写头部信息 ----
    # H9 = 日期 YYYY-MM-DD
    ws.cell(9, 8).value = now.strftime("%Y-%m-%d")

    # H10 = Invoice No.
    ws.cell(10, 8).value = invoice_no

    # B10 = 联系人
    ws.cell(10, 2).value = first_order.get("contact_name", "")

    # B11 = 公司英文名
    cli_name_en = first_order.get("cli_name_en", "")
    if not cli_name_en:
        cli_name_en = first_order.get("cli_name", "")
    ws.cell(11, 2).value = cli_name_en

    # B12 = 地址 (合并单元格 B12:H13)
    ws.cell(12, 2).value = first_order.get("address", "")

    # B14 = 邮箱
    ws.cell(14, 2).value = first_order.get("email", "")

    # B15 = 电话
    ws.cell(15, 2).value = first_order.get("phone", "")

    # ---- 2. 处理数据行 ----
    first_data_row = 17
    template_data_rows = 3  # 模板中有3行数据(17,18,19)
    footer_start_row = 20   # 合计行从20开始

    # 保存模板行的样式
    template_styles = {}
    for col in range(1, 9):
        cell = ws.cell(first_data_row, col)
        template_styles[col] = {
            "font": copy(cell.font) if cell.font else None,
            "border": copy(cell.border) if cell.border else None,
            "fill": copy(cell.fill) if cell.fill else None,
            "alignment": copy(cell.alignment) if cell.alignment else None,
            "number_format": cell.number_format,
        }

    # 获取行高
    template_row_height = ws.row_dimensions[first_data_row].height or 20.0

    # 根据数据量调整行
    if data_count > template_data_rows:
        # 需要插入新行
        rows_to_insert = data_count - template_data_rows
        ws.insert_rows(first_data_row + template_data_rows, rows_to_insert)

        # 设置新行的行高和样式
        for i in range(rows_to_insert):
            new_row = first_data_row + template_data_rows + i
            ws.row_dimensions[new_row].height = template_row_height
    elif data_count < template_data_rows:
        # 需要删除多余行
        rows_to_delete = template_data_rows - data_count
        ws.delete_rows(first_data_row + data_count, rows_to_delete)

    # 写入数据
    for idx, order in enumerate(orders):
        row = first_data_row + idx

        # A列 = Item (序号)
        ws.cell(row, 1).value = idx + 1

        # B列 = Part No. (型号)
        ws.cell(row, 2).value = order.get("inquiry_mpn", "")

        # C列 = Maker (品牌)
        ws.cell(row, 3).value = order.get("inquiry_brand", "")

        # D列 = QTY (报价数量) - 优先使用quoted_qty，其次inquiry_qty
        qty = order.get("quoted_qty") or order.get("inquiry_qty") or ""
        ws.cell(row, 4).value = qty

        # E列 = D/C (批号)
        ws.cell(row, 5).value = order.get("date_code", "")

        # F列 = L/T (货期)
        ws.cell(row, 6).value = order.get("delivery_date", "")

        # G列 = price/unit (KWR)
        price_kwr = order.get("price_kwr")
        if not price_kwr:
            price_kwr = order.get("price_rmb", "")
        ws.cell(row, 7).value = price_kwr

        # H列 = Total amount (KWR) = G * D
        if qty and price_kwr:
            try:
                ws.cell(row, 8).value = f"=G{row}*D{row}"
            except:
                ws.cell(row, 8).value = ""
        else:
            ws.cell(row, 8).value = ""

        # 应用样式
        for col in range(1, 9):
            cell = ws.cell(row, col)
            style = template_styles.get(col, {})
            if style.get("font"):
                cell.font = style["font"]
            if style.get("border"):
                cell.border = style["border"]
            if style.get("fill"):
                cell.fill = style["fill"]
            if style.get("alignment"):
                cell.alignment = style["alignment"]

    # ---- 3. 更新合计行 ----
    total_row = first_data_row + data_count
    last_data_row = total_row - 1

    # F20 = "Total amount："
    ws.cell(total_row, 6).value = "Total amount："

    # H20 = SUM(H17:H{last_data_row})
    ws.cell(total_row, 8).value = f"=SUM(H{first_data_row}:H{last_data_row})"

    # ---- 4. 保存文件 ----
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)
    return output_path


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="生成 Proforma Invoice (order-pi-generator)"
    )
    parser.add_argument("--order_ids", required=True,
                        help="订单编号，多个用逗号分隔")
    parser.add_argument("--db_path", default=None,
                        help="数据库路径（覆盖配置文件）")
    parser.add_argument("--output_dir", default=None,
                        help="输出目录（覆盖配置文件）")

    args = parser.parse_args()

    # 解析订单编号
    order_ids = [oid.strip() for oid in args.order_ids.split(",") if oid.strip()]
    if not order_ids:
        print("错误: 请提供至少一个订单编号")
        sys.exit(1)

    # 加载配置
    config = load_config()

    # 数据库路径
    db_path = args.db_path or get_db_path(config)
    if not db_path or not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在 {db_path}")
        sys.exit(1)

    # 输出目录
    output_base = args.output_dir or get_output_base(config)
    if not output_base:
        output_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "Trans"
        )

    # 模板路径
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(skill_root, "template")
    template_path = None
    if os.path.isdir(template_dir):
        for f in os.listdir(template_dir):
            if f.endswith(".xlsx"):
                template_path = os.path.join(template_dir, f)
                break

    if not template_path or not os.path.exists(template_path):
        print("错误: 模板文件不存在")
        sys.exit(1)

    # 查询数据
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        orders = query_orders(conn, order_ids)

        if not orders:
            print(f"错误: 订单编号 {order_ids} 不存在")
            sys.exit(1)

        # 检查是否找到所有订单
        found_ids = {o["order_id"] for o in orders}
        missing = set(order_ids) - found_ids
        if missing:
            print(f"警告: 以下订单编号未找到: {', '.join(missing)}")

        # 检查所有订单是否属于同一客户
        cli_names = set()
        for o in orders:
            name = o.get("cli_name") or "未知客户"
            cli_names.add(name)

        if len(cli_names) > 1:
            print(f"错误: 订单属于不同客户 ({', '.join(cli_names)})，无法生成同一份PI")
            sys.exit(1)

        cli_name = list(cli_names)[0]

        # 生成输出路径
        now = datetime.now()
        date_dir = now.strftime("%Y%m%d")
        invoice_no = now.strftime("UNI%Y%m%d%H%M%S")

        output_dir = os.path.join(output_base, cli_name, date_dir)
        output_filename = f"Proforma Invoice_{cli_name}_{invoice_no}.xlsx"
        output_path = os.path.join(output_dir, output_filename)

        # 生成PI
        result_path = generate_pi(orders, template_path, output_path, invoice_no, cli_name)

        if result_path:
            print(f"成功 PI生成成功！")
            print(f"文件路径: {result_path}")
            print(f"订单条数: {len(orders)}")
            print(f"客户: {cli_name}")
            print(f"Invoice No.: {invoice_no}")
        else:
            print("错误: PI生成失败")
            sys.exit(1)

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()