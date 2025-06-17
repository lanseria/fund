import httpx  # 1. 导入 httpx 库
import time
import json

# 创建一个全局的 httpx.Client 实例，可以复用连接，提升性能
# 我们还为它设置了通用的请求头
http_client = httpx.Client(
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    },
    timeout=10.0 # 设置默认超时为10秒
)

def fetch_fund_realtime_estimate(fund_code: str):
    """
    从天天基金网获取基金的实时估值 (使用 httpx)。
    """
    url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
    
    try:
        # 2. 使用 httpx.Client 发送请求
        response = http_client.get(url)
        # 3. httpx 的 response 对象也有 raise_for_status() 方法
        response.raise_for_status()

        # 4. 其余逻辑完全不变
        json_str = response.text.replace('jsonpgz(', '').replace(');', '')
        data = json.loads(json_str)
        return data
    except httpx.HTTPStatusError as e:
        # 捕获更具体的 httpx 错误
        print(f"获取基金 {fund_code} 实时估值失败，状态码: {e.response.status_code}, URL: {e.request.url}")
        return None
    except Exception as e:
        # 捕获其他所有可能的错误 (如超时、网络连接问题)
        print(f"获取基金 {fund_code} 实时估值时发生未知错误: {e}")
        return None

def fetch_fund_history(fund_code: str, start_date: str = None, end_date: str = None):
    """
    通过天天基金网的API获取基金的历史净值数据 (使用 httpx)。
    """
    print(f"开始获取基金 {fund_code} 的历史净值数据...")
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    
    # 5. 为这个特定的请求添加 Referer 请求头
    headers_with_referer = {
        'Referer': f'http://fundf10.eastmoney.com/jjjz_{fund_code}.html',
    }
    
    all_data = []
    page_index = 1
    max_pages = 200
    
    while page_index <= max_pages:
        params = {
            'fundCode': fund_code, 'pageIndex': page_index, 'pageSize': 50,
            'startDate': start_date if start_date else '',
            'endDate': end_date if end_date else '',
            '_': int(time.time() * 1000)
        }
        try:
            # 6. 使用 httpx.Client 发送带参数和特定请求头的 GET 请求
            response = http_client.get(url, params=params, headers=headers_with_referer)
            response.raise_for_status()
            
            # 7. httpx 的 response 对象有 .json() 方法，可以直接解析JSON
            data = response.json()
            
            # 8. 其余逻辑完全不变
            records = data['Data']['LSJZList']
            if not records: break
            all_data.extend(records)
            if data['TotalCount'] <= len(all_data): break
            page_index += 1
            time.sleep(0.2) # 保持礼貌性等待
            
        except httpx.HTTPStatusError as e:
            print(f"请求历史数据失败，状态码: {e.response.status_code}, URL: {e.request.url}")
            return [] # 返回空列表表示失败
        except Exception as e:
            print(f"请求或解析历史数据时发生未知错误: {e}")
            return []
            
    return all_data