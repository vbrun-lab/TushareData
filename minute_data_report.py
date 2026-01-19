#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股1分钟数据健康检查与补齐建议工具
整合了 check_status.py、analyze_minute_data.py、final_analysis.py 的功能
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

def format_date(date_str):
    """格式化日期字符串为可读格式"""
    date_str = str(date_str)
    if len(date_str) == 8:
        return f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
    return date_str

def check_basic_status():
    """基础状态检查（来自 check_status.py）"""
    print("=" * 60)
    print("📊 A股1分钟数据基础状态检查")
    print("=" * 60)
    
    try:
        # 读取股票基础信息
        stock_basic = pd.read_csv('data/reference/stock_basic.csv')
        total_stocks = len(stock_basic)
        print(f'总股票数量: {total_stocks:,}')
    except FileNotFoundError:
        print("❌ 错误: 未找到 data/reference/stock_basic.csv")
        print("   请先执行 [1] 更新基础数据")
        return None, None, None
    
    # 统计已下载的1分钟数据文件
    minute_1_dir = Path('data/data/equities/minute_1')
    minute_1_dir.mkdir(parents=True, exist_ok=True)
    downloaded_files = list(minute_1_dir.glob('*.parquet'))
    downloaded_count = len(downloaded_files)
    
    print(f'已下载1分钟数据的股票数量: {downloaded_count:,}')
    
    # 计算未下载的股票
    downloaded_codes = set()
    for file in downloaded_files:
        ts_code = file.stem
        downloaded_codes.add(ts_code)
    
    all_codes = set(stock_basic['ts_code'].tolist())
    missing_codes = all_codes - downloaded_codes
    missing_count = len(missing_codes)
    
    print(f'未下载1分钟数据的股票数量: {missing_count:,}')
    if total_stocks > 0:
        completion_rate = downloaded_count / total_stocks * 100
        print(f'下载完成率: {completion_rate:.1f}%')
    
    # 显示前20个未下载的股票
    if missing_codes:
        missing_list = sorted(list(missing_codes))[:20]
        print(f'\n前20个未下载的股票:')
        for code in missing_list:
            stock_info = stock_basic[stock_basic['ts_code'] == code]
            if not stock_info.empty:
                name = stock_info.iloc[0]['name']
                list_date = stock_info.iloc[0]['list_date']
                print(f'  {code} - {name} (上市日期: {list_date})')
    
    return stock_basic, downloaded_files, missing_codes

def analyze_time_ranges(downloaded_files, stock_basic):
    """数据时间范围分析（来自 analyze_minute_data.py）"""
    print("\n" + "=" * 60)
    print("📅 数据时间范围分析")
    print("=" * 60)
    
    if not downloaded_files:
        print("⚠️  没有已下载的数据文件")
        return None
    
    time_ranges = []
    sample_size = min(100, len(downloaded_files))
    print(f'分析样本: {sample_size} 个文件')
    
    print('\n前10个文件的详细时间范围:')
    for i, file in enumerate(downloaded_files[:sample_size]):
        try:
            df = pd.read_parquet(file)
            if not df.empty and 'trade_time' in df.columns:
                min_time = df['trade_time'].min()
                max_time = df['trade_time'].max()
                record_count = len(df)
                
                min_date = min_time[:10] if isinstance(min_time, str) else str(min_time)[:10]
                max_date = max_time[:10] if isinstance(max_time, str) else str(max_time)[:10]
                
                time_ranges.append({
                    'ts_code': file.stem,
                    'min_date': min_date,
                    'max_date': max_date,
                    'records': record_count
                })
                
                if i < 10:
                    print(f'  {file.stem}: {min_date} 到 {max_date} (共{record_count:,}条记录)')
        except Exception as e:
            print(f'  {file.stem}: 读取失败 - {e}')
    
    if not time_ranges:
        print("⚠️  无法读取任何数据文件")
        return None
    
    df_ranges = pd.DataFrame(time_ranges)
    
    print(f'\n起始日期分布（前10个）:')
    start_dates = df_ranges['min_date'].value_counts().head(10)
    for date, count in start_dates.items():
        print(f'  {date}: {count} 只股票')
    
    print(f'\n结束日期分布（前10个）:')
    end_dates = df_ranges['max_date'].value_counts().head(10)
    for date, count in end_dates.items():
        print(f'  {date}: {count} 只股票')
    
    print(f'\n记录数统计:')
    records_stats = df_ranges['records'].describe()
    print(f'  平均记录数: {records_stats["mean"]:,.0f}')
    print(f'  最少记录数: {records_stats["min"]:,.0f}')
    print(f'  最多记录数: {records_stats["max"]:,.0f}')
    print(f'  中位数记录数: {records_stats["50%"]:,.0f}')
    
    # 异常检测
    print(f'\n异常检测:')
    
    # 检查起始日期异常
    normal_start = '2019-01-02'
    abnormal_start = df_ranges[df_ranges['min_date'] != normal_start]
    if not abnormal_start.empty:
        print(f'  ⚠️  起始日期异常的股票 ({len(abnormal_start)} 只):')
        for _, row in abnormal_start.head(5).iterrows():
            print(f'    {row["ts_code"]}: {row["min_date"]} 到 {row["max_date"]} ({row["records"]:,}条)')
    else:
        print(f'  ✅ 起始日期正常（均为 {normal_start}）')
    
    # 检查记录数异常
    median_records = records_stats['50%']
    threshold = median_records * 0.5
    abnormal_records = df_ranges[df_ranges['records'] < threshold]
    if not abnormal_records.empty:
        print(f'  ⚠️  记录数异常的股票 ({len(abnormal_records)} 只，少于中位数的50%):')
        for _, row in abnormal_records.head(5).iterrows():
            print(f'    {row["ts_code"]}: {row["records"]:,}条记录')
    else:
        print(f'  ✅ 记录数正常')
    
    return df_ranges

def check_metadata():
    """元数据文件检查"""
    print("\n" + "=" * 60)
    print("📋 元数据文件检查")
    print("=" * 60)
    
    meta_file = Path('data/meta/last_sync_equities_minute_1.csv')
    
    if not meta_file.exists():
        print("⚠️  元数据文件不存在: data/meta/last_sync_equities_minute_1.csv")
        return None
    
    try:
        meta_df = pd.read_csv(meta_file)
        print(f'元数据记录数: {len(meta_df):,}')
        
        # 检查日期格式异常
        if 'last_date' in meta_df.columns:
            abnormal_dates = meta_df[meta_df['last_date'].astype(str).str.len() != 8]
            if not abnormal_dates.empty:
                print(f'⚠️  日期格式异常的记录: {len(abnormal_dates)} 条')
                print('异常日期样本:')
                for _, row in abnormal_dates.head(5).iterrows():
                    print(f'  {row["ts_code"]}: {row["last_date"]}')
            else:
                print('✅ 日期格式正常')
            
            print('\n最新日期分布（前10个）:')
            date_counts = meta_df['last_date'].value_counts().head(10)
            for date, count in date_counts.items():
                readable_date = format_date(date)
                print(f'  {readable_date}: {count:,} 只股票')
        
        return meta_df
    except Exception as e:
        print(f'❌ 读取元数据失败: {e}')
        return None

def analyze_completeness(stock_basic, meta_df):
    """数据完整性分析（来自 final_analysis.py）"""
    print("\n" + "=" * 60)
    print("🔍 数据完整性分析")
    print("=" * 60)
    
    if meta_df is None:
        print("⚠️  无法进行完整性分析（元数据文件不存在）")
        return
    
    total_stocks = len(stock_basic)
    downloaded_count = len(meta_df)
    
    print(f'总股票数量: {total_stocks:,}')
    print(f'已下载股票数量: {downloaded_count:,}')
    if total_stocks > 0:
        print(f'下载完成率: {downloaded_count/total_stocks*100:.1f}%')
    
    if 'last_date' not in meta_df.columns:
        print("⚠️  元数据缺少 last_date 字段")
        return
    
    # 分析最新日期分布
    print(f'\n最新数据日期分布:')
    date_counts = meta_df['last_date'].value_counts()
    
    if date_counts.empty:
        print("⚠️  没有日期数据")
        return
    
    for date, count in date_counts.head(10).items():
        readable_date = format_date(date)
        print(f'  {readable_date}: {count:,} 只股票')
    
    # 找出需要补齐的股票
    most_common_date = date_counts.index[0]
    most_common_count = date_counts.iloc[0]
    readable_most_common = format_date(most_common_date)
    
    print(f'\n最新日期: {readable_most_common} ({most_common_count:,} 只股票)')
    
    outdated_stocks = meta_df[meta_df['last_date'] != most_common_date]
    
    if not outdated_stocks.empty:
        print(f'\n⚠️  需要补齐数据的股票数量: {len(outdated_stocks):,}')
        
        print('\n需要补齐的股票详情（前20个）:')
        for _, row in outdated_stocks.head(20).iterrows():
            ts_code = row['ts_code']
            last_date = format_date(row['last_date'])
            
            stock_info = stock_basic[stock_basic['ts_code'] == ts_code]
            name = stock_info.iloc[0]['name'] if not stock_info.empty else '未知'
            
            print(f'  {ts_code} ({name}): 最新数据到 {last_date}')
        
        if len(outdated_stocks) > 20:
            print(f'  ... 还有 {len(outdated_stocks) - 20:,} 只股票需要补齐')
        
        # 按结束日期分组统计
        print('\n按结束日期分组的需补齐股票:')
        outdated_date_counts = outdated_stocks['last_date'].value_counts()
        for date, count in outdated_date_counts.items():
            readable_date = format_date(date)
            print(f'  {readable_date}: {count:,} 只股票')
        
        # 分析需要补齐的股票特征
        outdated_codes = outdated_stocks['ts_code'].tolist()
        outdated_stock_info = stock_basic[stock_basic['ts_code'].isin(outdated_codes)]
        
        if not outdated_stock_info.empty:
            print('\n需补齐股票的分布特征:')
            # 按交易所分组
            exchange_counts = outdated_stock_info['ts_code'].str[-2:].value_counts()
            print('  按交易所分布:')
            for exchange, count in exchange_counts.items():
                exchange_name = 'SH(上交所)' if exchange == 'SH' else 'SZ(深交所)'
                print(f'    {exchange_name}: {count:,} 只')
    else:
        print('\n✅ 所有股票的数据都是最新的！')

def generate_recommendations(missing_codes, meta_df):
    """生成补齐建议"""
    print("\n" + "=" * 60)
    print("💡 数据补齐建议")
    print("=" * 60)
    
    recommendations = []
    
    if missing_codes and len(missing_codes) > 0:
        recommendations.append(f"发现 {len(missing_codes):,} 只股票未下载1分钟数据")
        recommendations.append("建议执行: python main.py --fill-missing-minutes")
        recommendations.append("或使用交互式菜单: python start.py，选择 [c] 补齐分钟数据")
    
    if meta_df is not None and 'last_date' in meta_df.columns:
        date_counts = meta_df['last_date'].value_counts()
        if not date_counts.empty:
            most_common_date = date_counts.index[0]
            outdated_stocks = meta_df[meta_df['last_date'] != most_common_date]
            if not outdated_stocks.empty:
                recommendations.append(f"发现 {len(outdated_stocks):,} 只股票数据不是最新的")
                recommendations.append("建议执行: python start.py --incremental --6")
                recommendations.append("或使用交互式菜单: python start.py，选择 [6] A股1分钟数据下载（增量模式）")
    
    if not recommendations:
        print("✅ 数据状态良好，无需补齐")
    else:
        print("建议的补齐步骤:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🔬 A股1分钟数据健康检查报告")
    print("=" * 60)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 基础状态检查
    stock_basic, downloaded_files, missing_codes = check_basic_status()
    if stock_basic is None:
        sys.exit(1)
    
    # 2. 时间范围分析
    df_ranges = analyze_time_ranges(downloaded_files, stock_basic)
    
    # 3. 元数据检查
    meta_df = check_metadata()
    
    # 4. 完整性分析
    analyze_completeness(stock_basic, meta_df)
    
    # 5. 生成建议
    generate_recommendations(missing_codes, meta_df)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 总结")
    print("=" * 60)
    
    if downloaded_files:
        print(f"✅ 已下载股票数量: {len(downloaded_files):,}")
    if missing_codes:
        print(f"⚠️  未下载股票数量: {len(missing_codes):,}")
    if meta_df is not None:
        print(f"✅ 元数据记录数: {len(meta_df):,}")
    
    print("\n报告生成完成！")

if __name__ == "__main__":
    main()

