# AGENTS.md - UniUltraOpenPlatForm 项目指南

## 项目概述

UniUltraOpenPlatForm 是一个基于 FastAPI 的 ERP 系统，用于电子元器件贸易业务。
管理完整的销售流程：询价(quote) -> 报价(offer) -> 订单(order) -> 采购(buy)。

## 技术栈

- **后端**: FastAPI (单文件 main.py)
- **数据库**: SQLite3 (WAL模式) / PostgreSQL，连接池 + LRU缓存
- **前端**: Jinja2 模板 + 原生 JavaScript
- **文档生成**: openpyxl (Excel/CI/PI)

## 常用命令

```bash
# 启动应用
python main.py

# 使用 uvicorn 启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 初始化/重置数据库
python Sills/base.py

# 安装依赖
pip install -r requirements.txt
```

## 项目结构

```
UniUltraOpenPlatForm/
├── main.py              # FastAPI 主应用（路由、API）
├── Sills/               # 数据库操作层（一个实体一个模块）
│   ├── base.py          # 数据库连接、schema、分页工具
│   ├── db_emp.py        # 员工管理
│   ├── db_cli.py        # 客户管理
│   ├── db_vendor.py     # 供应商管理
│   ├── db_quote.py      # 询价/需求管理
│   ├── db_offer.py      # 报价管理
│   ├── db_order.py      # 销售订单管理
│   ├── db_buy.py        # 采购管理
│   ├── db_mail.py       # 邮件管理
│   └── ...
├── openclaw_skills/     # 自动化脚本（文档生成、数据处理）
├── templates/           # Jinja2 HTML 模板
├── static/              # 静态资源
└── utils/               # 工具函数
```

## 业务实体关系

```
uni_emp (员工)
    └── uni_cli (客户)
            ├── uni_quote (询价/需求)
            │       └── uni_offer (报价)
            │               └── uni_order (订单)
            │                       └── uni_buy (采购)
```

## ID 生成规则

- 员工: 001, 002 (3位数字)
- 客户: C001, C002
- 供应商: V001, V002
- 询价: Q + 时间戳 + 4位随机数
- 报价: O + 时间戳 + 4位随机数
- 订单: SO + 时间戳 + 4位随机数，order_no 格式 UNI-客户名-YYYYMMDDHH
- 采购: PU + 时间戳 + 4位随机数

## 编码规范

### 语言
- 中文注释和文档

### 文件组织
- 单个文件不要超过 1000 行代码
- 数据库操作全部通过 Sills/ 中的模块进行，不直接写 SQL 语句

### 权限级别
- 1 = 只读
- 2 = 编辑
- 3 = 管理员
- 4 = 禁用

### 默认管理员
- 用户名: Admin
- 密码: uni519

### 安全
- 关键 key 以单独的配置文件形式配置
- 密码使用 MD5 哈希

## Web 路由

### 页面 (HTML)
- / - 仪表盘
- /login - 登录页
- /emp, /cli, /vendor - 实体管理
- /quote, /offer, /order, /buy - 销售流程
- /daily - 汇率管理
- /settings - 系统设置

### API 端点
所有 CRUD 操作遵循模式: /api/{entity}/{action}
- 操作: list, add, update, delete, batch_import, batch_delete

## OpenClaw Skills 开发规范

Skills 目录 openclaw_skills/ 存放自动化脚本：

1. 与项目解耦: skills 可以调用项目封装的方法，但项目不依赖任何 skill
2. 无硬编码: 操作数据库通过数据操作层，不出现 SQL 语句
3. 相对路径: SKILL.md 中只使用相对路径，项目路径通过环境变量获取
4. 格式参考: Skills_guideline.md

## 工作流程要求

### 修改前沟通
在修改 bug、添加功能或优化之前，先不要写代码：
1. 分析变动可能影响的功能模块
2. 与用户沟通理解和计划
3. 用户明确同意后才开始修改

### 数据库修改
重要！ 不要私自修改表结构，凡是要修改表一定要先告诉用户。

### Bug 管理
- 出现的 bug 和错误都要记录下来
- 出现 2 次以上的 bug 要重点记录
- 每次提交前都要回归测试

### Git Commit
- 提交时添加时间戳，精确到分钟

### 文档维护
- 维护功能列表文件
- 维护表结构文件
- 维护单元测试表（用于回归测试）

## 文档输出路径

生成的文档 (CI, PI, 报价单) 保存到：
- 默认: E:\1_Business\1_Auto\{客户名}\{日期yyyymmdd}\
- 模板位于 openclaw_skills/*/template/
