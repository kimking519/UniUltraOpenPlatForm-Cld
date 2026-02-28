---
name: sale-input-needs
description: 自动从销售聊天、邮件或日常笔记中提取电子元组件需求（MPN、数量、价格、客户），并快速录入 UniUltra 平台的“需求管理”表。适用于快速处理非结构化询价信息。
---

# Sale Input Needs

`sale-input-needs` 是一个专为销售团队设计的自动化工具，它能通过自然语言处理能力将口头或文字的需求描述快速转化为系统内的询价记录。

## When to Use

在以下场景使用此 Skill：
- 从微信聊天记录中快速抓取客户发来的询价单
- 将邮件中的零件列表快速导入系统，而无需逐条手动录入
- 在与客户通话后，通过简短的文字总结快速归档需求
- 处理包含多个型号和不同客户的复杂询价信息

## Prerequisites

此 Skill 依赖 Python。
- 如果在 Windows 下运行：直接使用本地路径。
- 如果在 **WSL (Ubuntu)** 下运行：可以通过 `/mnt/` 挂载点访问 Windows 目录下的数据库。

```bash
# WSL 路径映射参考
# Windows: E:\WorkPlace\7_AI_APP\UniUltraOpenPlatForm\uni_platform.db
# WSL:     /mnt/e/WorkPlace/7_AI_APP/UniUltraOpenPlatForm/uni_platform.db
```

## WSL & 环境配置

为了让运行在 WSL 里的 OpenClaw 能够直接读取数据（用于校验客户 ID 等），Skill 提供了 `db_tool.py`。

**常用命令：**

```bash
# 在 WSL 中查询客户 ID (根据名称模糊搜索)
python openclaw_skills/sale-input-needs/scripts/db_tool.py \
  --db_path "/mnt/e/WorkPlace/7_AI_APP/UniUltraOpenPlatForm/uni_platform.db" \
  --action find_cli --query "客户名称"
```

## Quick Start

### 1. 识别需求数据

从用户输入中提取以下结构化信息：
- **cli_id**: 客户 ID（如 C001）
- **mpn**: 型号（必须为大写，如 TPS54331DR）
- **qty**: 需求数量
- **brand**: 指定品牌（可选）
- **price**: 客户目标价（可选）
- **remark**: 备注信息

### 2. 执行自动化录入

使用预置脚本提交数据：

```bash
python openclaw_skills/sale-input-needs/scripts/auto_input.py --cli_id "C001" --mpn "STM32F103" --qty 1000
```

## Search & Mapping (查找映射)

在录入前，可以先查询客户 ID 以确保正确：

```bash
# 查询客户列表以获取正确的 cli_id
# 建议通过 OpenClaw 检索 cli 表
```

## For AI Agents

此 Skill 为 AI Agent 提供了标准化的数据处理协议：

```bash
# 提取多个型号时的处理逻辑：
# 1. 将复杂段落分解为独立的条目列表
# 2. 依次调用 auto_input.py 脚本
# 3. 汇总所有成功录入的需求编号（如 Q2026xxxx）并反馈给用户
```

## Workflow (工作流)

```
1. 接收输入 → 销售粘贴聊天记录或描述
2. 数据建模 → 提取 (mpn, qty, price, cli_id)
3. 校验数据 → 转换型号为全大写，确保 cli_id 有效
4. 运行脚本 → 通过 auto_input.py 向后端发送请求
5. 结果反馈 → 返回已生成的 Q 编号并在系统内确认
6. 扩展功能 → 系统现在支持“一键复制”功能：由于同一需求可能有不同供应商的多个报价，用户可以在系统前端勾选对应需求记录并点击“批量复制”，生成相同需求的新记录以便录入多条报价。
```

## Tips

- **型号纠错**：电子行业型号对字母非常敏感，录入前请务必去除多余的空格并转换为大写。
- **缺失客户**：如果用户未指定客户名，请先询问或在 `uni_cli` 中模糊搜索。
- **批量处理**：如果聊天记录包含多个型号（如“A型号要100，B型号要200”），请循环调用录入命令或使用新支持的 `--text` 模式。

## Batch Processing (New)

如果你有多个型号，可以使用 `--text` 参数：

```bash
python openclaw_skills/sale-input-needs/scripts/auto_input.py --cli_name "客户A" --text "TPS54331 100 TI
STM32F103 500 ST"
```

## System Integration: Email Summary

系统现在支持在“报价管理”页面一键将选中的报价记录汇总发送邮件。
- **发送至**: joy@unicornsemi.com
- **功能**: 生成汇总表格附件 (.xlsx) 并生成标准格式的邮件正文。

## Troubleshooting

**Issue:** 连接被拒绝 (Connection Refused)  
**Fix:** 确保 Fast API 服务正在运行，且 `base_url` 正确。

**Issue:** 客户 ID 不存在  
**Fix:** 请先在“客户管理”模块创建客户，或使用已有的有效 ID（如 C001, C002）。

**Issue:** 录入成功但页面未刷新  
**Fix:** 脚本完成后请手动刷新 `/quote` 页面查看最新记录。

## References

- 核心脚本位置: `openclaw_skills/sale-input-needs/scripts/auto_input.py`
- 数据库查询工具: `openclaw_skills/sale-input-needs/scripts/db_tool.py`
- 原始数据表: `uni_quote`
