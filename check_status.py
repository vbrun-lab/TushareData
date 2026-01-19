#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查股票1分钟数据下载状态
"""

import pandas as pd
from pathlib import Path

def main():
    print("检查股票1分钟数据下载状态...")
    
    # 读取股票基础信息
    stock_basic = pd.read_csv('data/reference/stock_basic.csv')
    total_stocks = len(stock_basic)
    print(f'总股票数量: {total_stocks}')
    
    # 统计已下载的1分钟数据文件
    minute_1_dir = Path('data/data/equities/minute_1')
    downloaded_files = list(minute_1_dir.glob('*.parquet'))
    downloaded_count = len(downloaded_files)
    print(f'已下载1分钟数据的股票数量: {downloaded_count}')
    
    # 计算未下载的股票
    downloaded_codes = set()
    for file in downloaded_files:
        ts_code = file.stem  # 去掉.parquet扩展名
        downloaded_codes.add(ts_code)
    
    all_codes = set(stock_basic['ts_code'].tolist())
    missing_codes = all_codes - downloaded_codes
    missing_count = len(missing_codes)
    
    print(f'未下载1分钟数据的股票数量: {missing_count}')
    print(f'下载完成率: {downloaded_count/total_stocks*100:.1f}%')
    
    # 显示前20个未下载的股票
    if missing_codes:
        missing_list = sorted(list(missing_codes))[:20]
        print(f'\n前20个未下载的股票代码:')
        for code in missing_list:
            stock_info = stock_basic[stock_basic['ts_code'] == code]
            if not stock_info.empty:
                name = stock_info.iloc[0]['name']
                list_date = stock_info.iloc[0]['list_date']
                print(f'  {code} - {name} (上市日期: {list_date})')
    
    # 检查已下载数据的时间范围
    print(f'\n检查已下载数据的时间范围（前5个文件）:')
    sample_files = downloaded_files[:5]
    for file in sample_files:
        try:
            df = pd.read_parquet(file)
            if not df.empty and 'trade_time' in df.columns:
                min_time = df['trade_time'].min()
                max_time = df['trade_time'].max()
                record_count = len(df)
                print(f'{file.stem}: {min_time} 到 {max_time} (共{record_count}条记录)')
        except Exception as e:
            print(f'{file.stem}: 读取失败 - {e}')
    
    # 检查元数据文件
    print(f'\n检查元数据文件:')
    try:
        meta_df = pd.read_csv('data/meta/last_sync_equities_minute_1.csv')
        print(f'元数据记录数: {len(meta_df)}')
        print('最新日期分布:')
        print(meta_df['last_date'].value_counts().head())
    except Exception as e:
        print(f'读取元数据失败: {e}')

if __name__ == "__main__":
    main()
