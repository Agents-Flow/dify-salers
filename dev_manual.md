## 本地启动 Dify 指南

### 📋 前置要求

- **Node.js** >= v22.11.x + **pnpm** v10.x
- **Python** 3.12+ + **uv** (包管理器)
- **Docker** + **Docker Compose**

---

### 🚀 启动步骤

#### 1️⃣ 启动中间件服务（数据库、Redis、向量数据库）

```bash
cd /Users/xingqiangchen/dify-salers/docker
cp middleware.env.example middleware.env
docker compose -f docker-compose.middleware.yaml --profile postgresql --profile weaviate -p dify up -d
```

#### 2️⃣ 配置并启动后端 API

```bash
cd /Users/xingqiangchen/dify-salers/api
cp .env.example .env

# 生成 SECRET_KEY (Mac)
secret_key=$(openssl rand -base64 42)
sed -i '' "/^SECRET_KEY=/c\\
SECRET_KEY=${secret_key}" .env

# 安装依赖
uv sync --dev

# 运行数据库迁移（已完成）
uv run flask db upgrade

# 启动 API 服务
uv run flask run --host 0.0.0.0 --port=5001 --debug
```

#### 3️⃣ 启动 Celery Worker（异步任务处理）

在另一个终端：

```bash
cd /Users/xingqiangchen/dify-salers/api
uv run celery -A app.celery worker -P threads -c 2 --loglevel INFO -Q dataset,priority_dataset,priority_pipeline,pipeline,mail,ops_trace,app_deletion,plugin,workflow_storage,conversation,workflow,schedule_poller,schedule_executor,triggered_workflow_dispatcher,trigger_refresh_executor
```

#### 4️⃣ 配置并启动前端

在另一个终端：

```bash
cd /Users/xingqiangchen/dify-salers/web
cp .env.example .env.local
pnpm install
pnpm dev
```

---

### 🌐 访问地址

| 服务 | 地址 |
|------|------|
| **前端** | http://localhost:3000 |
| **后端 API** | http://localhost:5001 |
| **PostgreSQL** | localhost:5432 |
| **Redis** | localhost:6379 |

---

### ⚡ 快捷启动脚本

项目提供了便捷脚本：

```bash
# 启动 API
./dev/start-api

# 启动 Web
./dev/start-web

# 启动 Worker
./dev/start-worker
```
