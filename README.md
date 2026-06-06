<div align="center">

# 🍜 餐饮智慧供应链与库存智能决策系统

**Smart Supply Chain & Intelligent Inventory Decision System for F&B Stores**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

一款面向餐饮零售门店的**精细化供应链与智慧库存管理系统**，深度集成多模态大模型、自适应时序预测与 BOM 穿透扣料，彻底解决门店传统库存管理的盲区痛点。

[快速开始](#-快速开始) · [功能演示](#-业务功能模块) · [架构设计](#-系统架构) · [数据库设计](#-数据库设计)

</div>

---

## 📋 目录

- [🌟 核心亮点](#-核心技术亮点)
- [🚀 快速开始](#-快速开始)
- [⚙️ 业务功能模块](#-业务功能模块)
- [🗂️ 项目结构](#-项目结构)
- [💾 数据库设计](#-数据库设计)
- [🏗️ 系统架构](#-系统架构)

---

## 🌟 核心技术亮点

### 统一 AI 智能数据网关

> 打破传统进销存软件各模块孤立录入的壁垒

系统将**口语化记账文本、收银台下单口令、Excel 初始库存表与纸质盘点单拍照截图**全部统一交由 `Agnes-2.0-Flash` 多模态模型作为数据入口，自动清洗为标准结构化事务列表。

```
[任意输入] ──► Agnes-2.0-Flash ──► 标准结构化事务 ──► SQLite 落库
  口语文本                              Pydantic 校验
  收据截图
  Excel 上传
```

### 复合套餐 BOM 双层穿透扣料

```
前台下单（套餐）
      │
      ▼
   套餐拆解 (combo_config)
      │
      ▼
   单品列表
      │
      ▼
   BOM 配方穿透 (dish_bom)
      │
      ▼
   原材料库存原子扣减 ← 数据库事务锁保障
```

**结果保障**：`物理库存 = 历史入库 - 销售扣料 - 打烊报损`，实现全链路精准闭环。

### 其他核心优势

| 能力 | 描述 |
|------|------|
| 🤖 **批量智能建档** | 上传 Excel 截图，AI 自动高并发循环处理，新食材自动建档 |
| 📈 **时序预测** | 结合气温等外部协变量进行多项式拟合，预测未来 3 天销量 |
| 🔐 **安全合规** | `.env` 隔离 API Key，Pydantic 强校验，标准 `logging` 全链路可观测 |
| ⚡ **企业级容错** | 全面移除隐式吞错，所有 SQL/网络异常均有据可查 |

---

## 🚀 快速开始

### 前置要求

- Python **3.9+**

### 1. 克隆项目

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=你的真实_sk_api_key
OPENAI_BASE_URL=https://apihub.agnes-ai.com/v1
AI_MODEL=Agnes-2.0-Flash
```

> ⚠️ **注意**：请勿将 `.env` 提交至版本控制，已在 `.gitignore` 中配置忽略。

### 4. 启动系统

```bash
streamlit run app.py
```

浏览器将自动打开智能看板。

> 💡 **首次运行**：系统会自动建立全部 7 张表结构，并注入 **21 天历史销售数据**、标准 BOM 配方（宫保鸡丁、黑椒牛柳）及复合套餐（超值双人套餐等），可立即上手功能测试。

---

## ⚙️ 业务功能模块

<table>
<tr>
<th>模块</th>
<th>功能描述</th>
</tr>
<tr>
<td>🧠 <b>AI 智能录入网关</b></td>
<td>支持口语文本、收据截图、Excel 表格多模态输入，秒级批量入库与自适应建档</td>
</tr>
<tr>
<td>🖥️ <b>前台收银模拟器</b></td>
<td>模拟快捷结账，自动探查套餐并按 BOM 配方秒级更新底层原材料库存</td>
</tr>
<tr>
<td>🚨 <b>实时库存预警</b></td>
<td>库存水位线监测，低于安全库存时指标卡自动触发红色高亮预警</td>
</tr>
<tr>
<td>📊 <b>销量预测分析</b></td>
<td>多项式拟合 + 外部协变量，预测未来 3 天走势，含 MAE 回测与 95% 可信区间</td>
</tr>
<tr>
<td>🎯 <b>智能补货指南</b></td>
<td>AI 决策智能体按抗风险策略（防断货 / 控成本）动态生成大白话备货建议</td>
</tr>
<tr>
<td>🗃️ <b>资产配置管理</b></td>
<td>食材/商品档案 CRUD，支持建档与注销，为 BOM 配方提供元数据支撑</td>
</tr>
</table>

---

## 🗂️ 项目结构

```
inventory_project/
│
├── .env                        # 本地密钥与环境配置（手动创建，勿提交）
├── inventory_system.db         # SQLite 关系型数据库文件
├── requirements.txt            # 第三方依赖声明
├── README.md                   # 本文档
├── app.py                      # 系统主入口：前端 UI 渲染与控制器分发
│
├── config/
│   ├── __init__.py
│   └── settings.py             # 全局配置、环境隔离、AI 客户端初始化
│
├── database/
│   ├── __init__.py
│   └── db_manager.py           # 数据操作总线（建表、种子注入、BOM 扣料）
│
└── modules/
    ├── __init__.py
    ├── schemas.py              # Pydantic 强校验数据结构（网关边界隔离）
    ├── ai_parser.py            # Agnes-2.0-Flash 多模态批量提取引擎
    └── models.py               # 时序拟合模型 + AI 智能备货指南生成
```

---

## 💾 数据库设计

系统基于 SQLite 设计了 **7 张核心业务表**，保障全链路数据一致性：

```
┌─────────────────────┐     ┌─────────────────────┐
│    items_config     │     │      dish_bom        │
│ ─────────────────── │     │ ─────────────────────│
│ 食材/商品基础配置    │◄────│ 单品与原材料消耗配方  │
│ 当前库存/安全库存    │     │                     │
│ 特征损耗率/单位      │     └─────────────────────┘
└────────┬────────────┘
         │                   ┌─────────────────────┐
         │                   │    combo_config      │
         │                   │ ─────────────────────│
         │                   │ 复合套餐与单品组合关系 │
         │                   └─────────────────────┘
         │
┌────────▼────────────┐     ┌─────────────────────┐
│   sales_history     │     │   purchase_orders    │
│ ─────────────────── │     │ ─────────────────────│
│ 每日扣料消耗总量     │     │ 采购数量/成本/供应商  │
│ 气温/废弃量协变量    │     │                     │
└────────┬────────────┘     └─────────────────────┘
         │
┌────────▼────────────┐     ┌─────────────────────┐
│inventory_transactions│     │     ai_reports       │
│ ─────────────────── │     │ ─────────────────────│
│ 全链路库存流水审计   │     │ AI 备货指南当日缓存   │
│ 入库/扣料/报损溯源   │     │ 避免重复调用大模型    │
└─────────────────────┘     └─────────────────────┘
```

---

## 🏗️ 系统架构

```
                    ┌─────────────────────────────┐
                    │         app.py (UI)          │
                    │      Streamlit 前端看板       │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
   ┌──────────▼──────────┐  ┌──────▼──────┐  ┌────────▼────────┐
   │     ai_parser.py    │  │  models.py  │  │  db_manager.py  │
   │  Agnes-2.0-Flash    │  │  时序预测    │  │  SQLite 数据总线 │
   │  多模态解析引擎      │  │  补货指南    │  │  BOM 扣料事务   │
   └──────────┬──────────┘  └──────┬──────┘  └────────┬────────┘
              │                    │                    │
              └────────────────────▼────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        schemas.py            │
                    │    Pydantic 强校验层          │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     inventory_system.db      │
                    │       SQLite 数据库          │
                    └─────────────────────────────┘
```

---

<div align="center">

**如果本项目对你有帮助，欢迎点个 ⭐ Star！**

Made with ❤️ · Powered by Agnes-2.0-Flash

</div>
