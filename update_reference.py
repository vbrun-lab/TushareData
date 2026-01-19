import os
import time
import pandas as pd
import tushare as ts
import json
from datetime import datetime, timedelta
import logging

CONFIG_FILE = 'config.json'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_file=CONFIG_FILE):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        raise

def get_reference_data(pro, data_root):
    """Download reference data (stock list, fund list, trading calendar)"""
    logger.info("Downloading reference data...")
    
    # Stock basic info
    stock_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    stock_basic.to_csv(os.path.join(data_root, 'reference', 'stock_basic.csv'), index=False, encoding='utf-8-sig')
    time.sleep(0.12)
    
    # Fund basic info (ETFs)
    fund_basic = pro.fund_basic(market='E')
    fund_basic.to_csv(os.path.join(data_root, 'reference', 'fund_basic.csv'), index=False, encoding='utf-8-sig')
    time.sleep(0.12)
    
    # Trading calendar
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d')  # 5 years back
    trade_cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
    trade_cal.to_csv(os.path.join(data_root, 'reference', 'trade_cal.csv'), index=False, encoding='utf-8-sig')
    time.sleep(0.12)
    
    logger.info("Reference data downloaded.")
    return stock_basic, fund_basic, trade_cal

def main():
    config = load_config()
    ts_token = config.get('tushare_token', '')
    ts_url = config.get('tushare_url', '')
    
    if not ts_token:
        raise RuntimeError('请在config文件中配置tushare_token')
    
    ts.set_token(ts_token)
    pro = ts.pro_api()
    
    # 设置自定义URL（如果配置了的话）
    if ts_url:
        pro._DataApi__token = ts_token
        pro._DataApi__http_url = ts_url
    
    data_root = config.get('data_root', './')
    get_reference_data(pro, data_root)
    logger.info("Reference data update completed!")

if __name__ == '__main__':
    main()
