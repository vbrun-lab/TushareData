#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析A股1分钟线数据范围
"""

import pandas as pd
from pathlib import Path
import numpy as np
from datetime import datetime

def main():
    print('=== A股1分钟线数据范围分析 ===')

    # 读取股票基础信息
    stock_basic = pd.read_csv('data/reference/stock_basic.csv')
    total_stocks = len(stock_basic)
    print(f'总股票数量: {total_stocks}')

    # 统计已下载的1分钟数据文件
    minute_1_dir = Path('data/data/equities/minute_1')
    downloaded_files = list(minute_1_dir.glob('*.parquet'))
    downloaded_count = len(downloaded_files)
    print(f'已下载1分钟数据的股票数量: {downloaded_count}')
    print(f'下载完成率: {downloaded_count/total_stocks*100:.1f}%')

    # 分析数据时间范围
    print(f'\n=== 数据时间范围分析 ===')
    time_ranges = []
    sample_size = min(100, len(downloaded_files))  # 分析前100个文件
    print(f'分析样本: {sample_size} 个文件')

    for i, file in enumerate(downloaded_files[:sample_size]):
        try:
            df = pd.read_parquet(file)
            if not df.empty and 'trade_time' in df.columns:
                min_time = df['trade_time'].min()
                max_time = df['trade_time'].max()
                record_count = len(df)
                
                # 提取日期部分
                min_date = min_time[:10] if isinstance(min_time, str) else str(min_time)[:10]
                max_date = max_time[:10] if isinstance(max_time, str) else str(max_time)[:10]
                
                time_ranges.append({
                    'ts_code': file.stem,
                    'min_date': min_date,
                    'max_date': max_date,
                    'records': record_count,
                    'min_time': min_time,
                    'max_time': max_time
                })
                
                if i < 10:  # 显示前10个详细信息
                    print(f'{file.stem}: {min_date} 到 {max_date} (共{record_count:,}条记录)')
        except Exception as e:
            print(f'{file.stem}: 读取失败 - {e}')

    if time_ranges:
        # 统计时间范围分布
        df_ranges = pd.DataFrame(time_ranges)
        
        print(f'\n=== 起始日期分布 ===')
        start_dates = df_ranges['min_date'].value_counts().head(10)
        for date, count in start_dates.items():
            print(f'{date}: {count} 只股票')
        
        print(f'\n=== 结束日期分布 ===')
        end_dates = df_ranges['max_date'].value_counts().head(10)
        for date, count in end_dates.items():
            print(f'{date}: {count} 只股票')
        
        print(f'\n=== 记录数统计 ===')
        records_stats = df_ranges['records'].describe()
        print(f'平均记录数: {records_stats["mean"]:,.0f}')
        print(f'最少记录数: {records_stats["min"]:,.0f}')
        print(f'最多记录数: {records_stats["max"]:,.0f}')
        print(f'中位数记录数: {records_stats["50%"]:,.0f}')
        
        # 找出数据范围异常的股票
        print(f'\n=== 数据范围异常检查 ===')
        
        # 检查起始日期异常（不是2019-01-02的）
        normal_start = '2019-01-02'
        abnormal_start = df_ranges[df_ranges['min_date'] != normal_start]
        if not abnormal_start.empty:
            print(f'起始日期异常的股票 ({len(abnormal_start)} 只):')
            for _, row in abnormal_start.head(10).iterrows():
                print(f'  {row["ts_code"]}: {row["min_date"]} 到 {row["max_date"]} ({row["records"]:,}条)')
        
        # 检查结束日期异常（太早结束的）
        recent_dates = ['2025-08-29', '2025-08-30', '2025-07-08', '2025-07-07', '2025-07-04']
        abnormal_end = df_ranges[~df_ranges['max_date'].isin(recent_dates)]
        if not abnormal_end.empty:
            print(f'\n结束日期异常的股票 ({len(abnormal_end)} 只):')
            for _, row in abnormal_end.head(10).iterrows():
                print(f'  {row["ts_code"]}: {row["min_date"]} 到 {row["max_date"]} ({row["records"]:,}条)')
        
        # 检查记录数异常（明显偏少的）
        median_records = records_stats['50%']
        threshold = median_records * 0.5  # 少于中位数一半的认为异常
        abnormal_records = df_ranges[df_ranges['records'] < threshold]
        if not abnormal_records.empty:
            print(f'\n记录数异常的股票 ({len(abnormal_records)} 只):')
            for _, row in abnormal_records.head(10).iterrows():
                print(f'  {row["ts_code"]}: {row["min_date"]} 到 {row["max_date"]} ({row["records"]:,}条)')

    print(f'\n=== 元数据文件检查 ===')
    try:
        meta_df = pd.read_csv('data/meta/last_sync_equities_minute_1.csv')
        print(f'元数据记录数: {len(meta_df)}')
        
        # 检查日期格式异常
        abnormal_dates = meta_df[meta_df['last_date'].str.len() != 8]
        if not abnormal_dates.empty:
            print(f'日期格式异常的记录: {len(abnormal_dates)} 条')
            print('异常日期样本:')
            for _, row in abnormal_dates.head(5).iterrows():
                print(f'  {row["ts_code"]}: {row["last_date"]}')
        
        print('\n最新日期分布:')
        date_counts = meta_df['last_date'].value_counts().head(10)
        for date, count in date_counts.items():
            print(f'  {date}: {count} 只股票')
            
    except Exception as e:
        print(f'读取元数据失败: {e}')

    # 检查未下载的股票
    print(f'\n=== 未下载股票分析 ===')
    downloaded_codes = set()
    for file in downloaded_files:
        ts_code = file.stem
        downloaded_codes.add(ts_code)
    
    all_codes = set(stock_basic['ts_code'].tolist())
    missing_codes = all_codes - downloaded_codes
    missing_count = len(missing_codes)
    
    print(f'未下载股票数量: {missing_count}')
    if missing_codes:
        missing_list = sorted(list(missing_codes))[:20]
        print(f'前20个未下载的股票:')
        for code in missing_list:
            stock_info = stock_basic[stock_basic['ts_code'] == code]
            if not stock_info.empty:
                name = stock_info.iloc[0]['name']
                list_date = stock_info.iloc[0]['list_date']
                print(f'  {code} - {name} (上市日期: {list_date})')

if __name__ == "__main__":
    main()
