# 数据库表结构文档

数据库：SQLite3 (WAL模式) / PostgreSQL
双环境支持：`uni_platform.db` (生产), `uni_platform_dev.db` (开发)

---

## 表概览

| 表名 | 描述 | 主要功能 |
|------|------|----------|
| uni_daily | 汇率表 | 记录每日KRW/USD汇率 |
| uni_emp | 员工表 | 系统用户、权限管理 |
| uni_cli | 客户表 | 客户信息管理 |
| uni_quote | 询价表 | 客户询价记录 |
| uni_vendor | 供应商表 | 供应商信息管理 |
| uni_offer | 报价表 | 给客户的报价记录 |
| uni_order | 销售订单表 | 销售订单记录 |
| uni_buy | 采购表 | 采购记录跟踪 |
| uni_order_manager | 客户订单管理器 | 客户订单汇总管理 |
| uni_order_manager_rel | 订单报价关联表 | 订单管理器与报价关联 |
| uni_order_attachment | 订单附件表 | 订单附件文件管理 |
| mail_config | 邮件账户配置表 | 邮箱账户配置 |
| uni_mail | 邮件表 | 邮件收发记录 |
| uni_mail_rel | 邮件关联表 | 邮件与业务实体关联 |
| mail_sync_lock | 同步锁表 | 防止并发同步冲突 |
| global_settings | 全局设置表 | 系统配置参数 |
| mail_folder | 邮件文件夹表 | 自定义邮件分类 |
| mail_filter_rule | 过滤规则表 | 邮件自动分类规则 |
| mail_blacklist | 黑名单表 | 垃圾邮件发送者 |
| uni_mail_synced_uid | 已同步UID表 | 同步进度追踪 |
| mail_folder_sync_progress | 文件夹同步进度表 | 文件夹级别同步状态 |
| uni_contact | 联系人表 | 营销联系人管理 |
| uni_marketing_email | 营销邮件表 | 营销邮件发送记录 |

---

## 详细表结构

### 1. uni_daily (汇率表)

记录每日外汇汇率，用于多币种价格换算。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| record_date | TEXT | NOT NULL | 记录日期 (YYYY-MM-DD) |
| currency_code | INTEGER | NOT NULL | 币种代码 (1=USD, 2=KRW) |
| exchange_rate | REAL | NOT NULL | 汇率 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**唯一约束**: (record_date, currency_code)

**索引**: `idx_daily_date`, `idx_daily_currency`

---

### 2. uni_emp (员工表)

系统用户账户和权限管理。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| emp_id | TEXT | PRIMARY KEY | 员工编号 (3位数字，如001) |
| department | TEXT | - | 部门 |
| position | TEXT | - | 职位 |
| emp_name | TEXT | NOT NULL | 员工姓名 |
| contact | TEXT | - | 联系方式 |
| account | TEXT | UNIQUE NOT NULL | 登录账号 |
| password | TEXT | NOT NULL | 密码 (MD5加密) |
| hire_date | TEXT | - | 入职日期 |
| rule | TEXT | NOT NULL | 权限级别 (1:读，2:编辑，3:管理员，4:禁用) |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**索引**: `idx_emp_account`, `idx_emp_rule`

**默认管理员**: Admin/uni519 (MD5: 088426ba2d6e02949f54ef1e62a2aa73)

---

### 3. uni_cli (客户表)

客户信息管理。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| cli_id | TEXT | PRIMARY KEY | 客户编号 (C001格式) |
| cli_name | TEXT | NOT NULL | 客户名称 |
| cli_full_name | TEXT | - | 公司全名 |
| cli_name_en | TEXT | - | 公司英文名 |
| contact_name | TEXT | - | 公司联系人 |
| address | TEXT | - | 公司地址 |
| region | TEXT | NOT NULL DEFAULT '韩国' | 地区 |
| credit_level | TEXT | DEFAULT 'A' | 信用等级 (A/B/C) |
| margin_rate | REAL | DEFAULT 10.0 | 利润率 (%) |
| emp_id | TEXT | NOT NULL | 负责员工编号 (外键) |
| website | TEXT | - | 网站 |
| payment_terms | TEXT | - | 付款条件 |
| email | TEXT | - | 邮箱 |
| phone | TEXT | - | 电话 |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: emp_id → uni_emp(emp_id) ON UPDATE CASCADE

**索引**: `idx_cli_name`, `idx_cli_emp`

---

### 4. uni_quote (询价表)

客户询价/需求记录。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| quote_id | TEXT | PRIMARY KEY | 询价编号 (Q+时间戳+4位随机) |
| quote_date | TEXT | - | 询价日期 |
| cli_id | TEXT | NOT NULL | 客户编号 (外键) |
| inquiry_mpn | TEXT | NOT NULL | 询型号 |
| quoted_mpn | TEXT | - | 报型号 (替代型号) |
| inquiry_brand | TEXT | - | 询品牌 |
| inquiry_qty | INTEGER | - | 询数量 |
| target_price_rmb | REAL | - | 目标价 (RMB) |
| cost_price_rmb | REAL | - | 成本价 (RMB) |
| date_code | TEXT | - | 批次号 |
| delivery_date | TEXT | - | 交期 |
| status | TEXT | DEFAULT '询价中' | 状态 |
| remark | TEXT | - | 备注 |
| is_transferred | TEXT | DEFAULT '未转' | 是否已转报价 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: cli_id → uni_cli(cli_id) ON UPDATE CASCADE

**索引**: `idx_quote_date`, `idx_quote_cli`, `idx_quote_transferred`

---

### 5. uni_vendor (供应商表)

供应商信息管理。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| vendor_id | TEXT | PRIMARY KEY | 供应商编号 (V001格式) |
| vendor_name | TEXT | NOT NULL | 供应商名称 |
| address | TEXT | - | 地址 |
| qq | TEXT | - | QQ |
| wechat | TEXT | - | 微信 |
| email | TEXT | - | 邮箱 |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

---

### 6. uni_offer (报价表)

给客户的正式报价记录。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| offer_id | TEXT | PRIMARY KEY | 报价编号 (O+时间戳+4位随机) |
| offer_date | TEXT | - | 报价日期 |
| quote_id | TEXT | UNIQUE | 关联询价ID (外键) |
| cli_id | TEXT | - | 客户编号 (外键) |
| inquiry_mpn | TEXT | - | 询型号 |
| quoted_mpn | TEXT | - | 报型号 |
| inquiry_brand | TEXT | - | 询品牌 |
| quoted_brand | TEXT | - | 报品牌 |
| inquiry_qty | INTEGER | - | 询数量 |
| actual_qty | INTEGER | - | 实报数量 |
| quoted_qty | INTEGER | - | 报价数量 |
| cost_price_rmb | REAL | - | 成本价 (RMB) |
| offer_price_rmb | REAL | - | 报价 (RMB) |
| price_kwr | REAL | - | 报价 (KRW) |
| price_usd | REAL | - | 报价 (USD) |
| platform | TEXT | - | 货源平台 |
| vendor_id | TEXT | - | 供应商ID (外键) |
| date_code | TEXT | - | 批次号 |
| delivery_date | TEXT | - | 交期 |
| emp_id | TEXT | NOT NULL | 业务员ID (外键) |
| offer_statement | TEXT | - | 报价条款 |
| remark | TEXT | - | 备注 |
| status | TEXT | DEFAULT '询价中' | 状态 |
| target_price_rmb | REAL | - | 目标价 (RMB) |
| is_transferred | TEXT | DEFAULT '未转' | 是否已转订单 |
| manager_id | TEXT | - | 关联订单管理器ID (外键) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**:
- vendor_id → uni_vendor(vendor_id)
- emp_id → uni_emp(emp_id)
- cli_id → uni_cli(cli_id)
- manager_id → uni_order_manager(manager_id) ON DELETE SET NULL

**索引**: `idx_offer_date`, `idx_offer_vendor`, `idx_offer_transferred`, `idx_offer_status`, `idx_offer_target_price`

---

### 7. uni_order (销售订单表)

销售订单记录。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| order_id | TEXT | PRIMARY KEY | 订单编号 (SO+时间戳+4位随机) |
| order_no | TEXT | UNIQUE | 订单号 (UNI-客户名-YYYYMMDDHH格式) |
| order_date | TEXT | - | 订单日期 |
| cli_id | TEXT | NOT NULL | 客户编号 (外键) |
| offer_id | TEXT | - | 关联报价ID (外键) |
| inquiry_mpn | TEXT | - | 型号 |
| inquiry_brand | TEXT | - | 品牌 |
| price_rmb | REAL | - | 单价 (RMB) |
| price_kwr | REAL | - | 单价 (KRW) |
| price_usd | REAL | - | 单价 (USD) |
| cost_price_rmb | REAL | - | 成本价 (RMB) |
| is_finished | INTEGER | DEFAULT 0 | 是否完成 (0/1) |
| is_paid | INTEGER | DEFAULT 0 | 是否付款 (0/1) |
| paid_amount | REAL | DEFAULT 0.0 | 已付金额 |
| return_status | TEXT | DEFAULT '正常' | 退货状态 |
| remark | TEXT | - | 备注 |
| is_transferred | TEXT | DEFAULT '未转' | 是否已转采购 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**:
- cli_id → uni_cli(cli_id)
- offer_id → uni_offer(offer_id)

**索引**: `idx_order_date`, `idx_order_cli`, `idx_order_offer`, `idx_order_transferred`

---

### 8. uni_buy (采购表)

采购记录和物流跟踪。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| buy_id | TEXT | PRIMARY KEY | 采购编号 (PU+时间戳+4位随机) |
| buy_date | TEXT | - | 采购日期 |
| order_id | TEXT | - | 关联订单ID (外键) |
| vendor_id | TEXT | - | 供应商ID (外键) |
| buy_mpn | TEXT | - | 采购型号 |
| buy_brand | TEXT | - | 采购品牌 |
| buy_price_rmb | REAL | - | 采购单价 (RMB) |
| buy_qty | INTEGER | - | 采购数量 |
| sales_price_rmb | REAL | - | 销售单价 (RMB) |
| total_amount | REAL | - | 总金额 |
| is_source_confirmed | INTEGER | DEFAULT 0 | 货源已确认 (0/1) |
| is_ordered | INTEGER | DEFAULT 0 | 已下单 (0/1) |
| is_instock | INTEGER | DEFAULT 0 | 已入库 (0/1) |
| is_shipped | INTEGER | DEFAULT 0 | 已发货 (0/1) |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**:
- order_id → uni_order(order_id)
- vendor_id → uni_vendor(vendor_id)

**索引**: `idx_buy_date`, `idx_buy_order`, `idx_buy_vendor`

---

### 9. uni_order_manager (客户订单管理器)

客户订单汇总管理主表。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| manager_id | TEXT | PRIMARY KEY | 订单管理器ID |
| customer_order_no | TEXT | UNIQUE NOT NULL | 客户订单号 |
| order_date | TEXT | NOT NULL | 订单日期 |
| cli_id | TEXT | NOT NULL | 客户编号 (外键) |
| total_cost_rmb | REAL | DEFAULT 0 | 总成本 (RMB) |
| total_price_rmb | REAL | DEFAULT 0 | 总售价 (RMB) |
| total_price_kwr | REAL | DEFAULT 0 | 总售价 (KRW) |
| total_price_usd | REAL | DEFAULT 0 | 总售价 (USD) |
| profit_rmb | REAL | DEFAULT 0 | 利润 (RMB) |
| model_count | INTEGER | DEFAULT 0 | 型号数量 |
| total_qty | INTEGER | DEFAULT 0 | 总数量 |
| is_paid | INTEGER | DEFAULT 0 | 已付款 (0/1) |
| is_finished | INTEGER | DEFAULT 0 | 已完成 (0/1) |
| paid_amount | REAL | DEFAULT 0 | 已付金额 |
| shipping_fee | REAL | DEFAULT 0 | 运费 |
| tracking_no | TEXT | - | 快递单号 |
| query_link | TEXT | - | 物流查询链接 |
| mail_id | TEXT | - | 关联邮件ID |
| mail_notes | TEXT | - | 邮件备注 |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: cli_id → uni_cli(cli_id) ON UPDATE CASCADE

**索引**: `idx_order_manager_cli`, `idx_order_manager_date`

---

### 10. uni_order_manager_rel (订单报价关联表)

订单管理器与报价单的关联关系。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| manager_id | TEXT | NOT NULL | 订单管理器ID (外键) |
| offer_id | TEXT | NOT NULL | 报价ID (外键) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**:
- manager_id → uni_order_manager(manager_id) ON DELETE CASCADE
- offer_id → uni_offer(offer_id) ON DELETE CASCADE

**唯一约束**: (manager_id, offer_id)

**索引**: `idx_order_manager_rel_manager`, `idx_order_manager_rel_order`

---

### 11. uni_order_attachment (订单附件表)

订单附件文件管理。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| manager_id | TEXT | NOT NULL | 订单管理器ID (外键) |
| file_path | TEXT | NOT NULL | 文件路径 |
| file_type | TEXT | NOT NULL | 文件类型 |
| file_name | TEXT | - | 文件名 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: manager_id → uni_order_manager(manager_id) ON DELETE CASCADE

---

### 12. mail_config (邮件账户配置表)

邮箱账户配置，支持多账户。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| account_name | TEXT | DEFAULT '默认账户' | 账户名称 |
| smtp_server | TEXT | - | SMTP服务器地址 |
| smtp_port | INTEGER | DEFAULT 587 | SMTP端口 |
| imap_server | TEXT | - | IMAP服务器地址 |
| imap_port | INTEGER | DEFAULT 993 | IMAP端口 |
| username | TEXT | - | 邮箱用户名 |
| password | TEXT | - | 邮箱密码 (加密存储) |
| use_tls | INTEGER | DEFAULT 1 | 使用TLS (0/1) |
| sync_batch_size | INTEGER | DEFAULT 100 | 同步批次大小 |
| sync_pause_seconds | REAL | DEFAULT 1.0 | 同步间隔秒数 |
| is_current | INTEGER | DEFAULT 0 | 当前使用账户 (0/1) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

---

### 13. uni_mail (邮件表)

邮件收发记录。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| subject | TEXT | - | 邮件主题 |
| from_addr | TEXT | NOT NULL | 发件人地址 |
| from_name | TEXT | - | 发件人名称 |
| to_addr | TEXT | NOT NULL | 收件人地址 |
| cc_addr | TEXT | - | 抄送地址 |
| content | TEXT | - | 邮件内容 (纯文本) |
| html_content | TEXT | - | 邮件内容 (HTML) |
| received_at | DATETIME | - | 接收时间 |
| sent_at | DATETIME | - | 发送时间 |
| is_sent | INTEGER | DEFAULT 0 | 已发送 (0/1) |
| is_read | INTEGER | DEFAULT 0 | 已读 (0/1) |
| is_deleted | INTEGER | DEFAULT 0 | 已删除 (0/1) |
| deleted_at | DATETIME | - | 删除时间 |
| message_id | TEXT | - | 邮件唯一标识 |
| imap_uid | INTEGER | - | IMAP UID |
| imap_folder | TEXT | - | IMAP文件夹名 |
| account_id | INTEGER | - | 邮箱账户ID (外键) |
| folder_id | INTEGER | - | 自定义文件夹ID (外键) |
| sync_status | TEXT | DEFAULT 'completed' | 同步状态 |
| sync_error | TEXT | - | 同步错误信息 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**:
- account_id → mail_config(id) ON DELETE SET NULL
- folder_id → mail_folder(id) ON DELETE SET NULL

**索引**: `idx_mail_uid_folder`, `idx_mail_received`, `idx_mail_sent`, `idx_mail_from`, `idx_mail_sync_status`, `idx_mail_account`, `idx_mail_message_id`, `idx_mail_folder_id`

---

### 14. uni_mail_rel (邮件关联表)

邮件与业务实体的关联关系。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| mail_id | INTEGER | NOT NULL | 邮件ID (外键) |
| ref_type | TEXT | NOT NULL | 关联类型 (quote/offer/order等) |
| ref_id | TEXT | NOT NULL | 关联实体ID |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: mail_id → uni_mail(id) ON DELETE CASCADE

**索引**: `idx_mail_rel_ref`

---

### 15. mail_sync_lock (同步锁表)

防止并发同步冲突。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY CHECK (id = 1) | 单行锁 |
| locked_at | DATETIME | - | 锁定时间 |
| locked_by | TEXT | - | 锁定者 |
| expires_at | DATETIME | - | 过期时间 |
| progress_total | INTEGER | DEFAULT 0 | 总进度 |
| progress_current | INTEGER | DEFAULT 0 | 当前进度 |
| progress_message | TEXT | DEFAULT '' | 进度消息 |
| sync_start_date | TEXT | - | 同步开始日期 |
| sync_end_date | TEXT | - | 同步结束日期 |
| total_emails | INTEGER | DEFAULT 0 | 总邮件数 |
| synced_emails | INTEGER | DEFAULT 0 | 已同步数 |

---

### 16. global_settings (全局设置表)

系统配置参数。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| key | TEXT | PRIMARY KEY | 配置键 |
| value | TEXT | - | 配置值 |
| updated_at | DATETIME | DEFAULT now | 更新时间 |

**常用配置键**:
- `sync_interval`: 同步间隔(分钟)
- `sync_days`: 同步天数范围
- `sync_deleted`: 是否同步已删除邮件
- `undo_send_seconds`: 撤回发送时间
- `signature`: 邮件签名

---

### 17. mail_folder (邮件文件夹表)

自定义邮件分类文件夹。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| folder_name | TEXT | NOT NULL | 文件夹名称 |
| folder_icon | TEXT | DEFAULT 'folder' | 文件夹图标 |
| sort_order | INTEGER | DEFAULT 0 | 排序顺序 |
| account_id | INTEGER | - | 邮箱账户ID (外键) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: account_id → mail_config(id) ON DELETE CASCADE

**索引**: `idx_mail_folder_account`

---

### 18. mail_filter_rule (过滤规则表)

邮件自动分类规则。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| folder_id | INTEGER | NOT NULL | 目标文件夹ID (外键) |
| keyword | TEXT | NOT NULL | 过滤关键词 |
| priority | INTEGER | DEFAULT 0 | 优先级 |
| is_enabled | INTEGER | DEFAULT 1 | 启用状态 (0/1) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: folder_id → mail_folder(id) ON DELETE CASCADE

**索引**: `idx_mail_filter_folder`, `idx_mail_filter_priority`

---

### 19. mail_blacklist (黑名单表)

垃圾邮件发送者黑名单。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| email_addr | TEXT | NOT NULL UNIQUE | 黑名单邮箱地址 |
| reason | TEXT | - | 黑名单原因 |
| account_id | INTEGER | - | 邮箱账户ID (外键) |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: account_id → mail_config(id) ON DELETE CASCADE

---

### 20. uni_mail_synced_uid (已同步UID表)

区分"从未同步"和"已删除"邮件。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| account_id | INTEGER | NOT NULL | 邮箱账户ID (外键) |
| imap_uid | INTEGER | NOT NULL | IMAP UID |
| imap_folder | TEXT | NOT NULL | IMAP文件夹名 |
| synced_at | DATETIME | DEFAULT now | 同步时间 |

**外键**: account_id → mail_config(id) ON DELETE CASCADE

**唯一约束**: (account_id, imap_uid, imap_folder)

---

### 21. mail_folder_sync_progress (文件夹同步进度表)

文件夹级别同步状态追踪。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| account_id | INTEGER | NOT NULL | 邮箱账户ID (外键) |
| folder_name | TEXT | NOT NULL | 文件夹名称 |
| last_uid | INTEGER | DEFAULT 0 | 最后同步的UID |
| last_sync_at | DATETIME | - | 最后同步时间 |

**外键**: account_id → mail_config(id) ON DELETE CASCADE

**唯一约束**: (account_id, folder_name)

---

### 22. uni_contact (联系人表)

营销联系人管理。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| contact_id | TEXT | PRIMARY KEY | 联系人ID (CT+时间戳) |
| cli_id | TEXT | - | 关联客户ID (外键，可为空) |
| email | TEXT | NOT NULL UNIQUE | 联系人邮箱 |
| domain | TEXT | NOT NULL | 邮箱域名 (自动提取) |
| contact_name | TEXT | - | 联系人姓名 |
| country | TEXT | - | 国家 |
| position | TEXT | - | 职位 |
| phone | TEXT | - | 电话 |
| company | TEXT | - | 公司名称 |
| is_bounced | INTEGER | DEFAULT 0 | 是否退信 (0/1) |
| is_read | INTEGER | DEFAULT 0 | 是否已读 (0/1) |
| is_deleted | INTEGER | DEFAULT 0 | 是否删除 (0/1) |
| send_count | INTEGER | DEFAULT 0 | 发送次数 |
| bounce_count | INTEGER | DEFAULT 0 | 退信次数 |
| read_count | INTEGER | DEFAULT 0 | 已读次数 |
| last_sent_at | DATETIME | - | 最后发送时间 |
| remark | TEXT | - | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**外键**: cli_id → uni_cli(cli_id) ON DELETE SET NULL

**索引**: `idx_contact_cli`, `idx_contact_domain`, `idx_contact_email`, `idx_contact_country`, `idx_contact_bounced`

---

### 23. uni_marketing_email (营销邮件表)

营销邮件发送记录。

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增ID |
| contact_id | TEXT | NOT NULL | 联系人ID (外键) |
| mail_id | INTEGER | - | 关联邮件表ID (外键) |
| subject | TEXT | - | 邮件主题 |
| content | TEXT | - | 邮件内容 |
| sent_at | DATETIME | DEFAULT now | 发送时间 |
| status | TEXT | DEFAULT 'sent' | 状态 (sent/delivered/bounced/read) |
| bounced_reason | TEXT | - | 退信原因 |

**外键**:
- contact_id → uni_contact(contact_id) ON DELETE CASCADE
- mail_id → uni_mail(id) ON DELETE SET NULL

**索引**: `idx_marketing_contact`, `idx_marketing_sent`, `idx_marketing_status`

---

## ER 关系图

```
┌─────────────┐
│  uni_emp    │
│  (员工表)   │
└──────┬──────┘
       │
       ├──────────────────┬──────────────────────┐
       │                  │                      │
       ▼                  ▼                      ▼
┌─────────────┐    ┌─────────────┐        ┌───────────────┐
│  uni_cli    │    │  uni_vendor │        │ mail_config   │
│  (客户表)   │    │  (供应商表) │        │ (邮件账户表) │
└──────┬──────┘    └──────┬──────┘        └───────┬───────┘
       │                  │                       │
       ├──────────────────┤                       │
       │                  │                       │
       ▼                  │               ┌───────▼───────┐
┌─────────────┐           │               │   uni_mail    │
│ uni_quote   │           │               │   (邮件表)    │
│  (询价表)   │           │               └───────┬───────┘
└──────┬──────┘           │                       │
       │                  │                       │
       ▼                  │               ┌───────▼───────┐
┌─────────────┐◄──────────┤               │  uni_mail_rel │
│  uni_offer  │           │               │ (邮件关联表) │
│  (报价表)   │           │               └───────┬───────┘
└──────┬──────┘           │                       │
       │                  │               ┌───────▼───────┐
       ▼                  │               │ mail_folder   │
┌─────────────┐           │               │ (文件夹表)    │
│  uni_order  │           │               └───────┬───────┘
│  (订单表)   │           │                       │
└──────┬──────┘           │               ┌───────▼───────┐
       │                  │               │mail_filter_rule│
       └──────────────────┘               │ (过滤规则表) │
       │                                  └───────┬───────┘
       ▼                                  │
┌─────────────┐                           ▼
│   uni_buy   │                   ┌───────────────┐
│  (采购表)   │                   │ mail_blacklist│
└─────────────┘                   │  (黑名单表)   │
                                  └───────────────┘

┌─────────────────────┐
│ uni_order_manager   │
│ (客户订单管理器)    │
└──────┬──────────────┘
       │
       ├──────────────────┬──────────────────────┐
       │                  │                      │
       ▼                  ▼                      ▼
┌─────────────────────┐  ┌──────────────────┐  ┌────────────────────┐
│uni_order_manager_rel│  │uni_order_attachment│ │   uni_contact      │
│ (报价关联表)        │  │   (附件表)        │  │  (联系人表)        │
└─────────────────────┘  └──────────────────┘  └──────┬─────────────┘
                                                      │
                                                      ▼
                                              ┌────────────────────┐
                                              │uni_marketing_email │
                                              │  (营销邮件表)      │
                                              └────────────────────┘

┌─────────────┐
│  uni_daily  │
│  (汇率表)   │
└─────────────┘
      │
      └── 被报价/订单/采购引用进行汇率换算
```

---

## 索引汇总

共40+个索引，主要分类：

### 业务表索引 (20个)
```sql
CREATE INDEX idx_cli_name ON uni_cli(cli_name);
CREATE INDEX idx_cli_emp ON uni_cli(emp_id);
CREATE INDEX idx_quote_date ON uni_quote(quote_date);
CREATE INDEX idx_quote_cli ON uni_quote(cli_id);
CREATE INDEX idx_quote_transferred ON uni_quote(is_transferred);
CREATE INDEX idx_offer_date ON uni_offer(offer_date);
CREATE INDEX idx_offer_vendor ON uni_offer(vendor_id);
CREATE INDEX idx_offer_transferred ON uni_offer(is_transferred);
CREATE INDEX idx_offer_status ON uni_offer(status);
CREATE INDEX idx_offer_target_price ON uni_offer(target_price_rmb);
CREATE INDEX idx_order_date ON uni_order(order_date);
CREATE INDEX idx_order_cli ON uni_order(cli_id);
CREATE INDEX idx_order_offer ON uni_order(offer_id);
CREATE INDEX idx_order_transferred ON uni_order(is_transferred);
CREATE INDEX idx_buy_date ON uni_buy(buy_date);
CREATE INDEX idx_buy_order ON uni_buy(order_id);
CREATE INDEX idx_buy_vendor ON uni_buy(vendor_id);
CREATE INDEX idx_order_manager_cli ON uni_order_manager(cli_id);
CREATE INDEX idx_order_manager_date ON uni_order_manager(order_date);
CREATE INDEX idx_order_manager_rel_manager ON uni_order_manager_rel(manager_id);
CREATE INDEX idx_order_manager_rel_order ON uni_order_manager_rel(offer_id);
CREATE INDEX idx_daily_date ON uni_daily(record_date);
CREATE INDEX idx_daily_currency ON uni_daily(currency_code);
CREATE INDEX idx_emp_account ON uni_emp(account);
CREATE INDEX idx_emp_rule ON uni_emp(rule);
```

### 邮件系统索引 (10个)
```sql
CREATE INDEX idx_mail_uid_folder ON uni_mail(imap_uid, imap_folder);
CREATE INDEX idx_mail_received ON uni_mail(received_at DESC);
CREATE INDEX idx_mail_sent ON uni_mail(sent_at DESC);
CREATE INDEX idx_mail_from ON uni_mail(from_addr);
CREATE INDEX idx_mail_sync_status ON uni_mail(sync_status);
CREATE INDEX idx_mail_account ON uni_mail(account_id);
CREATE UNIQUE INDEX idx_mail_message_id ON uni_mail(message_id);
CREATE INDEX idx_mail_rel_ref ON uni_mail_rel(ref_type, ref_id);
CREATE INDEX idx_mail_folder_account ON mail_folder(account_id);
CREATE INDEX idx_mail_filter_folder ON mail_filter_rule(folder_id);
CREATE INDEX idx_mail_filter_priority ON mail_filter_rule(priority DESC);
CREATE INDEX idx_mail_folder_id ON uni_mail(folder_id);
```

### 联系人营销索引 (5个)
```sql
CREATE INDEX idx_contact_cli ON uni_contact(cli_id);
CREATE INDEX idx_contact_domain ON uni_contact(domain);
CREATE INDEX idx_contact_email ON uni_contact(email);
CREATE INDEX idx_contact_country ON uni_contact(country);
CREATE INDEX idx_contact_bounced ON uni_contact(is_bounced);
CREATE INDEX idx_marketing_contact ON uni_marketing_email(contact_id);
CREATE INDEX idx_marketing_sent ON uni_marketing_email(sent_at DESC);
CREATE INDEX idx_marketing_status ON uni_marketing_email(status);
```

---

*最后更新：2026-04-14*