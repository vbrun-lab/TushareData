#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据下载模块
支持A股日线和分钟线数据下载
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
from data_downloader import DataDownloader
from tqdm import tqdm


class StockDownloader(DataDownloader):
    """股票数据下载器"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
        
    def get_stock_list(self, use_config_filter: bool = True) -> pd.DataFrame:
        """获取股票列表"""
        stock_file = self.data_root / 'reference' / 'stock_basic.csv'
        if not stock_file.exists():
            self.logger.error("股票基础信息文件不存在，请先更新基础数据")
            return pd.DataFrame()
        
        stock_basic = pd.read_csv(stock_file)
        
        if not use_config_filter:
            return stock_basic[['ts_code', 'name', 'list_date', 'market', 'exchange']]
        
        # 检查update_mode，只有custom模式才使用详细筛选条件
        date_ranges = self.config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        if update_mode == 'custom':
            # custom模式：使用custom_ranges中的详细筛选条件
            stock_config = self.get_config_for_asset('stocks')
            
            if not stock_config.get('enabled', True):
                self.logger.info("股票下载已禁用")
                return pd.DataFrame()
            
            # 交易所筛选
            exchanges = stock_config.get('exchanges', [])
            if exchanges:
                stock_basic = stock_basic[stock_basic['exchange'].isin(exchanges)]
            
            # 板块筛选
            markets = stock_config.get('markets', [])
            if markets:
                stock_basic = stock_basic[stock_basic['market'].isin(markets)]
            
            # 上市状态筛选
            list_status = stock_config.get('list_status', ['L'])
            if list_status:
                # 注意：stock_basic表中可能没有list_status字段，这里假设都是上市状态
                pass
            
            # 最早上市日期筛选（之前）
            min_list_date = stock_config.get('min_list_date')
            if min_list_date:
                # 确保数据类型一致，都转为字符串进行比较
                stock_basic['list_date'] = stock_basic['list_date'].astype(str)
                stock_basic = stock_basic[stock_basic['list_date'] <= str(min_list_date)]
            
            # 退市日期筛选
            delist_date = stock_config.get('delist_date')
            if delist_date and 'delist_date' in stock_basic.columns:
                # 如果设置了退市日期，筛选在此日期之前退市或未退市的股票
                # 空值表示未退市，符合条件
                stock_basic = stock_basic[
                    stock_basic['delist_date'].isna() | 
                    (stock_basic['delist_date'] == '') |
                    (stock_basic['delist_date'].astype(str) >= str(delist_date))
                ]
            
            # 排除ST股票
            if stock_config.get('exclude_st', True):
                stock_basic = stock_basic[~stock_basic['name'].str.contains('ST', na=False)]
            
            # 排除退市股票（如果有相关字段）
            if stock_config.get('exclude_delisted', True):
                # 这里可以根据实际数据结构添加退市股票的筛选逻辑
                pass
            
            # 应用数量限制
            limits = stock_config.get('limits')
            if limits:
                stock_basic = stock_basic.head(limits)
            
            self.logger.info(f"custom模式：根据配置筛选后的股票数量: {len(stock_basic)}")
        else:
            # full和incremental模式：只应用全局数量限制，不使用详细筛选条件
            limits = date_ranges.get('limits')
            if limits:
                stock_basic = stock_basic.head(limits)
            
            self.logger.info(f"{update_mode}模式：使用全局限制，股票数量: {len(stock_basic)}")
        
        return stock_basic[['ts_code', 'name', 'list_date', 'market', 'exchange']]
    
    def download_stock_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载股票日线数据"""
        try:
            # 获取日线行情
            daily_data = self._retry_call(
                self.pro.daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if daily_data.empty:
                return pd.DataFrame()
            
            # 获取复权因子
            adj_data = self._retry_call(
                self.pro.adj_factor,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            # 合并复权因子
            if not adj_data.empty:
                daily_data = daily_data.merge(
                    adj_data[['ts_code', 'trade_date', 'adj_factor']], 
                    on=['ts_code', 'trade_date'], 
                    how='left'
                )
                daily_data['adj_factor'].fillna(1.0, inplace=True)
                
                # 计算后复权价格
                if len(daily_data) > 0:
                    # 后复权：使用最早的复权因子作为基准
                    earliest_factor = daily_data['adj_factor'].iloc[-1]
                    for col in ['open', 'high', 'low', 'close']:
                        if col in daily_data.columns:
                            daily_data[f'adj_{col}'] = (
                                daily_data[col] * daily_data['adj_factor'] / earliest_factor
                            )
            
            return daily_data
            
        except Exception as e:
            self.logger.error(f"下载股票日线数据失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def download_stock_minutes(self, ts_code: str, freq: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载股票分钟线数据"""
        try:
            # 频率映射
            freq_map = {
                'minute_1': '1min',
                'minute_5': '5min',
                'minute_15': '15min',
                'minute_30': '30min',
                'minute_60': '60min'
            }
            
            ts_freq = freq_map.get(freq, '1min')
            
            # 使用分批下载方法解决8000条限制
            minute_data = self.download_minutes_batch(
                ts_code=ts_code,
                freq=ts_freq,
                start_date=start_date,
                end_date=end_date,
                interface_func=self.pro.stk_mins,
                asset_type='stocks'
            )
            
            return minute_data
            
        except Exception as e:
            self.logger.error(f"下载股票分钟线数据失败 {ts_code} ({freq}): {e}")
            return pd.DataFrame()
    
    def download_single_stock(self, ts_code: str, frequencies: List[str] = None, save_to_temp: bool = False):
        """下载单只股票的所有频率数据"""
        stock_config = self.get_config_for_asset('stocks')
        
        if frequencies is None:
            frequencies = stock_config.get('frequencies', ['daily'])
        
        self.logger.info(f"开始下载股票数据: {ts_code}")
        
        for freq in frequencies:
            try:
                # 计算下载日期范围
                start_date, end_date = self.calculate_download_range(ts_code, 'equities', freq)
                
                if start_date >= end_date:
                    self.logger.info(f"{ts_code} {freq} 数据已是最新，跳过")
                    continue
                
                # 下载数据
                if freq == 'daily':
                    data = self.download_stock_daily(ts_code, start_date, end_date)
                else:
                    data = self.download_stock_minutes(ts_code, freq, start_date, end_date)
                
                if not data.empty:
                    # 保存数据
                    if save_to_temp:
                        # 保存到临时目录
                        temp_dir = stock_config.get('directories', './temp_stocks')
                        base_path = Path(temp_dir) / freq
                        base_path.mkdir(parents=True, exist_ok=True)
                        file_path = self.get_data_file_path(base_path, ts_code)
                    else:
                        # 保存到主数据目录
                        base_path = self.data_root / 'data' / 'equities' / freq
                        file_path = self.get_data_file_path(base_path, ts_code)
                    
                    self.save_data_to_file(data, file_path, append=None)
                    
                    # 更新元数据
                    if freq == 'daily' and 'trade_date' in data.columns:
                        latest_date = data['trade_date'].max()
                    elif 'trade_time' in data.columns:
                        latest_date = data['trade_time'].max()[:8]  # 提取日期部分
                    else:
                        latest_date = end_date
                    
                    # 更新同步信息
                    sync_info = self.get_last_sync_info('equities', freq)
                    sync_info = sync_info[sync_info['ts_code'] != ts_code]  # 移除旧记录
                    new_record = pd.DataFrame({'ts_code': [ts_code], 'last_date': [latest_date]})
                    sync_info = pd.concat([sync_info, new_record], ignore_index=True)
                    self.update_sync_info('equities', freq, sync_info)
                    
                    self.logger.info(f"{ts_code} {freq} 数据下载完成，记录数: {len(data)}")
                else:
                    self.logger.warning(f"{ts_code} {freq} 无数据")
                    
            except Exception as e:
                self.logger.error(f"下载股票数据失败 {ts_code} {freq}: {e}")
    
    def download_all_stocks(self, frequencies: List[str] = None, limit: int = None, use_config: bool = True, save_to_temp: bool = False):
        """下载所有股票数据"""
        if use_config:
            stock_list = self.get_stock_list(use_config_filter=True)
            stock_config = self.get_config_for_asset('stocks')
            
            if not stock_config.get('enabled', True):
                self.logger.info("股票下载已禁用，跳过")
                return
            
            if frequencies is None:
                frequencies = stock_config.get('frequencies', ['daily'])
            
            # 配置中的限制优先
            if limit is None:
                limit = stock_config.get('limits')
        else:
            stock_list = self.get_stock_list(use_config_filter=False)
        
        if stock_list.empty:
            self.logger.error("股票列表为空，请先更新基础数据")
            return
        
        if limit:
            stock_list = stock_list.head(limit)
        
        total_stocks = len(stock_list)
        self.logger.info(f"开始下载 {total_stocks} 只股票的数据")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=total_stocks, desc="下载股票数据", unit="只", ncols=100) as pbar:
            for idx, row in stock_list.iterrows():
                try:
                    ts_code = row['ts_code']
                    name = row['name']
                    
                    # 更新进度条描述
                    pbar.set_description(f"下载 {ts_code} {name[:10]}")
                    self.download_single_stock(ts_code, frequencies, save_to_temp)
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"处理股票失败 {row['ts_code']}: {e}")
                    pbar.update(1)  # 即使失败也更新进度
                    continue
        
        self.logger.info("所有股票数据下载完成")
    
    def download_stock_list(self, ts_codes: List[str], frequencies: List[str] = None):
        """下载指定股票列表的数据"""
        total_stocks = len(ts_codes)
        self.logger.info(f"开始下载指定的 {total_stocks} 只股票数据")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=total_stocks, desc="下载股票数据", unit="只", ncols=100) as pbar:
            for idx, ts_code in enumerate(ts_codes):
                try:
                    # 更新进度条描述
                    pbar.set_description(f"下载 {ts_code}")
                    self.download_single_stock(ts_code, frequencies)
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"处理股票失败 {ts_code}: {e}")
                    pbar.update(1)  # 即使失败也更新进度
                    continue
        
        self.logger.info("指定股票数据下载完成")


if __name__ == "__main__":
    # 测试股票下载功能
    downloader = StockDownloader()
    
    # 更新基础数据
    downloader.update_reference_data()
    
    # 下载测试股票数据
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH']
    downloader.download_stock_list(test_stocks, ['daily']) 