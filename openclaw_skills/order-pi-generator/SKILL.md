---
name: order-pi-generator
description: >
  根据销售订单生成 Proforma Invoice (PI) 文件。
  当用户提到"生成PI"、"PI文件"、"发票"、"Proforma Invoice"、
  或在订单管理页面选择订单后要求生成PI时使用此skill。
---

# 订单PI生成器

根据选中的销售订单信息，自动生成 Proforma Invoice Excel 文件。

---

## 前置条件

- Python 3.x
- openpyxl 库 (`pip install openpyxl`)
- SQLite 数据库访问权限

---

## 工作流程

### 第一步：获取订单数据

从数据库查询选中订单的完整信息，包括：
- 订单基本信息（型号、品牌、价格）
- 客户信息（联系人、公司名、地址、邮箱、电话）
- 关联报价信息（数量、批号、货期）

### 第二步：数据验证

- 检查所有订单是否属于同一客户
- 验证必要字段是否完整

### 第三步：生成PI文件

基于模板填充数据：
- 头部信息：客户联系人、公司英文名、地址、邮箱、电话
- 日期和发票号：自动生成
- 数据行：动态插入，包含型号、品牌、数量、批号、货期、单价、总价
- 合计行：自动计算总金额

### 第四步：输出

- 输出目录：`E:\1_Business\1_Auto\{客户名}\{日期yyyymmdd}`
- 文件名：`Proforma Invoice_{客户名}_{发票号}.xlsx`

---

## 示例

### 输入示例
```
订单编号: d00001, d00002, d00003
```

### 输出示例
```
文件路径: E:\1_Business\1_Auto\TAEJU\20260305\Proforma Invoice_TAEJU_UNI20260305143000.xlsx
订单条数: 3
客户: TAEJU
Invoice No.: UNI20260305143000
```

---

## 注意事项 / 边缘情况

- 订单必须属于同一客户，否则拒绝生成
- 如果订单没有关联报价单，QTY/D/C/L/T 字段为空
- 支持跨平台路径（Windows/WSL）
- 动态行数：根据订单数量自动插入或删除行

---

## 配置说明

配置文件位于 `config/db_config.json`：

| 配置项 | 说明 |
|--------|------|
| db_path_windows | Windows 数据库路径 |
| db_path_wsl | WSL 数据库路径 |
| output_base_windows | Windows 输出目录 |
| output_base_wsl | WSL 输出目录 |

环境变量 `ORDER_PI_DB_PATH` 可覆盖数据库路径配置。

---

## 目录结构

```
order-pi-generator/
├── SKILL.md                    # 本文档
├── config/
│   └── db_config.json          # 配置文件
├── scripts/
│   └── make_pi.py              # PI生成脚本
└── template/
    └── Proforma_Invoice_template.xlsx  # PI模板