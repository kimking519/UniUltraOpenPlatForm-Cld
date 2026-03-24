# UniUltraOpenPlatForm 产品需求文档 (PRD)

**版本**: v1.0
**日期**: 2026-03-24
**文档状态**: 正式发布

---

## 1. 产品概述

### 1.1 产品背景

UniUltraOpenPlatForm（统一超开放平台）是一款专为**电子元器件贸易企业**设计的企业资源规划（ERP）系统。系统覆盖从客户询价到采购交付的完整销售流程，帮助企业实现业务流程数字化、数据管理规范化。

### 1.2 目标用户

- **电子元器件贸易公司**：从事芯片、电子元器件进出口贸易的企业
- **业务类型**：B2B贸易，主要面向韩国、美国等海外市场
- **用户角色**：销售经理、采购专员、财务人员、企业管理者

### 1.3 核心价值

| 价值维度 | 描述 |
|---------|------|
| 流程闭环 | 实现询价→报价→订单→采购的完整业务闭环 |
| 数据统一 | 统一管理客户、供应商、产品、订单等核心数据 |
| 效率提升 | 自动化汇率计算、状态流转、数据转换 |
| 决策支持 | 实时统计销售数据、利润分析 |

---

## 2. 系统架构

### 2.1 技术栈

| 层级 | 技术选型 |
|-----|---------|
| 后端框架 | FastAPI (Python) |
| 数据库 | SQLite3 (WAL模式) |
| 前端 | Jinja2 + Vanilla JavaScript |
| 文档生成 | openpyxl (Excel/CI/PI) |
| 邮件服务 | IMAP4/SMTP |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端展示层                            │
│              (Jinja2 Templates + JavaScript)                │
├─────────────────────────────────────────────────────────────┤
│                        业务逻辑层                            │
│                    (FastAPI Routes)                         │
├─────────────────────────────────────────────────────────────┤
│                        数据操作层                            │
│    (db_emp, db_cli, db_quote, db_offer, db_order, db_buy)   │
├─────────────────────────────────────────────────────────────┤
│                        数据存储层                            │
│                   (SQLite3 + WAL Mode)                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 部署架构

- **单机部署**：支持 Windows / Linux / WSL 环境
- **端口**：默认 8000
- **数据库**：单文件数据库，便于备份迁移

---

## 3. 功能模块详细设计

### 3.1 用户认证与权限管理

#### 3.1.1 功能描述

| 功能 | 描述 |
|-----|------|
| 登录认证 | 账号密码登录，MD5加密存储 |
| 权限控制 | 四级权限体系 |
| 会话管理 | Cookie-based Session |
| 密码修改 | 首次登录强制修改密码 |

#### 3.1.2 权限等级

| 等级 | 名称 | 权限范围 |
|-----|------|---------|
| 0 | 超级管理员 | 所有权限，可绕过所有检查 |
| 1 | 只读用户 | 仅查看数据，无修改权限 |
| 2 | 编辑用户 | 可新增、修改数据，不可删除 |
| 3 | 管理员 | 完整CRUD权限 |
| 4 | 禁用账户 | 无法登录系统 |

#### 3.1.3 默认账户

```
管理员账号: Admin
默认密码: uni519
```

---

### 3.2 员工管理模块

#### 3.2.1 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 员工列表 | GET /emp | 分页查询，支持搜索 |
| 新增员工 | POST /emp/add | 自动生成3位编号 |
| 编辑员工 | POST /api/emp/update | 字段级更新 |
| 删除员工 | POST /api/emp/delete | 管理员权限 |
| 批量导入 | POST /emp/import | CSV/文本导入 |
| 修改密码 | POST /change_password | 强制首次修改 |

#### 3.2.2 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| emp_id | TEXT(3) | 是 | 员工编号，格式：001, 002... |
| emp_name | TEXT | 是 | 员工姓名 |
| account | TEXT | 是 | 登录账号（唯一） |
| password | TEXT | 是 | MD5加密密码 |
| department | TEXT | 否 | 部门 |
| position | TEXT | 否 | 职位 |
| contact | TEXT | 否 | 联系方式 |
| hire_date | TEXT | 否 | 入职日期 |
| rule | TEXT | 是 | 权限等级 1-4 |
| remark | TEXT | 否 | 备注 |

---

### 3.3 客户管理模块

#### 3.3.1 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 客户列表 | GET /cli | 分页查询，支持搜索 |
| 新增客户 | POST /cli/add | 自动生成C开头编号 |
| 编辑客户 | POST /api/cli/update | 字段级更新 |
| 删除客户 | POST /api/cli/delete | 检查关联数据 |
| 批量导入 | POST /cli/import | CSV/文本导入 |
| 批量删除 | POST /api/cli/batch_delete | 批量操作 |

#### 3.3.2 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| cli_id | TEXT | 是 | 客户编号，格式：C001, C002... |
| cli_name | TEXT | 是 | 客户简称 |
| cli_full_name | TEXT | 否 | 客户全称 |
| cli_name_en | TEXT | 否 | 英文名称 |
| contact_name | TEXT | 否 | 联系人 |
| region | TEXT | 是 | 地区，默认"韩国" |
| credit_level | TEXT | 否 | 信用等级 A/B/C/D |
| margin_rate | REAL | 否 | 利润率%，默认10.0 |
| emp_id | TEXT | 是 | 关联员工ID |
| email | TEXT | 否 | 邮箱地址 |
| phone | TEXT | 否 | 电话 |
| address | TEXT | 否 | 地址 |
| website | TEXT | 否 | 网站 |
| payment_terms | TEXT | 否 | 付款条件 |
| remark | TEXT | 否 | 备注 |

---

### 3.4 供应商管理模块

#### 3.4.1 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 供应商列表 | GET /vendor | 分页查询 |
| 新增供应商 | POST /vendor/add | 自动生成V开头编号 |
| 编辑供应商 | POST /api/vendor/update | 字段级更新 |
| 删除供应商 | POST /api/vendor/delete | 检查关联 |

#### 3.4.2 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| vendor_id | TEXT | 是 | 供应商编号，格式：V001... |
| vendor_name | TEXT | 是 | 供应商名称 |
| address | TEXT | 否 | 地址 |
| qq | TEXT | 否 | QQ号 |
| wechat | TEXT | 否 | 微信号 |
| email | TEXT | 否 | 邮箱 |
| remark | TEXT | 否 | 备注 |

---

### 3.5 需求管理模块（询价）

#### 3.5.1 业务流程

```
客户询价 → 登记需求 → 报价处理 → 转报价单
```

#### 3.5.2 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 需求列表 | GET /quote | 多条件筛选 |
| 新增需求 | POST /quote/add | 自动生成x开头编号 |
| 编辑需求 | POST /api/quote/update | 字段级更新 |
| 删除需求 | POST /api/quote/delete | 检查是否已转报价 |
| 批量导入 | POST /quote/import | CSV/文本导入 |
| 批量删除 | POST /api/quote/batch_delete | 批量操作 |
| 批量复制 | POST /api/quote/batch_copy | 快速复制 |
| 转报价单 | POST /api/offer/batch_convert | 批量转换 |
| 导出CSV | POST /api/quote/export_offer_csv | 数据导出 |

#### 3.5.3 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| quote_id | TEXT | 是 | 需求编号，格式：x00001 |
| quote_date | TEXT | 是 | 需求日期 |
| cli_id | TEXT | 是 | 关联客户ID |
| inquiry_mpn | TEXT | 是 | 询价型号（物料编号） |
| quoted_mpn | TEXT | 否 | 报价型号，默认=询价型号 |
| inquiry_brand | TEXT | 否 | 品牌 |
| inquiry_qty | INTEGER | 否 | 需求数量 |
| actual_qty | INTEGER | 否 | 实际数量 |
| target_price_rmb | REAL | 否 | 目标价(RMB) |
| cost_price_rmb | REAL | 否 | 成本价(RMB) |
| date_code | TEXT | 否 | 批号，默认3年内 |
| delivery_date | TEXT | 否 | 交期，默认1~3days |
| status | TEXT | 否 | 状态：询价中/已报价/已失效 |
| is_transferred | TEXT | 否 | 已转：未转/已转 |
| remark | TEXT | 否 | 备注 |

#### 3.5.4 业务规则

1. **编号生成**：递增5位数，格式 `x00001`
2. **默认值**：
   - 批号：当前日期+3年
   - 交期：1~3days
3. **状态流转**：询价中 → 已报价
4. **转换限制**：已转报价的需求不可删除

---

### 3.6 报价管理模块

#### 3.6.1 业务流程

```
需求转报价 → 填写成本/报价 → 转销售订单
```

#### 3.6.2 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 报价列表 | GET /offer | 多条件筛选 |
| 新增报价 | POST /offer/add | 自动生成b开头编号 |
| 编辑报价 | POST /api/offer/update | 联动更新订单价格 |
| 删除报价 | POST /api/offer/delete | 检查关联订单 |
| 批量导入 | POST /offer/import | CSV/文本导入 |
| 批量删除 | POST /api/offer/batch_delete | 批量操作 |
| 转销售订单 | POST /api/order/batch_convert | 批量转换 |

#### 3.6.3 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| offer_id | TEXT | 是 | 报价编号，格式：b00001 |
| offer_date | TEXT | 是 | 报价日期 |
| quote_id | TEXT | 否 | 关联需求ID（唯一约束） |
| inquiry_mpn | TEXT | 是 | 询价型号 |
| quoted_mpn | TEXT | 否 | 报价型号 |
| inquiry_brand | TEXT | 否 | 询价品牌 |
| quoted_brand | TEXT | 否 | 报价品牌 |
| inquiry_qty | INTEGER | 否 | 询价数量 |
| actual_qty | INTEGER | 否 | 实际数量 |
| quoted_qty | INTEGER | 否 | 报价数量 |
| cost_price_rmb | REAL | 否 | 成本价(RMB) |
| offer_price_rmb | REAL | 否 | 报价(RMB) |
| price_kwr | REAL | 否 | 韩元价格（自动计算） |
| price_usd | REAL | 否 | 美元价格（自动计算） |
| platform | TEXT | 否 | 平台 |
| vendor_id | TEXT | 否 | 供应商ID |
| date_code | TEXT | 否 | 批号 |
| delivery_date | TEXT | 否 | 交期 |
| emp_id | TEXT | 是 | 员工ID |
| offer_statement | TEXT | 否 | 报价声明 |
| is_transferred | TEXT | 否 | 已转：未转/已转 |
| remark | TEXT | 否 | 备注 |

#### 3.6.4 业务规则

1. **编号生成**：递增5位数，格式 `b00001`
2. **自动报价**：根据客户利润率自动计算报价
   ```
   报价 = 成本价 × (1 + 利润率%)
   ```
3. **汇率换算**：实时汇率自动计算KRW/USD价格
4. **唯一约束**：一个需求只能转一个报价

---

### 3.7 销售订单模块

#### 3.7.1 业务流程

```
报价转订单 → 订单执行 → 收款 → 完成
```

#### 3.7.2 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 订单列表 | GET /order | 多条件筛选 |
| 新增订单 | POST /order/add | 自动生成d开头编号 |
| 编辑订单 | POST /api/order/update | 字段级更新 |
| 更新状态 | POST /api/order/update_status | 完成/付款状态 |
| 删除订单 | POST /api/order/delete | 检查采购关联 |
| 批量导入 | POST /order/import | CSV/文本导入 |
| 批量删除 | POST /api/order/batch_delete | 批量操作 |
| 转采购单 | POST /api/buy/batch_convert | 批量转换 |

#### 3.7.3 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| order_id | TEXT | 是 | 订单ID，格式：d00001 |
| order_no | TEXT | 是 | 订单编号（唯一） |
| order_date | TEXT | 是 | 订单日期 |
| cli_id | TEXT | 是 | 客户ID |
| offer_id | TEXT | 否 | 关联报价ID |
| inquiry_mpn | TEXT | 否 | 型号 |
| inquiry_brand | TEXT | 否 | 品牌 |
| price_rmb | REAL | 否 | 销售价(RMB) |
| price_kwr | REAL | 否 | 韩元价格 |
| price_usd | REAL | 否 | 美元价格 |
| cost_price_rmb | REAL | 否 | 成本价(RMB) |
| is_finished | INTEGER | 否 | 是否完成 0/1 |
| is_paid | INTEGER | 否 | 是否付款 0/1 |
| paid_amount | REAL | 否 | 已付金额 |
| return_status | TEXT | 否 | 退货状态：正常/退货中/已退货 |
| is_transferred | TEXT | 否 | 已转采购：未转/已转 |
| remark | TEXT | 否 | 备注 |

#### 3.7.4 业务规则

1. **编号生成**：递增5位数，格式 `d00001`
2. **利润计算**：
   ```
   利润 = 销售价 - 成本价
   总利润 = 利润 × 数量
   ```
3. **状态跟踪**：完成状态、付款状态、退货状态

---

### 3.8 采购管理模块

#### 3.8.1 业务流程

```
订单转采购 → 确认货源 → 下单 → 入库 → 发货
```

#### 3.8.2 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 采购列表 | GET /buy | 多条件筛选 |
| 新增采购 | POST /buy/add | 自动生成c开头编号 |
| 编辑采购 | POST /api/buy/update | 字段级更新 |
| 更新节点 | POST /api/buy/update_node | 货源/下单/入库/发货 |
| 删除采购 | POST /api/buy/delete | 单条删除 |
| 批量导入 | POST /buy/import | CSV/文本导入 |
| 批量删除 | POST /api/buy/batch_delete | 批量操作 |

#### 3.8.3 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| buy_id | TEXT | 是 | 采购ID，格式：c00001 |
| buy_date | TEXT | 是 | 采购日期 |
| order_id | TEXT | 否 | 关联订单ID |
| vendor_id | TEXT | 否 | 供应商ID |
| buy_mpn | TEXT | 否 | 采购型号 |
| buy_brand | TEXT | 否 | 采购品牌 |
| buy_price_rmb | REAL | 否 | 采购单价(RMB) |
| buy_qty | INTEGER | 否 | 采购数量 |
| sales_price_rmb | REAL | 否 | 销售单价(RMB) |
| total_amount | REAL | 否 | 总金额（自动计算） |
| is_source_confirmed | INTEGER | 否 | 货源确认 0/1 |
| is_ordered | INTEGER | 否 | 已下单 0/1 |
| is_instock | INTEGER | 否 | 已入库 0/1 |
| is_shipped | INTEGER | 否 | 已发货 0/1 |
| remark | TEXT | 否 | 备注 |

#### 3.8.4 采购节点流程

```
货源确认 → 已下单 → 已入库 → 已发货
```

---

### 3.9 汇率管理模块

#### 3.9.1 功能清单

| 功能 | API路由 | 描述 |
|-----|--------|------|
| 汇率列表 | GET /daily | 查询历史汇率 |
| 新增汇率 | POST /daily/add | 添加每日汇率 |
| 更新汇率 | POST /api/daily/update | 修改汇率 |

#### 3.9.2 数据结构

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| id | INTEGER | 是 | 自增ID |
| record_date | TEXT | 是 | 记录日期 |
| currency_code | INTEGER | 是 | 货币代码：1=USD, 2=KRW |
| exchange_rate | REAL | 是 | 汇率值 |
| created_at | DATETIME | 否 | 创建时间 |

#### 3.9.3 汇率使用规则

- **KRW汇率**：1 RMB = X KRW
- **USD汇率**：1 RMB = X USD
- 系统自动获取最新汇率进行价格换算

---

### 3.10 邮件中心模块

#### 3.10.1 功能概述

集成IMAP/SMTP邮件服务，支持多账户管理、邮件同步、分类管理。

#### 3.10.2 功能清单

| 功能 | 描述 |
|-----|------|
| 多账户管理 | 支持多个邮箱账户配置与切换 |
| 邮件同步 | IMAP增量同步收件箱 |
| 文件夹管理 | 自定义邮件分类文件夹 |
| 过滤规则 | 关键词自动分类 |
| 黑名单 | 垃圾邮件过滤 |
| 回收站 | 删除邮件恢复 |
| 邮件关联 | 关联客户/订单/报价 |
| 智能回复 | AI智能回复建议（预留） |

#### 3.10.3 数据表结构

**mail_config（邮件配置）**

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 账户ID |
| account_name | TEXT | 账户名称 |
| smtp_server | TEXT | SMTP服务器 |
| smtp_port | INTEGER | SMTP端口 |
| imap_server | TEXT | IMAP服务器 |
| imap_port | INTEGER | IMAP端口 |
| username | TEXT | 用户名 |
| password | TEXT | 加密密码 |
| use_tls | INTEGER | 是否TLS |
| is_current | INTEGER | 是否当前账户 |

**uni_mail（邮件表）**

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 邮件ID |
| subject | TEXT | 主题 |
| from_addr | TEXT | 发件人地址 |
| from_name | TEXT | 发件人名称 |
| to_addr | TEXT | 收件人 |
| cc_addr | TEXT | 抄送 |
| content | TEXT | 纯文本内容 |
| html_content | TEXT | HTML内容 |
| received_at | DATETIME | 接收时间 |
| sent_at | DATETIME | 发送时间 |
| is_sent | INTEGER | 是否已发送 |
| is_read | INTEGER | 是否已读 |
| is_deleted | INTEGER | 是否删除 |
| folder_id | INTEGER | 文件夹ID |
| account_id | INTEGER | 账户ID |
| message_id | TEXT | 邮件唯一标识 |
| imap_uid | INTEGER | IMAP UID |

---

### 3.11 系统设置模块

#### 3.11.1 功能清单

| 功能 | 描述 |
|-----|------|
| 数据备份 | 手动/自动数据库备份 |
| 系统信息 | 服务器环境、内存状态 |
| 邮件配置 | 邮件账户设置 |

#### 3.11.2 自动备份

- **备份间隔**：每30分钟自动备份
- **保留策略**：保留最近3天备份
- **备份内容**：数据库文件(.db)、静态资源(static/)

---

## 4. 业务实体关系

### 4.1 实体关系图（ER图）

```
uni_emp (员工)
    │
    └──▶ uni_cli (客户)
              │
              ├──▶ uni_quote (询价/需求)
              │         │
              │         └──▶ uni_offer (报价)
              │                   │
              │                   └──▶ uni_order (销售订单)
              │                             │
              │                             └──▶ uni_buy (采购)
              │
              └──▶ uni_vendor (供应商)
```

### 4.2 ID生成规则

| 实体 | 前缀 | 格式 | 示例 |
|-----|------|------|------|
| 员工 | 无 | 3位数字 | 001, 002 |
| 客户 | C | C + 3位数字 | C001, C002 |
| 供应商 | V | V + 3位数字 | V001, V002 |
| 需求 | x | x + 5位数字 | x00001 |
| 报价 | b | b + 5位数字 | b00001 |
| 订单 | d | d + 5位数字 | d00001 |
| 采购 | c | c + 5位数字 | c00001 |

---

## 5. API接口规范

### 5.1 接口格式

**请求格式**
```
POST /api/{module}/{action}
Content-Type: application/x-www-form-urlencoded
```

**响应格式**
```json
{
  "success": true/false,
  "message": "操作结果描述",
  "data": { ... }
}
```

### 5.2 通用接口

| 接口 | 方法 | 描述 |
|-----|------|------|
| /api/{module}/list | GET | 列表查询 |
| /api/{module}/add | POST | 新增记录 |
| /api/{module}/update | POST | 更新记录 |
| /api/{module}/delete | POST | 删除记录 |
| /api/{module}/batch_delete | POST | 批量删除 |
| /api/{module}/import | POST | 批量导入 |

### 5.3 认证方式

- **Cookie认证**：登录成功后设置Cookie
  - emp_id: 员工ID
  - account: 账号
  - rule: 权限等级
- **内部API认证**：X-Internal-API-Key Header

---

## 6. 数据库设计

### 6.1 数据库配置

| 配置项 | 值 |
|-------|-----|
| 数据库类型 | SQLite3 |
| Journal模式 | WAL / DELETE(WSL) |
| 连接池大小 | 10 |
| 超时时间 | 5秒 / 30秒(WSL) |
| 外键约束 | 开启 |

### 6.2 索引设计

系统包含19个优化索引，主要包括：

- 客户名称索引：idx_cli_name
- 需求日期索引：idx_quote_date
- 报价日期索引：idx_offer_date
- 订单日期索引：idx_order_date
- 邮件接收时间索引：idx_mail_received
- 邮件账户索引：idx_mail_account

---

## 7. 安全设计

### 7.1 认证安全

- 密码MD5加密存储
- 首次登录强制修改密码
- Session会话管理
- 权限分级控制

### 7.2 数据安全

- 自动备份机制
- 外键级联约束
- 软删除（邮件回收站）

### 7.3 敏感配置

- API密钥通过环境变量配置
- 邮件密码加密存储
- 开发模式可跳过认证（生产环境禁用）

---

## 8. 性能优化

### 8.1 数据库优化

- WAL模式提升并发性能
- LRU缓存汇率查询
- 批量操作使用executemany
- 连接池复用

### 8.2 前端优化

- 分页加载（默认20条/页）
- 列表视图排除大字段
- 静态资源缓存

---

## 9. 扩展功能

### 9.1 AI服务预留

系统预留AI服务接口：

- **意图识别**：分析邮件意图类型
- **智能回复**：生成建议回复内容
- **询价检测**：识别询价邮件关键词

### 9.2 OpenClaw Skills

系统支持通过OpenClaw Skills扩展功能：

- 邮件自动提取询价信息
- 商业发票(CI)自动生成
- 形式发票(PI)自动生成
- 韩国报价单生成

---

## 10. 版本规划

### 10.1 当前版本 v1.0

- ✅ 完整ERP核心功能
- ✅ 邮件系统集成
- ✅ 多账户管理
- ✅ 自动备份

### 10.2 后续规划

| 版本 | 功能 |
|-----|------|
| v1.1 | AI智能报价建议 |
| v1.2 | 移动端适配 |
| v1.3 | 多语言支持 |
| v2.0 | 微服务架构升级 |

---

## 附录

### A. 错误码定义

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| 账号不存在 | 登录账号错误 | 检查账号输入 |
| 此账号被限制登录 | 权限等级=4 | 联系管理员启用 |
| 密码错误 | 密码不匹配 | 重置密码 |
| 无权限 | 权限不足 | 申请更高权限 |
| 非法字段 | 更新不允许的字段 | 检查字段名 |
| FOREIGN KEY constraint failed | 存在关联数据 | 先删除关联数据 |

### B. 常见问题

**Q: 如何重置管理员密码？**
A: 使用默认后门账号 Admin/uni519 登录

**Q: 如何批量导入数据？**
A: 支持CSV文件和文本两种方式，首行为表头会自动跳过

**Q: 邮件同步失败怎么办？**
A: 检查IMAP服务器配置，163/126邮箱需要开启IMAP服务并使用授权码

---

**文档编写**: Claude Code
**最后更新**: 2026-03-24