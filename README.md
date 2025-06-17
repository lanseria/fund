
# Fund Investment Assistant - Backend Server

这是基金投资助手项目的 **Python 后端服务**。它使用 FastAPI, SQLAlchemy 和 Typer 构建，负责所有核心业务逻辑、数据处理和 API 服务。

## ✨ 主要功能

-   **RESTful API**: 提供一套完整的 API 用于管理基金持仓（增删改查）和查询历史数据。
-   **数据同步服务**: 内置一个与 API 服务共同运行的定时任务调度器，负责：
    -   每日自动增量更新所有持仓基金的历史净值。
    -   在交易时段内定时更新基金的实时估值。
-   **命令行工具 (CLI)**: 提供了一套管理命令，方便在服务器端进行手动数据同步、添加持仓等操作。
-   **数据库支持**: 使用 PostgreSQL，并支持自定义 Schema 进行数据隔离。

## 🛠️ 技术栈

-   **Web 框架**: FastAPI
-   **命令行框架**: Typer
-   **数据库 ORM**: SQLAlchemy
-   **数据库**: PostgreSQL
-   **项目管理**: uv (替代 pip 和 venv)
-   **定时任务**: Schedule
-   **HTTP 客户端**: httpx

## 🚀 本地开发环境设置

### 1. 环境准备

-   **安装 uv**:
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
-   **安装 PostgreSQL**: 确保本地已安装并运行 PostgreSQL 服务。
-   **创建数据库**:
    ```sql
    CREATE DATABASE fund_assistant;
    ```

### 2. 项目配置

-   **创建 `.env` 文件**: 在项目根目录下，创建一个名为 `.env` 的文件，并填入您的本地数据库配置。
    ```dotenv
    # .env
    DATABASE_URL="postgresql://your_user:your_password@localhost:5432/fund_assistant"
    DB_SCHEMA="fund_app"
    ```

### 3. 安装与运行

-   **创建并激活虚拟环境**:
    ```bash
    uv venv
    source .venv/bin/activate
    ```
-   **安装项目依赖**:
    ```bash
    uv pip install -e .
    ```
-   **启动 API 及定时任务服务**:
    ```bash
    uv run python -m uvicorn src.python_cli_starter.main:api_app --reload
    ```
    服务启动后，定时任务会自动在后台运行。您可以在 `http://127.0.0.1:8888/docs` 查看 API 文档。

---

## 🐳 生产环境 Docker 部署

我们使用 Docker 和 Docker Compose 进行生产环境的部署。部署流程分为**构建镜像**和**运行容器**两个步骤。

### 1. 环境准备

-   **安装 Docker 和 Docker Compose**。
-   **准备外部 Docker 网络**: 我们的服务被设计为连接到一个外部共享网络，以便与数据库等其他服务通信。如果网络不存在，请先创建它：
    ```bash
    docker network create shared-db-network
    ```
-   **准备生产环境变量文件**: 创建一个名为 `.env.prod` 的文件，用于存放生产环境的配置。
    ```dotenv
    # .env.prod
    # 注意：DATABASE_URL 中的主机名应为数据库容器在 Docker 网络中的服务名
    DATABASE_URL="postgresql://prod_user:prod_password@postgres_container_name:5432/prod_db"
    DB_SCHEMA="fund_production"
    ```

### 2. 构建 Docker 镜像 (打包)

此步骤会根据 `Dockerfile` 创建一个包含您的应用和所有依赖的 Docker 镜像。

在项目根目录下，运行以下命令：
```bash
docker build -t fund-server:latest .
```
-   `-t fund-server:latest`: 为构建的镜像指定一个名称 (`fund-server`) 和一个标签 (`latest`)。您可以根据版本控制策略修改标签，例如 `fund-server:v1.0.2`。
-   `.`: 指定 Docker build 的上下文为当前目录。

### 3. 运行服务 (Docker Compose)

我们使用 `docker-compose.yml` 文件来定义和运行我们的服务容器。

**首先，确保您的 `docker-compose.yml` 文件已配置好**:
```yaml
# docker-compose.yml
services:
  fund_service:
    image: fund-server:latest # 使用我们刚刚构建的镜像
    container_name: fund_service
    env_file:
      - .env.prod # 加载生产环境变量
    ports:
      - "8888:8888"
    command: >
      sh -c "python -m uvicorn src.python_cli_starter.main:api_app --host 0.0.0.0 --port 8888"
    restart: unless-stopped
    networks:
      - shared_app_net

networks:
  shared_app_net:
    external: true
    name: shared-db-network
```

**然后，使用以下命令启动服务**:
```bash
docker-compose up -d
```
-   `-d`: 在后台（detached mode）运行容器。
-   Docker Compose 会自动找到 `docker-compose.yml` 文件，并根据定义启动 `fund_service`。

### 4. 常用 Docker 命令

-   **查看服务日志**:
    ```bash
    docker-compose logs -f fund_service
    ```
-   **停止并移除容器**:
    ```bash
    docker-compose down
    ```
-   **进入容器执行 CLI 命令**:
    如果您需要手动执行一个 CLI 命令（例如 `sync-history`），可以使用 `docker-compose exec`：
    ```bash
    docker-compose exec fund_service cli sync-history
    ```

---

## 📄 License

MIT