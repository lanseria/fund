# Fund Investment Assistant (基金投资助手)

一个基于 Python 的基金投资助手后台服务，提供 API 和 CLI 两种交互方式，帮助用户管理和分析其持有的基金。

该项目使用现代 Python 技术栈构建，包括 FastAPI, Typer, SQLAlchemy, และ uv，并遵循清晰的分层架构设计。

## ✨ 主要功能

-   **持仓管理**: 通过 API 或命令行 (CLI) 添加、查询、修改和删除个人持有的基金。
-   **数据同步**:
    -   定时任务每日自动更新基金的历史净值数据。
    -   定时任务在交易时段内自动更新基金的盘中实时估值。
-   **数据分析**: 查询指定基金的历史净值，并计算 5日、10日、20日移动平均线。
-   **API 服务**: 基于 FastAPI 提供了一套 RESTful API，方便与前端应用（如 Nuxt3）集成。
-   **命令行工具**: 基于 Typer 提供了一套易用的命令行工具，方便在终端进行快速操作。
-   **数据库支持**: 使用 PostgreSQL 数据库，并支持自定义 Schema 进行数据隔离。

## 🛠️ 技术栈

-   **后台框架**: FastAPI
-   **命令行框架**: Typer
-   **数据库 ORM**: SQLAlchemy
-   **数据库**: PostgreSQL
-   **项目管理与打包**: uv (替代 pip 和 venv)
-   **数据校验**: Pydantic
-   **定时任务**: Schedule
-   **代码测试**: Pytest

## 🚀 快速开始

### 1. 环境准备

-   **安装 uv**:
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows (PowerShell)
    irm https://astral.sh/uv/install.ps1 | iex
    ```

-   **安装 PostgreSQL**:
    请确保您本地或服务器上已安装并运行 PostgreSQL 服务。

-   **创建数据库**:
    使用您喜欢的数据库工具（如 `psql`, DBeaver）连接到 PostgreSQL 并创建一个新的数据库。
    ```sql
    CREATE DATABASE fund_assistant;
    ```

### 2. 项目配置

-   **克隆项目**:
    ```bash
    git clone <your-repo-url>
    cd fund-server
    ```

-   **创建 `.env` 文件**:
    在项目根目录下，复制 `.env.example` (如果提供) 或手动创建一个名为 `.env` 的文件，并填入您的数据库配置信息。

    ```dotenv
    # .env

    # 数据库连接字符串 (请替换为您的真实配置)
    DATABASE_URL="postgresql://your_user:your_password@localhost:5432/fund_assistant"

    # 自定义数据库 Schema (推荐)
    DB_SCHEMA="fund_app"
    ```

### 3. 安装与运行

-   **创建并激活虚拟环境**:
    ```bash
    # 创建虚拟环境
    uv venv

    # 激活虚拟环境 (macOS / Linux)
    source .venv/bin/activate
    ```

-   **安装项目依赖**:
    `uv` 会读取 `pyproject.toml` 并以极快的速度安装所有依赖。
    ```bash
    uv pip install -e .
    ```

-   **运行数据库迁移**:
    项目首次运行时，会自动根据模型在指定的 Schema 下创建数据表。

### 4. 启动服务

本项目提供两种服务模式，您可以根据需要启动一个或两个。

-   **启动 API 服务**:
    使用 `uvicorn` 运行 FastAPI 应用。`--reload` 参数会在代码变动时自动重启服务。
    ```bash
    uv run uvicorn src.python_cli_starter.main:api_app --reload
    ```
    服务启动后，您可以在浏览器中访问 `http://127.0.0.1:8000/docs` 查看自动生成的 API 文档 (Swagger UI)。

-   **启动定时任务服务 (待实现)**:
    (当前蓝图中已规划，需要创建一个单独的脚本来运行 `scheduler.py` 中的 `run_scheduler()` 函数)
    ```bash
    # 示例 (需要创建一个 run_scheduler.py 脚本)
    # uv run python run_scheduler.py
    ```

## ⌨️ 命令行 (CLI) 用法

您可以使用 `uv run cli` 来执行所有命令行操作，无需手动激活虚拟环境。

-   **查看所有命令**:
    ```bash
    uv run cli --help
    ```

-   **添加一个新的持仓基金**:
    ```bash
    uv run cli add-holding --code "161725" --amount 5000
    ```
    *   `--code` / `-c`: 基金代码 (必填)
    *   `--amount` / `-a`: 持有金额 (必填)
    *   `--name` / `-n`: 基金名称 (可选, 程序会自动尝试获取)


-   **(未来可添加) 查看所有持仓**:
    ```bash
    # 示例
    # uv run cli list-holdings
    ```

## ✅ 运行测试

项目使用 `pytest` 进行自动化测试，测试用例位于 `tests/` 目录下。测试会使用一个独立的内存数据库，不会影响您的主数据。

```bash
uv run pytest
```

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
├── tests/                  # 测试用例
│   ├── conftest.py         # Pytest 配置文件和 Fixtures
│   └── test_api.py         # API 接口测试
├── .env                    # 环境变量 (本地配置，不提交到 git)
├── pyproject.toml          # 项目配置文件 (依赖、元数据等)
└── README.md               # 项目说明文档
```

## 📄 License

MIT