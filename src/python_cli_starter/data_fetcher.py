import httpx
import time
import json
import logging

logger = logging.getLogger(__name__)

http_client = httpx.Client(
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    },
    timeout=10.0
)

def fetch_fund_realtime_estimate(fund_code: str):
    """从天天基金网获取基金的实时估值。"""
    url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
    try:
        response = http_client.get(url)
        response.raise_for_status()
        json_str = response.text.replace('jsonpgz(', '').replace(');', '')
        data = json.loads(json_str)
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"获取基金 {fund_code} 实时估值失败，状态码: {e.response.status_code}, URL: {e.request.url}")
        return None
    except Exception as e:
        logger.exception(f"获取基金 {fund_code} 实时估值时发生未知错误。")
        return None

def fetch_fund_history(fund_code: str, start_date: str = None, end_date: str = None):
    """通过天天基金网的API获取基金的历史净值数据。"""
    logger.info(f"开始获取基金 {fund_code} 的历史净值数据...")
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    headers_with_referer = {'Referer': f'http://fundf10.eastmoney.com/jjjz_{fund_code}.html'}
    
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
            response = http_client.get(url, params=params, headers=headers_with_referer)
            response.raise_for_status()
            data = response.json()
            
            records = data['Data']['LSJZList']
            if not records:
                break
            all_data.extend(records)
            if data['TotalCount'] <= len(all_data):
                break
            page_index += 1
            time.sleep(0.2)
        except httpx.HTTPStatusError as e:
            logger.error(f"请求历史数据失败，状态码: {e.response.status_code}, URL: {e.request.url}")
            return []
        except Exception as e:
            logger.exception(f"请求或解析历史数据时发生未知错误: {e}")
            return []
            
    logger.info(f"成功获取基金 {fund_code} 的 {len(all_data)} 条历史记录。")
    return all_data