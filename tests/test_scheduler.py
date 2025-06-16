# conftest.py (最终修正版)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (create_engine, MetaData, Column, String, Date, Float, 
                        Numeric, PrimaryKeyConstraint)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

# --- 导入需要被 Patch 的模块和原始的 FastAPI app ---
from python_cli_starter import main as main_app
from python_cli_starter import crud as crud_module
from python_cli_starter import services as services_module
from python_cli_starter import scheduler as scheduler_module

# ===============================================================
#  1. 创建一个完全隔离的、自给自_足的测试数据库环境
# ===============================================================

test_metadata = MetaData()
TestBase = declarative_base(metadata=test_metadata)

class TestHolding(TestBase):
    __tablename__ = "my_holdings"
    code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    yesterday_nav = Column(Numeric(10, 4), nullable=False)
    holding_amount = Column(Numeric(12, 2), nullable=False)
    today_estimate_nav = Column(Float, nullable=True)

class TestNavHistory(TestBase):
    __tablename__ = "fund_nav_history"
    code = Column(String, index=True)
    nav_date = Column(Date, index=True)
    nav = Column(Numeric(10, 4), nullable=False)
    __table_args__ = (PrimaryKeyConstraint('code', 'nav_date', name='pk_fund_date'),)

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, poolclass=StaticPool, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# ===============================================================
#  2. 使用 Monkeypatch 全面替换生产模型
# ===============================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """自动执行，将所有模块中对生产模型的引用替换为测试模型。"""
    
    # --- 核心改动在这里 ---
    # 对于 crud 和 services 模块，它们可能导入了整个 models 模块，所以替换 models
    # 为了安全起见，即使它们也是直接导入类，这种方式也能兼容
    fake_models_module = type('models', (), {'Holding': TestHolding, 'NavHistory': TestNavHistory})()
    monkeypatch.setattr(crud_module, "models", fake_models_module)
    monkeypatch.setattr(services_module, "models", fake_models_module)

    # 对于 scheduler 模块，我们直接替换它导入的类
    monkeypatch.setattr(scheduler_module, "Holding", TestHolding)
    monkeypatch.setattr(scheduler_module, "NavHistory", TestNavHistory)
    
    # 同时替换掉 SessionLocal
    monkeypatch.setattr(scheduler_module, "SessionLocal", TestingSessionLocal)


@pytest.fixture(scope="function")
def db_session(setup_test_environment):
    TestBase.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    TestBase.metadata.drop_all(bind=test_engine)

# ... API Client 和 Mock Fixtures 保持不变 ...
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    main_app.api_app.dependency_overrides[main_app.get_db] = override_get_db
    with TestClient(main_app.api_app) as c:
        yield c
    main_app.api_app.dependency_overrides.clear()

@pytest.fixture
def mock_fetch_fund_history():
    with patch('python_cli_starter.scheduler.fetch_fund_history') as mock_fetch:
        yield mock_fetch