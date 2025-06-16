# src/python_cli_starter/models.py

from sqlalchemy import create_engine, Column, String, Date, Float, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    Base.metadata.create_all(bind=engine)