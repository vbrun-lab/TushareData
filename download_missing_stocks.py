#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充下载缺失的股票1分钟数据
"""

import pandas as pd
from pathlib import Path
import logging
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # 导入下载器类
    from stock_downloader import StockDownloader

    # 创建下载器
    downloader = StockDownloader('config.json')
    
    # 读取股票基础信息
    stock_basic = pd.read_csv('data/reference/stock_basic.csv')
    total_stocks = len(stock_basic)
    logger.info(f'总股票数量: {total_stocks}')
    
    # 统计已下载的1分钟数据文件
    minute_1_dir = Path('data/data/equities/minute_1')
    downloaded_files = list(minute_1_dir.glob('*.parquet'))
    downloaded_count = len(downloaded_files)
    logger.info(f'已下载1分钟数据的股票数量: {downloaded_count}')
    
    # 计算未下载的股票
    downloaded_codes = set()
    for file in downloaded_files:
        ts_code = file.stem  # 去掉.parquet扩展名
        downloaded_codes.add(ts_code)
    
    all_codes = set(stock_basic['ts_code'].tolist())
    missing_codes = all_codes - downloaded_codes
    missing_count = len(missing_codes)
    
    logger.info(f'未下载1分钟数据的股票数量: {missing_count}')
    logger.info(f'下载完成率: {downloaded_count/total_stocks*100:.1f}%')
    
    if missing_count == 0:
        logger.info('所有股票的1分钟数据都已下载完成！')
        return
    
    # 显示前20个未下载的股票
    missing_list = sorted(list(missing_codes))[:20]
    logger.info(f'前20个未下载的股票代码:')
    for code in missing_list:
        stock_info = stock_basic[stock_basic['ts_code'] == code]
        if not stock_info.empty:
            name = stock_info.iloc[0]['name']
            list_date = stock_info.iloc[0]['list_date']
            logger.info(f'  {code} - {name} (上市日期: {list_date})')
    
    # 开始补充下载
    logger.info(f'开始补充下载 {missing_count} 只股票的1分钟数据...')
    
    # 将缺失的股票代码转换为列表
    missing_list = sorted(list(missing_codes))
    
    # 分批下载，每批100只股票
    batch_size = 100
    total_batches = (len(missing_list) + batch_size - 1) // batch_size
    
    for i in range(0, len(missing_list), batch_size):
        batch_codes = missing_list[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        logger.info(f'开始下载第 {batch_num}/{total_batches} 批，共 {len(batch_codes)} 只股票')
        
        try:
            # 下载这批股票的1分钟数据
            downloader.download_stock_list(batch_codes, ['minute_1'])
            logger.info(f'第 {batch_num} 批下载完成')
        except Exception as e:
            logger.error(f'第 {batch_num} 批下载失败: {e}')
            continue
    
    logger.info('补充下载完成！')

if __name__ == "__main__":
    main()
