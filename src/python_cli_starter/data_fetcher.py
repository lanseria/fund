import requests
import time
import json

def fetch_fund_realtime_estimate(fund_code: str):
    """
    从天天基金网获取基金的实时估值。
    """
    url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        json_str = response.text.replace('jsonpgz(', '').replace(');', '')
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"获取基金 {fund_code} 实时估值失败: {e}")
        return None

def fetch_fund_history(fund_code: str, start_date: str = None, end_date: str = None):
    """
    通过天天基金网的API获取基金的历史净值数据。
    (这个函数是之前我们已经写好的，直接移到这里来)
    """
    # ... 将之前版本中 get_fund_history 的完整代码粘贴到这里 ...
    print(f"开始获取基金 {fund_code} 的历史净值数据...")
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            records = data['Data']['LSJZList']
            if not records: break
            all_data.extend(records)
            if data['TotalCount'] <= len(all_data): break
            page_index += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"请求或解析历史数据时出错: {e}")
            return []
            
    return all_data