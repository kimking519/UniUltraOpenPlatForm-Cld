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
import shutil
import zipfile
from datetime import datetime
from copy import copy
from xml.etree import ElementTree as ET

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
# XML命名空间
# ============================================================

NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}


def get_cell_value_element(sheet_xml, row, col):
    """获取指定单元格的值元素"""
    # 列字母转换
    col_letter = ''
    temp = col
    while temp > 0:
        temp -= 1
        col_letter = chr(temp % 26 + ord('A')) + col_letter
        temp //= 26

    cell_ref = f"{col_letter}{row}"

    # 查找单元格
    for row_elem in sheet_xml.findall('.//main:row', NS):
        if row_elem.get('r') == str(row):
            for c in row_elem.findall('main:c', NS):
                if c.get('r') == cell_ref:
                    return c
    return None


def set_cell_value(sheet_xml, row, col, value, shared_strings=None):
    """设置单元格值（直接修改XML）"""
    from xml.etree.ElementTree import SubElement

    # 列字母转换
    col_letter = ''
    temp = col
    while temp > 0:
        temp -= 1
        col_letter = chr(temp % 26 + ord('A')) + col_letter
        temp //= 26

    cell_ref = f"{col_letter}{row}"

    # 查找或创建行元素
    sheet_data = sheet_xml.find('main:sheetData', NS)
    row_elem = None
    for r in sheet_data.findall('main:row', NS):
        if r.get('r') == str(row):
            row_elem = r
            break

    if row_elem is None:
        row_elem = SubElement(sheet_data, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
        row_elem.set('r', str(row))

    # 查找或创建单元格元素
    cell_elem = None
    for c in row_elem.findall('main:c', NS):
        if c.get('r') == cell_ref:
            cell_elem = c
            break

    if cell_elem is None:
        cell_elem = SubElement(row_elem, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
        cell_elem.set('r', cell_ref)

    # 设置值
    if value is not None and value != '':
        # 检查是否是数字
        try:
            num_val = float(value)
            cell_elem.set('t', 'n')
            v_elem = cell_elem.find('main:v', NS)
            if v_elem is None:
                v_elem = SubElement(cell_elem, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            v_elem.text = str(num_val if num_val != int(num_val) else int(num_val))
        except (ValueError, TypeError):
            # 字符串值
            cell_elem.set('t', 'str')
            v_elem = cell_elem.find('main:v', NS)
            if v_elem is None:
                v_elem = SubElement(cell_elem, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            v_elem.text = str(value)
    else:
        # 清空值
        v_elem = cell_elem.find('main:v', NS)
        if v_elem is not None:
            cell_elem.remove(v_elem)


# ============================================================
# 生成PI文件
# ============================================================

def generate_pi(orders, template_path, output_path, invoice_no, cli_name):
    """
    基于模板生成PI Excel文件，保留图片等所有内容
    """
    now = datetime.now()
    data_count = len(orders)

    if data_count == 0:
        return None

    # 获取第一个订单的客户信息
    first_order = orders[0]

    # 复制模板文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copy2(template_path, output_path)

    # 临时解压目录
    temp_dir = output_path + '_temp'
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # 解压xlsx文件
    with zipfile.ZipFile(output_path, 'r') as z:
        z.extractall(temp_dir)

    # 读取sheet1.xml
    sheet_path = os.path.join(temp_dir, 'xl', 'worksheets', 'sheet1.xml')
    ET.register_namespace('', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')

    tree = ET.parse(sheet_path)
    root = tree.getroot()

    # ---- 修改单元格值 ----
    # H9 = 日期 YYYY-MM-DD
    set_cell_value(root, 9, 8, now.strftime("%Y-%m-%d"))

    # H10 = Invoice No.
    set_cell_value(root, 10, 8, invoice_no)

    # B10 = 联系人
    set_cell_value(root, 10, 2, first_order.get("contact_name", ""))

    # B11 = 公司英文名
    cli_name_en = first_order.get("cli_name_en", "") or first_order.get("cli_name", "")
    set_cell_value(root, 11, 2, cli_name_en)

    # B12 = 地址
    set_cell_value(root, 12, 2, first_order.get("address", ""))

    # B14 = 邮箱
    set_cell_value(root, 14, 2, first_order.get("email", ""))

    # B15 = 电话
    set_cell_value(root, 15, 2, first_order.get("phone", ""))

    # ---- 处理数据行 ----
    # 注意：XML方式暂时不支持动态增删行，这里使用openpyxl处理行调整
    # 先保存XML修改
    tree.write(sheet_path, xml_declaration=True, encoding='UTF-8')

    # 使用openpyxl处理行调整和数据写入
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active

    first_data_row = 17
    template_data_rows = 3

    # 保存样式
    row_styles = {}
    for col in range(1, 9):
        cell = ws.cell(first_data_row, col)
        row_styles[col] = {
            "font": copy(cell.font) if cell.font else None,
            "border": copy(cell.border) if cell.border else None,
            "fill": copy(cell.fill) if cell.fill else None,
            "alignment": copy(cell.alignment) if cell.alignment else None,
        }

    template_height = ws.row_dimensions[first_data_row].height or 20.0

    # 调整行数
    if data_count > template_data_rows:
        rows_to_insert = data_count - template_data_rows
        ws.insert_rows(20, rows_to_insert)
        for i in range(rows_to_insert):
            new_row = first_data_row + template_data_rows + i
            ws.row_dimensions[new_row].height = template_height
    elif data_count < template_data_rows:
        rows_to_delete = template_data_rows - data_count
        ws.delete_rows(first_data_row + data_count, rows_to_delete)

    total_row = first_data_row + data_count
    last_data_row = total_row - 1

    # 写入数据
    for idx, order in enumerate(orders):
        row = first_data_row + idx

        ws.cell(row, 1).value = idx + 1
        ws.cell(row, 2).value = order.get("inquiry_mpn", "")
        ws.cell(row, 3).value = order.get("inquiry_brand", "")

        qty = order.get("quoted_qty") or order.get("inquiry_qty") or ""
        ws.cell(row, 4).value = qty

        ws.cell(row, 5).value = order.get("date_code", "")
        ws.cell(row, 6).value = order.get("delivery_date", "")

        price_kwr = order.get("price_kwr", "")
        ws.cell(row, 7).value = price_kwr

        if qty and price_kwr:
            ws.cell(row, 8).value = f"=G{row}*D{row}"
        else:
            ws.cell(row, 8).value = ""

        # 应用样式
        for col in range(1, 9):
            cell = ws.cell(row, col)
            style = row_styles.get(col, {})
            if style.get("font"):
                cell.font = style["font"]
            if style.get("border"):
                cell.border = style["border"]
            if style.get("fill"):
                cell.fill = style["fill"]
            if style.get("alignment"):
                cell.alignment = style["alignment"]

    # 更新合计行
    ws.cell(total_row, 6).value = "Total amount："
    ws.cell(total_row, 8).value = f"=SUM(H{first_data_row}:H{last_data_row})"

    # 保存（这会丢失图片）
    wb.save(output_path)

    # 恢复图片：重新解压原始模板，复制图片和drawing相关文件
    with zipfile.ZipFile(template_path, 'r') as z:
        for name in z.namelist():
            if 'media' in name or 'drawing' in name:
                # 提取到临时目录
                z.extract(name, temp_dir)

    # 将图片和drawing文件添加到生成的文件中
    with zipfile.ZipFile(output_path, 'a') as z:
        for root_dir, dirs, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root_dir, file)
                arc_name = os.path.relpath(full_path, temp_dir)
                if 'media' in arc_name or 'drawing' in arc_name:
                    z.write(full_path, arc_name)

    # 清理临时目录
    shutil.rmtree(temp_dir)

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
        invoice_no = now.strftime("UNI%Y%m%d%H")

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