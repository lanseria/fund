import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 导入你的主应用和数据库模型
from python_cli_starter.main import app, get_db
from python_cli_starter.models import Base

# --- 配置测试数据库 ---
# 使用内存中的SQLite数据库进行测试
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    # StaticPool 确保每个测试会话都使用同一个连接，这对于内存数据库是必需的
    poolclass=StaticPool,
    # connect_args 是SQLite特有的，允许多个线程共享同一个连接
    connect_args={"check_same_thread": False},
)

# 创建一个用于测试的数据库会话生成器
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 创建 Fixtures ---

@pytest.fixture(scope="function")
def db_session():
    """
    这是一个pytest fixture，它会在每个测试函数运行前执行。
    1. 创建所有数据库表。
    2. 提供一个数据库会话 (yield)。
    3. 测试函数结束后，删除所有数据库表，保持环境干净。
    """
    # 在数据库中创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # yield 关键字是fixture的核心，它将db会话对象提供给测试函数
        yield db
    finally:
        # 测试结束后，关闭会话
        db.close()

    # 删除所有表，确保下一个测试是全新的环境
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    创建一个API测试客户端，它会使用我们临时的测试数据库。
    """
    def override_get_db():
        """
        这是一个依赖覆盖函数。它会替换掉FastAPI应用中原始的 get_db，
        让API在测试时连接到我们的临时数据库，而不是生产数据库。
        """
        try:
            yield db_session
        finally:
            db_session.close()

    # 使用依赖覆盖
    app.dependency_overrides[get_db] = override_get_db

    # 创建并返回一个与app绑定的测试客户端
    with TestClient(app) as c:
        yield c
    
    # 清理依赖覆盖，以免影响其他测试
    app.dependency_overrides.clear()