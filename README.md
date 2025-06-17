# Fund Investment Assistant (基金投资助手)

一个基于 Python 的基金投资助手后台服务，提供 API 和 CLI 两种交互方式，帮助用户管理和分析其持有的基金。

该项目使用现代 Python 技术栈构建，包括 FastAPI, Typer, SQLAlchemy, 和 uv，并遵循清晰的分层架构设计。

## ✨ 主要功能

-   **持仓管理**: 通过 API 或命令行 (CLI) 添加、查询、修改和删除个人持有的基金。
-   **数据同步**:
    -   定时任务每日自动更新基金的历史净值数据。
    -   定时任务在交易时段内自动更新基金的盘中实时估值。
    -   支持手动触发历史数据同步。
-   **数据展示**: 以美观的表格形式展示持仓组合及其预估盈亏。
-   **API 服务**: 基于 FastAPI 提供了一套 RESTful API，方便与前端应用（如 Nuxt3）集成。
-   **命令行工具**: 基于 Typer 提供了一套易用的命令行工具，方便在终端进行快速操作。

## 🚀 快速开始

### 1. 环境准备

-   **安装 uv**:
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
-   **安装 PostgreSQL**: 确保本地或服务器上已安装并运行 PostgreSQL 服务。
-   **创建数据库**:
    ```sql
    CREATE DATABASE fund_assistant;
    ```

### 2. 项目配置

-   **克隆项目**并进入目录。
-   **创建 `.env` 文件**: 在项目根目录下，创建一个名为 `.env` 的文件，并填入您的数据库配置信息。
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

-   **启动 API 服务**:
    ```bash
    uv run uvicorn src.python_cli_starter.main:api_app --reload
    ```
    服务启动后，可在 `http://127.0.0.1:8000/docs` 查看 API 文档。

---

## 📖 使用指南

您可以通过 **命令行 (CLI)** 或 **API (curl)** 两种方式与本应用交互。

### 命令行 (CLI) 用法

所有命令都通过 `uv run cli` 执行，无需手动激活虚拟环境。

#### **查看所有持仓**
以表格形式列出所有持仓基金及其预估盈亏。
```bash
uv run cli list-holdings
```

#### **添加新的持仓**
```bash
# 示例：添加一只基金，持有金额为 5000
uv run cli add-holding --code "161725" --amount 5000
```
-   `--code` / `-c`: 基金代码 (**必填**)
-   `--amount` / `-a`: 持有金额 (**必填**)
-   `--name` / `-n`: 基金名称 (可选, 程序会自动获取)

#### **更新持仓金额**
```bash
# 示例：将代码为 161725 的基金持有金额更新为 6500
uv run cli update-holding --code "161725" --amount 6500
```
-   `--code` / `-c`: 要更新的基金代码 (**必填**)
-   `--amount` / `-a`: 新的持有金额 (**必填**)

#### **删除持仓记录**
此操作会进行交互式确认，防止误删。
```bash
# 示例：删除代码为 161725 的基金
uv run cli delete-holding 161725
```
> ⚠️ 您确定要删除基金代码为 **161725** 的所有记录吗？此操作不可撤销！ [y/N]:

如果要跳过确认（例如在脚本中使用），可以添加 `--force` 标志：
```bash
uv run cli delete-holding 161725 --force
```

#### **手动同步历史数据**
立即触发一次所有持仓基金的历史净值同步任务。
```bash
uv run cli sync-history
```

---

### API (curl) 用法

请确保 API 服务正在运行 (`uv run uvicorn ...`)。

#### **GET /holdings/ - 查询所有持仓**
```bash
curl -X GET "http://127.0.0.1:8000/holdings/"
```

#### **POST /holdings/ - 添加新的持仓**
```bash
curl -X POST "http://127.0.0.1:8000/holdings/" \
-H "Content-Type: application/json" \
-d '{
    "code": "005827",
    "name": "易方达蓝筹精选",
    "holding_amount": 10000.00
}'
```

#### **GET /holdings/{fund_code}/history - 查询单只基金历史及均线**
```bash
curl -X GET "http://127.0.0.1:8000/holdings/005827/history"
```

#### **PUT /holdings/{fund_code} - 更新持仓金额**
```bash
curl -X PUT "http://127.0.0.1:8000/holdings/005827" \
-H "Content-Type: application/json" \
-d '{
    "holding_amount": 12500.50
}'
```

#### **DELETE /holdings/{fund_code} - 删除持仓记录**
成功的删除请求将返回 `204 No Content` 状态码，没有响应体。使用 `-v` 参数可以查看响应头信息。
```bash
curl -X DELETE "http://127.0.0.1:8000/holdings/005827" -v
```

---

## 🏗️ 项目结构

```
.
├── src/
│   └── python_cli_starter/
│       ├── __init__.py
│       ├── cli.py          # CLI 命令定义 (Typer)
│       ├── crud.py         # 数据库 CRUD 操作 (适配 API)
│       ├── data_fetcher.py # 从网络获取数据的函数
│       ├── main.py         # API 服务入口 (FastAPI)
│       ├── models.py       # 数据库模型 (SQLAlchemy)
│       ├── schemas.py      # 数据校验模型 (Pydantic)
│       ├── services.py     # 核心业务逻辑层
│       └── scheduler.py    # 定时任务逻辑 (Schedule)
├── .env                    # 环境变量 (本地配置，不提交到 git)
├── pyproject.toml          # 项目配置文件 (依赖、元数据等)
└── README.md               # 项目说明文档
```

## 📄 License

MIT