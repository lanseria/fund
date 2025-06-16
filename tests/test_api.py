import pytest
from fastapi.testclient import TestClient

# pytest会自动发现并使用 conftest.py 中定义的 fixtures
# 我们只需要在测试函数的参数中声明需要哪个 fixture 即可

def test_create_holding(client: TestClient):
    """
    测试 /holdings/ POST 接口能否成功创建一个新的持仓记录。
    
    Args:
        client (TestClient): 这是从 conftest.py 注入的API测试客户端 fixture。
    """
    # 1. 准备要发送的JSON数据
    fund_data = {
        "code": "161725",
        "name": "招商中证白酒",
        "holding_amount": 5000.00
    }

    # 2. 使用测试客户端发送POST请求
    response = client.post("/holdings/", json=fund_data)

    # 3. 断言 (Assert) - 验证结果是否符合预期
    
    # a. 验证HTTP状态码是否为 200 OK
    assert response.status_code == 200, f"请求失败，状态码：{response.status_code}，响应内容：{response.text}"

    # b. 解析返回的JSON数据
    data = response.json()
    
    # c. 验证返回的数据内容是否正确
    assert data["code"] == fund_data["code"]
    assert data["name"] == fund_data["name"]
    assert data["holding_amount"] == fund_data["holding_amount"]
    
    # d. 验证响应中是否包含数据库自动生成的字段
    assert "yesterday_nav" in data
    # 在我们的crud.create_holding中，我们硬编码了昨日净值为1.0
    assert data["yesterday_nav"] == 1.0 
    assert data["today_estimate_nav"] is None

def test_create_holding_with_existing_code(client: TestClient):
    """
    测试当尝试添加一个已存在的基金代码时，是否会失败。
    注意：当前的数据库模型将 code 设为主键，所以重复添加应该会导致数据库层面的错误，
    FastAPI会返回 500 Internal Server Error。这是一个可以改进的地方，
    理想情况下应该返回 400 Bad Request。但我们先测试当前的行为。
    """
    # 1. 先成功创建一个持仓
    client.post("/holdings/", json={"code": "005827", "name": "易方达蓝筹精选", "holding_amount": 10000})

    # 2. 再次尝试用相同的代码创建
    response = client.post("/holdings/", json={"code": "005827", "name": "不同的名称", "holding_amount": 2000})

    # 3. 断言
    # 因为主键冲突，SQLAlchemy会抛出 IntegrityError，FastAPI默认会将其转换为500错误。
    # 如果你在crud层做了判断，可以期望返回400。
    # 我们先假设会返回500
    assert response.status_code == 500, "预期因主键冲突返回500错误，但实际返回了其他状态码"
    # 理想的错误处理应该返回类似 {"detail": "Fund with code 005827 already exists."}