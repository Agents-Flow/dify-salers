# AI 抖音获客系统 - 目标文档

## 一、项目概述

### 1.1 一句话介绍
**不拍短视频、不用直播，帮你在抖音上抓到所有你想要的精准客户。**

### 1.2 解决的痛点
- 自己做短视频没有流量，竞争激烈
- 自己做不过同行，请人运营成本太高
- 传统获客方式效率低下

### 1.3 核心理念
> 几人别人抖音做得好，就去抓别人的客户就可以了

## 二、核心功能模块

### 2.1 抓取评论区客户

**功能描述：** 从抖音同行视频的评论区抓取潜在客户

**操作流程：**
1. 打开 AI销售后台 → 获客 → 抖音获客 → 抓取评论区客户
2. 告诉 AI 目标客户所在城市
3. 输入目标客户关键词（如：行业、需求等）
4. 输入同行视频链接（评论区的人就是潜在客户）
5. AI 自动抓取评论区用户信息

**价值展示：**
- 对比：传统方式一个月才能获取的客户量，AI 1分钟就能搞定
- 对比：别人花几百块投抖加才获得的客户，你一分钱没花就拿到了

### 2.2 抓取抖音团购客户

**功能描述：** 从本地团购商家的评论区抓取周边6公里内的精准客户

**操作流程：**
1. 打开 AI销售后台 → 获客 → 抖音获客 → 抓取团购客户
2. 设置商家位置（定位）
3. 系统自动从最近的商家开始抓取
4. 展示抓取到的商家数据和客户数据

**核心逻辑：**
- 团购评论区的用户 = 到店消费过的客户 = 住在周边的人
- 同城吃喝玩乐榜的商家是优质数据源

### 2.3 自动化开发客户

**功能描述：** AI 自动完成客户触达全流程

**自动化能力：**
1. **自动发私信** - AI 生成个性化私信内容
2. **自动要微信** - 智能话术引导客户提供微信
3. **自动加微信** - 自动发送好友申请
4. **精准分类** - 评论内容智能分类，只开发精准客户

## 三、ROI 算账模型

### 3.1 系统容量
| 指标 | 数值 |
|------|------|
| 1个AI销售绑定抖音号 | 10个 |
| 每个抖音号每天私信数 | 30条 |
| 每天总私信数 | 300条 |
| 每月总私信数 | 9,000条 |

### 3.2 收益预估

**保守估算（1%成交率）：**
- 月成交客户：9,000 × 1% = 90人
- 年成交客户：90 × 12 = 1,080人
- 年营收（客单价1000元）：**108万**

**乐观估算（3%成交率）：**
- 月成交客户：9,000 × 3% = 270人
- 年成交客户：270 × 12 = 3,240人
- 年营收（客单价1000元）：**324万**

## 四、技术实现方案

### 4.1 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端界面 (Web)                        │
│         Next.js + React + TypeScript                    │
│         (Dify 现有前端扩展)                              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Dify 工作流引擎                        │
│    - 客户意向分析工作流                                  │
│    - 私信内容生成工作流                                  │
│    - 客户智能分类工作流                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    后端 API                              │
│              Python Flask + Celery                      │
├───────────────────────────┬─────────────────────────────┤
│   Dify 核心服务           │   获客扩展服务               │
│   - 工作流执行            │   - 爬虫任务调度             │
│   - 模型调用              │   - 客户数据管理             │
│   - 对话管理              │   - 自动化任务服务           │
└───────────────────────────┴─────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              MediaCrawler 数据采集引擎                   │
│         https://github.com/NanmiCoder/MediaCrawler      │
├─────────────────────────────────────────────────────────┤
│  - 抖音视频/评论爬取      - Playwright 浏览器自动化      │
│  - 小红书/快手/B站支持    - 扫码登录认证                 │
│  - 多种存储格式           - 反爬策略内置                 │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    数据存储                              │
│         PostgreSQL + Redis + Vector DB                  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 MediaCrawler 集成方案

**项目地址：** https://github.com/NanmiCoder/MediaCrawler

**核心能力：**
| 功能 | 说明 |
|------|------|
| 抖音视频爬取 | 支持关键词搜索、指定视频ID抓取 |
| 抖音评论爬取 | 自动抓取视频评论区用户信息 |
| 多平台支持 | 小红书、快手、B站、微博、知乎、百度贴吧 |
| 登录方式 | 扫码登录（QRCode） |
| 数据存储 | CSV、JSON、Excel、SQLite、MySQL |
| 浏览器自动化 | Playwright |

**集成方式：**

```bash
# 1. 克隆 MediaCrawler 作为子模块
git submodule add https://github.com/NanmiCoder/MediaCrawler.git tools/media_crawler

# 2. 安装依赖
cd tools/media_crawler
uv sync
uv run playwright install

# 3. 运行抖音评论抓取
uv run main.py --platform dy --lt qrcode --type search
```

**关键配置（config/base_config.py）：**
```python
# 开启评论爬取
ENABLE_GET_COMMENTS = True

# 抖音相关配置
CRAWLER_TYPE = "search"  # search: 关键词搜索, detail: 指定视频
KEYWORDS = ["装修", "家具"]  # 搜索关键词
```

### 4.3 功能模块划分

#### 模块一：数据采集层（基于 MediaCrawler）
- [ ] 集成 MediaCrawler 作为爬虫引擎
- [ ] 封装抖音评论区抓取 API
- [ ] 封装抖音团购数据抓取 API
- [ ] 实现抓取任务队列管理
- [ ] 用户信息解析与清洗

#### 模块二：AI 智能分析层（基于 Dify）
- [ ] 创建客户意向度评分工作流
- [ ] 创建评论内容分类工作流
- [ ] 创建精准客户筛选工作流
- [ ] 创建个性化私信生成工作流

#### 模块三：自动化触达层
- [ ] 抖音账号绑定管理（Cookie 管理）
- [ ] 私信自动发送（基于 Playwright）
- [ ] 发送频率控制（防封号策略）
- [ ] 微信引流话术库

#### 模块四：客户管理层
- [ ] 客户池管理（去重、标签）
- [ ] 跟进状态追踪
- [ ] 转化漏斗统计
- [ ] 数据报表展示

### 4.4 技术选型

| 层级 | 技术方案 | 说明 |
|------|----------|------|
| 前端 | Next.js 15 + React 19 | 基于 Dify Web 扩展 |
| 后端 | Python Flask + Celery | 基于 Dify API 扩展 |
| AI引擎 | Dify 工作流 + LLM | 客户分析、私信生成 |
| **爬虫引擎** | **MediaCrawler** | **抖音/小红书数据采集** |
| 浏览器自动化 | Playwright | 登录、私信发送 |
| 数据库 | PostgreSQL | 客户数据存储 |
| 缓存 | Redis | 任务队列、会话缓存 |
| 容器化 | Docker + Docker Compose | 一键部署 |

### 4.5 数据流设计

```
用户输入关键词/视频链接
        │
        ▼
┌───────────────────┐
│  MediaCrawler     │  ← 抓取抖音评论/用户数据
│  (Playwright)     │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  数据清洗服务      │  ← 去重、格式化、入库
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Dify 工作流       │  ← AI 分析客户意向
│  (LLM 分类)       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  精准客户池        │  ← 高意向客户列表
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Dify 工作流       │  ← AI 生成私信内容
│  (私信生成)       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  自动私信服务      │  ← Playwright 发送私信
│  (频率控制)       │
└───────────────────┘
```

## 五、开发里程碑

### Phase 1: 基础设施（1周）
- [ ] 克隆并配置 MediaCrawler
- [ ] 验证抖音评论抓取功能
- [ ] 设计数据库表结构（客户表、任务表）
- [ ] 搭建基础 API 框架

### Phase 2: 数据采集模块（1周）
- [ ] 封装 MediaCrawler 调用接口
- [ ] 实现评论区抓取 API
- [ ] 实现抓取任务队列（Celery）
- [ ] 客户数据入库与去重

### Phase 3: AI 分析模块（1周）
- [ ] 创建 Dify 客户分类工作流
- [ ] 创建 Dify 私信生成工作流
- [ ] 接入工作流 API
- [ ] 实现客户意向度评分

### Phase 4: 前端界面（1周）
- [ ] 获客任务创建页面
- [ ] 客户列表展示页面
- [ ] 任务执行状态监控
- [ ] 私信模板管理页面

### Phase 5: 自动化触达（1周）
- [ ] 抖音账号 Cookie 管理
- [ ] 自动私信发送服务
- [ ] 发送频率控制策略
- [ ] 任务调度配置

### Phase 6: 完善优化（1周）
- [ ] 数据统计报表
- [ ] 团购客户抓取（扩展）
- [ ] 系统稳定性优化
- [ ] 风控策略完善

## 六、风险与合规

### 6.1 风险点
1. **平台风控** - 抖音可能检测并封禁异常账号
2. **数据合规** - 用户数据采集需符合法规
3. **私信限制** - 平台对私信频率有限制

### 6.2 应对策略
1. 控制抓取频率，模拟真实用户行为
2. 仅采集公开可见数据
3. 分散到多个账号，控制单账号发送量
4. 预留账号轮换机制

## 七、成功指标

| 指标 | 目标值 |
|------|--------|
| 日均抓取客户数 | 1,000+ |
| 私信送达率 | 95%+ |
| 客户响应率 | 5%+ |
| 微信添加成功率 | 2%+ |

## 八、最小化改动方案（评论区获客 MVP）

> 🎯 **设计原则**：遵循 Dify 现有架构模式，最小化新增文件，复用现有基础设施

### 8.1 文件改动清单

#### 📁 需要新增的文件（共 6 个）

```
api/
├── models/
│   └── leads.py                    # 新增：数据模型（2个表）
├── controllers/console/
│   └── leads.py                    # 新增：API 路由（1个文件搞定）
├── services/
│   └── leads_service.py            # 新增：业务逻辑服务
├── tasks/
│   └── lead_crawl_task.py          # 新增：Celery 异步任务
├── migrations/versions/
│   └── 2025_11_30_xxxx-lead_tables.py  # 新增：数据库迁移
└── fields/
    └── lead_fields.py              # 新增：响应字段定义

web/app/
├── (commonLayout)/leads/
│   └── page.tsx                    # 新增：获客页面（1个文件）
└── components/header/
    └── leads-nav/index.tsx         # 新增：导航入口
```

#### 📝 需要修改的文件（共 3 个）

```
api/
├── models/__init__.py              # 修改：导出新模型
├── controllers/console/__init__.py # 修改：注册新路由
web/
└── app/components/header/index.tsx # 修改：添加导航
```

### 8.2 数据库模型（api/models/leads.py）

```python
"""Lead acquisition models - following Dify's existing patterns"""
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TypeBase
from .types import LongText, StringUUID


class LeadTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    INVALID = "invalid"


class LeadTask(TypeBase):
    """获客任务表 - 遵循 Dify TypeBase 模式"""
    __tablename__ = "lead_tasks"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="lead_task_pkey"),
        sa.Index("lead_task_tenant_idx", "tenant_id"),
        sa.Index("lead_task_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="douyin")
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class Lead(TypeBase):
    """潜在客户表"""
    __tablename__ = "leads"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="lead_pkey"),
        sa.Index("lead_tenant_idx", "tenant_id"),
        sa.Index("lead_task_idx", "task_id"),
        sa.Index("lead_status_idx", "status"),
        sa.Index("lead_intent_idx", "intent_score"),
        sa.UniqueConstraint(
            "tenant_id", "platform", "platform_user_id",
            name="unique_lead_platform_user"
        ),
    )

    id: Mapped[str] = mapped_column(
        StringUUID, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    task_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True)
    platform: Mapped[str] = mapped_column(String(50), default="douyin")
    platform_user_id: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(255))
    comment_content: Mapped[str | None] = mapped_column(Text)
    source_video_url: Mapped[str | None] = mapped_column(Text)
    source_video_title: Mapped[str | None] = mapped_column(Text)
    intent_score: Mapped[int] = mapped_column(sa.Integer, default=0)
    intent_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="new")
    contacted_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
```

### 8.3 Controller 路由（api/controllers/console/leads.py）

```python
"""Lead acquisition API - single file, following Dify patterns"""
from flask import request
from flask_restx import Resource, fields, marshal_with, reqparse
from werkzeug.exceptions import NotFound

from controllers.console import console_ns
from controllers.console.wraps import (
    account_initialization_required,
    setup_required,
)
from libs.login import current_account_with_tenant, login_required
from services.leads_service import LeadService, LeadTaskService


# === 获客任务 API ===
@console_ns.route("/lead-tasks")
class LeadTaskListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """获取任务列表"""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        tasks = LeadTaskService.get_tasks(tenant_id, page, limit)
        return tasks

    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """创建获客任务"""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json()
        task = LeadTaskService.create_task(
            tenant_id=tenant_id,
            created_by=account.id,
            **data
        )
        return task, 201


@console_ns.route("/lead-tasks/<uuid:task_id>")
class LeadTaskApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, task_id):
        """获取任务详情"""
        _, tenant_id = current_account_with_tenant()
        task = LeadTaskService.get_task(tenant_id, str(task_id))
        if not task:
            raise NotFound("Task not found")
        return task

    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, task_id):
        """删除任务"""
        _, tenant_id = current_account_with_tenant()
        LeadTaskService.delete_task(tenant_id, str(task_id))
        return {"result": "success"}, 204


@console_ns.route("/lead-tasks/<uuid:task_id>/run")
class LeadTaskRunApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, task_id):
        """执行任务"""
        _, tenant_id = current_account_with_tenant()
        LeadTaskService.run_task(tenant_id, str(task_id))
        return {"result": "success", "message": "Task started"}


# === 潜在客户 API ===
@console_ns.route("/leads")
class LeadListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """获取客户列表"""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status")
        min_intent = request.args.get("min_intent", type=int)
        
        leads = LeadService.get_leads(
            tenant_id, page, limit, status, min_intent
        )
        return leads


@console_ns.route("/leads/<uuid:lead_id>")
class LeadApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, lead_id):
        """获取客户详情"""
        _, tenant_id = current_account_with_tenant()
        lead = LeadService.get_lead(tenant_id, str(lead_id))
        if not lead:
            raise NotFound("Lead not found")
        return lead

    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, lead_id):
        """更新客户状态"""
        _, tenant_id = current_account_with_tenant()
        data = request.get_json()
        lead = LeadService.update_lead(tenant_id, str(lead_id), **data)
        return lead
```

### 8.4 修改文件清单

#### 修改 api/models/__init__.py（添加 2 行）

```python
# 在现有导入后添加
from .leads import Lead, LeadTask, LeadStatus, LeadTaskStatus

# 在 __all__ 列表中添加
__all__ = [
    # ... 现有内容 ...
    "Lead",
    "LeadTask",
    "LeadStatus",
    "LeadTaskStatus",
]
```

#### 修改 api/controllers/console/__init__.py（添加 1 行）

```python
# 在现有导入后添加
from . import leads

# 在 __all__ 列表中添加
__all__ = [
    # ... 现有内容 ...
    "leads",
]
```

#### 修改 web/app/components/header/index.tsx（添加导航）

```typescript
// 导入 LeadsNav
import LeadsNav from './leads-nav'

// 在导航区域添加（与 ToolsNav 同级）
{!isCurrentWorkspaceDatasetOperator && <LeadsNav className={navClassName} />}
```

### 8.5 Service 服务（api/services/leads_service.py）

```python
"""Lead service - business logic layer"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.leads import Lead, LeadTask, LeadTaskStatus
from tasks.lead_crawl_task import crawl_douyin_comments_task


class LeadTaskService:
    @staticmethod
    def get_tasks(tenant_id: str, page: int, limit: int):
        with Session(db.engine) as session:
            query = (
                select(LeadTask)
                .where(LeadTask.tenant_id == tenant_id)
                .order_by(LeadTask.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            tasks = session.scalars(query).all()
            return {"data": [t.__dict__ for t in tasks], "page": page}

    @staticmethod
    def create_task(tenant_id: str, created_by: str, **kwargs) -> dict:
        task = LeadTask(
            tenant_id=tenant_id,
            created_by=created_by,
            name=kwargs["name"],
            task_type=kwargs.get("task_type", "comment_crawl"),
            config=kwargs.get("config", {}),
        )
        db.session.add(task)
        db.session.commit()
        return {"id": task.id, "name": task.name, "status": task.status}

    @staticmethod
    def run_task(tenant_id: str, task_id: str):
        task = db.session.query(LeadTask).filter_by(
            id=task_id, tenant_id=tenant_id
        ).first()
        if task:
            task.status = LeadTaskStatus.RUNNING
            db.session.commit()
            # 触发 Celery 异步任务
            crawl_douyin_comments_task.delay(task_id)


class LeadService:
    @staticmethod
    def get_leads(tenant_id: str, page: int, limit: int, 
                  status: str = None, min_intent: int = None):
        query = select(Lead).where(Lead.tenant_id == tenant_id)
        if status:
            query = query.where(Lead.status == status)
        if min_intent:
            query = query.where(Lead.intent_score >= min_intent)
        query = query.order_by(Lead.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        
        with Session(db.engine) as session:
            leads = session.scalars(query).all()
            return {"data": [l.__dict__ for l in leads], "page": page}
```

### 8.6 Celery 任务（api/tasks/lead_crawl_task.py）

```python
"""Lead crawling async task"""
import logging
from celery import shared_task

from extensions.ext_database import db
from models.leads import Lead, LeadTask, LeadTaskStatus

logger = logging.getLogger(__name__)


@shared_task(queue="dataset")  # 复用现有队列
def crawl_douyin_comments_task(task_id: str):
    """
    异步抓取抖音评论任务
    复用 Dify 现有的 Celery 基础设施
    """
    logger.info(f"Starting crawl task: {task_id}")
    
    task = db.session.query(LeadTask).filter_by(id=task_id).first()
    if not task:
        logger.error(f"Task not found: {task_id}")
        return

    try:
        config = task.config
        # TODO: 集成 MediaCrawler 调用
        # 1. 调用 MediaCrawler 抓取评论
        # 2. 解析结果，写入 leads 表
        # 3. 可选：调用 Dify 工作流进行意向分析
        
        task.status = LeadTaskStatus.COMPLETED
        task.result_summary = {"total_leads": 0}
        db.session.commit()
        
    except Exception as e:
        logger.exception(f"Task failed: {task_id}")
        task.status = LeadTaskStatus.FAILED
        task.error_message = str(e)
        db.session.commit()
```

### 8.7 前端页面（复用 Dify 现有组件）

> 🎯 **复用原则**：使用 Dify 现有组件和模式，保持 UI 风格一致

#### 可复用的 Dify 组件

| 组件 | 路径 | 用途 |
|------|------|------|
| `Input` | `@/app/components/base/input` | 搜索框 |
| `Button` | `@/app/components/base/button` | 按钮 |
| `TabSliderNew` | `@/app/components/base/tab-slider-new` | 标签切换 |
| `Pagination` | `@/app/components/base/pagination` | 分页组件 |
| `Badge` | `@/app/components/base/badge` | 状态/意向度标签 |
| `Modal` | `@/app/components/base/modal` | 弹窗 |
| `Confirm` | `@/app/components/base/confirm` | 确认对话框 |
| `Toast` | `@/app/components/base/toast` | 通知提示 |
| `Loading` | `@/app/components/base/loading` | 加载状态 |
| `Empty` | `@/app/components/apps/empty` | 空状态 |

#### 新增文件清单（3个）

```
web/
├── service/
│   └── use-leads.ts                      # 新增：API 调用 hooks
└── app/
    ├── (commonLayout)/leads/
    │   └── page.tsx                      # 新增：获客页面
    └── components/header/
        └── leads-nav/index.tsx           # 新增：导航组件
```

#### 1. Service 层（web/service/use-leads.ts）

```typescript
/**
 * Lead service hooks - 遵循 Dify 的 useQuery 模式
 * 参考: web/service/use-apps.ts
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, del, patch } from './base'

const NAME_SPACE = 'leads'

// Lead 类型定义
export interface Lead {
  id: string
  nickname: string
  platform_user_id: string
  comment_content: string
  intent_score: number
  intent_tags: string[]
  status: 'new' | 'contacted' | 'converted' | 'invalid'
  source_video_title: string
  created_at: string
}

export interface LeadTask {
  id: string
  name: string
  platform: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  config: Record<string, any>
  result_summary?: Record<string, any>
  created_at: string
}

interface LeadListResponse {
  data: Lead[]
  total: number
  page: number
  has_more: boolean
}

interface LeadTaskListResponse {
  data: LeadTask[]
  total: number
  page: number
}

// ===== Lead Hooks =====
export const useLeadList = (params: { 
  page?: number
  limit?: number
  status?: string
  min_intent?: number 
}) => {
  return useQuery<LeadListResponse>({
    queryKey: [NAME_SPACE, 'list', params],
    queryFn: () => get<LeadListResponse>('/leads', { params }),
  })
}

export const useUpdateLead = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Lead>) => 
      patch(`/leads/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'list'] })
    },
  })
}

// ===== Lead Task Hooks =====
export const useLeadTaskList = (params: { page?: number; limit?: number }) => {
  return useQuery<LeadTaskListResponse>({
    queryKey: [NAME_SPACE, 'tasks', params],
    queryFn: () => get<LeadTaskListResponse>('/lead-tasks', { params }),
  })
}

export const useCreateLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<LeadTask>) => 
      post('/lead-tasks', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

export const useRunLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => 
      post(`/lead-tasks/${taskId}/run`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

export const useDeleteLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => del(`/lead-tasks/${taskId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}
```

#### 2. 导航组件（web/app/components/header/leads-nav/index.tsx）

```typescript
/**
 * LeadsNav - 遵循 Dify 导航组件模式
 * 参考: web/app/components/header/tools-nav/index.tsx
 */
'use client'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useSelectedLayoutSegment } from 'next/navigation'
import { RiUserSearchLine } from '@remixicon/react'
import classNames from '@/utils/classnames'

type Props = { className?: string }

const LeadsNav = ({ className }: Props) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const isActive = selectedSegment === 'leads'

  return (
    <Link
      href="/leads"
      className={classNames(
        className,
        'group',
        isActive 
          ? 'bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text-active' 
          : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover'
      )}
    >
      <RiUserSearchLine className='mr-1 h-4 w-4' />
      {t('common.menus.leads') || '获客'}
    </Link>
  )
}

export default LeadsNav
```

#### 3. 获客页面（web/app/(commonLayout)/leads/page.tsx）

```typescript
/**
 * Leads Page - 遵循 Dify Apps 列表页模式
 * 参考: web/app/components/apps/list.tsx
 */
'use client'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RiAddLine, RiPlayLine, RiDeleteBinLine } from '@remixicon/react'
import { useLeadList, useLeadTaskList, useCreateLeadTask, useRunLeadTask, useUpdateLead } from '@/service/use-leads'
import type { Lead, LeadTask } from '@/service/use-leads'
import { useAppContext } from '@/context/app-context'
import useDocumentTitle from '@/hooks/use-document-title'
// 复用 Dify 现有组件
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Pagination from '@/app/components/base/pagination'
import Badge from '@/app/components/base/badge'
import Modal from '@/app/components/base/modal'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'

// 意向度颜色映射
const getIntentColor = (score: number) => {
  if (score >= 80) return 'bg-util-colors-green-green-500'
  if (score >= 60) return 'bg-util-colors-blue-blue-500'
  if (score >= 40) return 'bg-util-colors-orange-orange-500'
  return 'bg-util-colors-gray-gray-500'
}

// 状态颜色映射
const statusConfig = {
  new: { label: '新客户', color: 'blue' },
  contacted: { label: '已联系', color: 'orange' },
  converted: { label: '已转化', color: 'green' },
  invalid: { label: '无效', color: 'gray' },
}

const LeadsPage = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('common.menus.leads') || '获客')
  
  const [activeTab, setActiveTab] = useState<string>('leads')
  const [page, setPage] = useState(0)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  // 使用复用的 hooks
  const { data: leadsData, isLoading: leadsLoading } = useLeadList({ 
    page: page + 1, 
    limit: 20 
  })
  const { data: tasksData, isLoading: tasksLoading } = useLeadTaskList({ 
    page: 1, 
    limit: 50 
  })
  const createTask = useCreateLeadTask()
  const runTask = useRunLeadTask()
  const updateLead = useUpdateLead()

  const tabs = [
    { value: 'leads', text: '客户列表' },
    { value: 'tasks', text: '获客任务' },
  ]

  const handleCreateTask = useCallback(async (data: Partial<LeadTask>) => {
    try {
      await createTask.mutateAsync(data)
      Toast.notify({ type: 'success', message: '任务创建成功' })
      setShowCreateModal(false)
    } catch (e) {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }, [createTask])

  const handleRunTask = useCallback(async (taskId: string) => {
    try {
      await runTask.mutateAsync(taskId)
      Toast.notify({ type: 'success', message: '任务已启动' })
    } catch (e) {
      Toast.notify({ type: 'error', message: '启动失败' })
    }
  }, [runTask])

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      {/* Header - 复用 Dify 布局模式 */}
      <div className='sticky top-0 z-10 flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-7'>
        <TabSliderNew
          value={activeTab}
          onChange={setActiveTab}
          options={tabs}
        />
        <div className='flex items-center gap-2'>
          <Input
            showLeftIcon
            showClearIcon
            wrapperClassName='w-[200px]'
            value={searchKeyword}
            placeholder='搜索客户...'
            onChange={e => setSearchKeyword(e.target.value)}
            onClear={() => setSearchKeyword('')}
          />
          <Button 
            variant='primary'
            onClick={() => setShowCreateModal(true)}
          >
            <RiAddLine className='mr-1 h-4 w-4' />
            新建任务
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className='px-12 pb-6'>
        {activeTab === 'leads' && (
          <>
            {leadsLoading ? (
              <Loading type='area' />
            ) : (
              <>
                <div className='rounded-xl border border-divider-subtle bg-components-panel-bg'>
                  <table className='w-full'>
                    <thead>
                      <tr className='border-b border-divider-subtle'>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>昵称</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>评论内容</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>来源</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>意向度</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>状态</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leadsData?.data?.map((lead: Lead) => (
                        <tr key={lead.id} className='border-b border-divider-subtle last:border-0 hover:bg-background-default-hover'>
                          <td className='px-4 py-3 text-sm text-text-secondary'>{lead.nickname}</td>
                          <td className='max-w-[300px] truncate px-4 py-3 text-sm text-text-secondary'>{lead.comment_content}</td>
                          <td className='max-w-[200px] truncate px-4 py-3 text-sm text-text-tertiary'>{lead.source_video_title}</td>
                          <td className='px-4 py-3'>
                            <div className='flex items-center gap-2'>
                              <div className={`h-2 w-2 rounded-full ${getIntentColor(lead.intent_score)}`} />
                              <span className='text-sm text-text-secondary'>{lead.intent_score}</span>
                            </div>
                          </td>
                          <td className='px-4 py-3'>
                            <Badge color={statusConfig[lead.status].color as any}>
                              {statusConfig[lead.status].label}
                            </Badge>
                          </td>
                          <td className='px-4 py-3'>
                            <Button variant='ghost' size='small'>详情</Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  
                  {(!leadsData?.data || leadsData.data.length === 0) && (
                    <div className='py-12 text-center text-text-tertiary'>
                      暂无客户数据，请先创建获客任务
                    </div>
                  )}
                </div>
                
                {leadsData && leadsData.total > 0 && (
                  <Pagination
                    className='mt-4'
                    current={page}
                    onChange={setPage}
                    total={leadsData.total}
                    limit={20}
                  />
                )}
              </>
            )}
          </>
        )}

        {activeTab === 'tasks' && (
          <>
            {tasksLoading ? (
              <Loading type='area' />
            ) : (
              <div className='grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3'>
                {tasksData?.data?.map((task: LeadTask) => (
                  <div 
                    key={task.id} 
                    className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4 hover:shadow-sm'
                  >
                    <div className='mb-3 flex items-center justify-between'>
                      <h3 className='font-medium text-text-secondary'>{task.name}</h3>
                      <Badge color={task.status === 'completed' ? 'green' : task.status === 'running' ? 'blue' : 'gray'}>
                        {task.status}
                      </Badge>
                    </div>
                    <div className='mb-4 text-sm text-text-tertiary'>
                      {task.task_type} · {task.platform}
                    </div>
                    <div className='flex gap-2'>
                      {task.status === 'pending' && (
                        <Button 
                          variant='primary' 
                          size='small'
                          onClick={() => handleRunTask(task.id)}
                        >
                          <RiPlayLine className='mr-1 h-3 w-3' />
                          执行
                        </Button>
                      )}
                      <Button variant='ghost' size='small'>
                        <RiDeleteBinLine className='h-3 w-3' />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* 创建任务弹窗 - 复用 Modal 组件 */}
      <Modal
        isShow={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title='创建获客任务'
      >
        <CreateTaskForm 
          onSubmit={handleCreateTask}
          onCancel={() => setShowCreateModal(false)}
        />
      </Modal>
    </div>
  )
}

// 创建任务表单组件
const CreateTaskForm = ({ 
  onSubmit, 
  onCancel 
}: { 
  onSubmit: (data: Partial<LeadTask>) => void
  onCancel: () => void 
}) => {
  const [name, setName] = useState('')
  const [videoUrl, setVideoUrl] = useState('')

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>任务名称</label>
        <Input 
          value={name} 
          onChange={e => setName(e.target.value)}
          placeholder='如：装修行业获客'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>抖音视频链接</label>
        <Input 
          value={videoUrl} 
          onChange={e => setVideoUrl(e.target.value)}
          placeholder='粘贴抖音视频链接'
        />
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>取消</Button>
        <Button 
          variant='primary' 
          onClick={() => onSubmit({ 
            name, 
            task_type: 'comment_crawl',
            config: { video_urls: [videoUrl] }
          })}
          disabled={!name || !videoUrl}
        >
          创建
        </Button>
      </div>
    </div>
  )
}

export default LeadsPage
```

#### 4. 修改 Header（添加导航入口）

```typescript
// web/app/components/header/index.tsx
// 在导入部分添加
import LeadsNav from './leads-nav'

// 在导航区域添加（与 ToolsNav 同级）
{!isCurrentWorkspaceDatasetOperator && <LeadsNav className={navClassName} />}
```

### 8.8 改动量统计

| 类型 | 文件数 | 说明 |
|------|--------|------|
| **后端新增** | 4 | models/leads.py, controllers/leads.py, services/leads_service.py, tasks/lead_crawl_task.py |
| **后端修改** | 2 | models/__init__.py, controllers/__init__.py |
| **前端新增** | 2 | service/use-leads.ts, (commonLayout)/leads/page.tsx, header/leads-nav |
| **前端修改** | 1 | header/index.tsx（添加1行导航） |
| **数据库** | 1 | migration 迁移文件 |
| **总计** | **10** | 完全复用现有架构和组件 |

#### 复用的 Dify 前端组件

- ✅ `Input` - 搜索框
- ✅ `Button` - 按钮（primary/secondary/ghost）
- ✅ `TabSliderNew` - 标签切换
- ✅ `Pagination` - 分页（带跳转）
- ✅ `Badge` - 状态标签
- ✅ `Modal` - 弹窗
- ✅ `Toast` - 通知提示
- ✅ `Loading` - 加载状态
- ✅ `useQuery/useMutation` - 数据请求模式

### 8.9 遵循的 Dify 架构模式

✅ **Controller**: 使用 `@console_ns.route` 装饰器，继承 `Resource`  
✅ **Model**: 继承 `TypeBase`，使用 `StringUUID` 类型  
✅ **Service**: 静态方法，使用 `Session(db.engine)` 上下文  
✅ **Task**: 使用 `@shared_task(queue="dataset")` 复用现有队列  
✅ **Migration**: 遵循 Alembic 格式，支持 PostgreSQL/MySQL

---

**文档版本：** v1.1  
**创建日期：** 2025-11-30  
**更新日期：** 2025-11-30  
**状态：** 设计阶段 - 待确认
