# src/python_cli_starter/models.py

from sqlalchemy import (create_engine, Column, String, Date, Float, Numeric, 
                        PrimaryKeyConstraint, MetaData, text)
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public") 

# --- 核心改动在这里 ---
# 1. 创建一个 MetaData 实例，并指定 schema
metadata_obj = MetaData(schema=DB_SCHEMA)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base(metadata=metadata_obj)

# 表1：我的持仓 (my_holdings)
class Holding(Base):
    __tablename__ = "my_holdings"

    code = Column(String, primary_key=True, index=True, comment="基金代码")
    name = Column(String, nullable=False, comment="基金名称")
    yesterday_nav = Column(Numeric(10, 4), nullable=False, comment="昨日单位净值")
    holding_amount = Column(Numeric(12, 2), nullable=False, comment="我持有的金额")
    today_estimate_nav = Column(Float, nullable=True, comment="今日估算净值")
    
    def __repr__(self):
        return f"<Holding(code='{self.code}', name='{self.name}', amount={self.holding_amount})>"

# 表2：基金历史净值 (fund_nav_history)
class NavHistory(Base):
    __tablename__ = "fund_nav_history"

    code = Column(String, index=True, comment="基金代码")
    nav_date = Column(Date, index=True, comment="净值日期")
    nav = Column(Numeric(10, 4), nullable=False, comment="单位净值")
    
    # 使用联合主键，确保同一基金同一天只有一条记录
    __table_args__ = (PrimaryKeyConstraint('code', 'nav_date', name='pk_fund_date'),)

    def __repr__(self):
        return f"<NavHistory(code='{self.code}', date='{self.nav_date}', nav={self.nav})>"

# 创建数据库表的函数 (可以在应用启动时调用一次)
def create_db_and_tables():
    # 当调用 create_all 时，SQLAlchemy 会检查 schema 是否存在
    # 如果不存在，它会尝试创建 (需要用户有相应权限)
    # 但我们推荐手动先创建好
    with engine.connect() as connection:
        # --- 核心改动在这里 ---
        # 使用 text() 函数将字符串标记为可执行的SQL
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        
        # SQLAlchemy 2.0 中，DDL 语句（如 CREATE）通常在事务之外执行
        # 或者需要显式提交。这里的 commit() 是正确的。
        connection.commit()
    
    Base.metadata.create_all(bind=engine)