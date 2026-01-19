#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指数数据下载模块
支持主要指数的日线数据下载
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
from data_downloader import DataDownloader
from tqdm import tqdm


class IndexDownloader(DataDownloader):
    """指数数据下载器"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
    
    def get_index_list(self, market: str = 'ALL', use_config_filter: bool = False) -> pd.DataFrame:
        """获取指数列表"""
        index_file = self.data_root / 'reference' / 'index_basic.csv'
        if not index_file.exists():
            self.logger.error("指数基础信息文件不存在，请先更新基础数据")
            return pd.DataFrame()
        
        index_basic = pd.read_csv(index_file)
        
        # 根据市场过滤
        if market != 'ALL':
            index_basic = index_basic[index_basic['market'] == market]
        
        # 过滤掉已终止的指数（如果有exp_date字段）
        if 'exp_date' in index_basic.columns:
            index_basic = index_basic[
                index_basic['exp_date'].isna() | 
                (index_basic['exp_date'] == '')
            ]
        
        if not use_config_filter:
            return index_basic[['ts_code', 'name', 'market', 'publisher', 'category', 'list_date']]
        
        # 检查update_mode，只有custom模式才使用详细筛选条件
        date_ranges = self.config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        if update_mode == 'custom':
            # custom模式：使用custom_ranges中的详细筛选条件
            indices_config = self.get_config_for_asset('indices')
            
            if not indices_config.get('enabled', True):
                self.logger.info("指数下载已禁用")
                return pd.DataFrame()
            
            # 市场筛选
            markets = indices_config.get('markets', [])
            if markets:
                index_basic = index_basic[index_basic['market'].isin(markets)]
            
            # 分类筛选
            categories = indices_config.get('categories', [])
            if categories and 'category' in index_basic.columns:
                index_basic = index_basic[index_basic['category'].isin(categories)]
            
            # 最早上市日期筛选（之前）
            min_list_date = indices_config.get('min_list_date')
            if min_list_date:
                # 先过滤掉list_date为空的记录
                index_basic = index_basic[index_basic['list_date'].notna()]
                # 转换为整数进行比较
                index_basic['list_date'] = index_basic['list_date'].astype(int).astype(str)
                index_basic = index_basic[index_basic['list_date'] <= str(min_list_date)]
            
            # 到期日期筛选
            exp_date = indices_config.get('exp_date')
            if exp_date and 'exp_date' in index_basic.columns:
                # 如果设置了到期日期，筛选在此日期之前到期或未到期的指数
                # 空值表示未到期，符合条件
                index_basic = index_basic[
                    index_basic['exp_date'].isna() | 
                    (index_basic['exp_date'] == '') |
                    (index_basic['exp_date'].astype(str) >= str(exp_date))
                ]
            
            # 应用数量限制
            limits = indices_config.get('limits')
            if limits:
                index_basic = index_basic.head(limits)
            
            self.logger.info(f"custom模式：根据配置筛选后的指数数量: {len(index_basic)}")
        else:
            # full和incremental模式：只应用全局数量限制，不使用详细筛选条件
            limits = date_ranges.get('limits')
            if limits:
                index_basic = index_basic.head(limits)
            
            self.logger.info(f"{update_mode}模式：使用全局限制，指数数量: {len(index_basic)}")
        
        return index_basic[['ts_code', 'name', 'market', 'publisher', 'category', 'list_date']]
    
    def get_major_indices(self) -> List[str]:
        """获取主要指数代码列表"""
        major_indices = [
            # 上证指数
            '000001.SH',  # 上证指数
            '000002.SH',  # A股指数
            '000003.SH',  # B股指数
            '000016.SH',  # 上证50
            '000300.SH',  # 沪深300
            '000905.SH',  # 中证500
            '000852.SH',  # 中证1000
            
            # 深证指数
            '399001.SZ',  # 深证成指
            '399006.SZ',  # 创业板指
            '399106.SZ',  # 深证综指
            '399107.SZ',  # 深证A指
            '399300.SZ',  # 沪深300
            '399905.SZ',  # 中证500
            
            # 科创板
            '000688.SH',  # 科创50
            
            # 行业指数
            '399812.SZ',  # 养老产业
            '399813.SZ',  # 国防军工
            '399814.SZ',  # 传媒娱乐
            '399815.SZ',  # 互联网+
        ]
        return major_indices
    
    def download_index_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载指数日线数据"""
        try:
            # 获取指数日线行情
            daily_data = self._retry_call(
                self.pro.index_daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return daily_data
            
        except Exception as e:
            self.logger.error(f"下载指数日线数据失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def download_index_minutes(self, ts_code: str, freq: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载指数分钟线数据"""
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
                asset_type='indices'
            )
            
            return minute_data
            
        except Exception as e:
            self.logger.error(f"下载指数分钟线数据失败 {ts_code} ({freq}): {e}")
            return pd.DataFrame()
    
    def download_single_index(self, ts_code: str, frequencies: List[str] = None, save_to_temp: bool = False):
        """下载单只指数的数据"""
        if frequencies is None:
            frequencies = ['daily']
        
        # 获取指数配置
        indices_config = self.get_config_for_asset('indices')
        
        self.logger.info(f"开始下载指数数据: {ts_code}")
        
        for freq in frequencies:
            try:
                # 计算下载日期范围
                start_date, end_date = self.calculate_download_range(ts_code, 'indices', freq)
                
                if start_date >= end_date:
                    self.logger.info(f"{ts_code} {freq} 数据已是最新，跳过")
                    continue
                
                # 下载数据
                if freq == 'daily':
                    data = self.download_index_daily(ts_code, start_date, end_date)
                else:
                    data = self.download_index_minutes(ts_code, freq, start_date, end_date)
                
                if not data.empty:
                    # 保存数据
                    if save_to_temp:
                        # 保存到临时目录
                        temp_dir = indices_config.get('directories', './temp_indices')
                        base_path = Path(temp_dir) / freq
                        base_path.mkdir(parents=True, exist_ok=True)
                        file_path = self.get_data_file_path(base_path, ts_code)
                    else:
                        # 保存到主数据目录
                        base_path = self.data_root / 'data' / 'indices' / freq
                        base_path.mkdir(parents=True, exist_ok=True)
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
                    sync_info = self.get_last_sync_info('indices', freq)
                    sync_info = sync_info[sync_info['ts_code'] != ts_code]  # 移除旧记录
                    new_record = pd.DataFrame({'ts_code': [ts_code], 'last_date': [latest_date]})
                    sync_info = pd.concat([sync_info, new_record], ignore_index=True)
                    self.update_sync_info('indices', freq, sync_info)
                    
                    self.logger.info(f"{ts_code} {freq} 数据下载完成，记录数: {len(data)}")
                else:
                    self.logger.warning(f"{ts_code} {freq} 无数据")
                    
            except Exception as e:
                self.logger.error(f"下载指数数据失败 {ts_code} {freq}: {e}")
    
    def download_all_indices(self, market: str = 'ALL', limit: int = None, use_config: bool = True, save_to_temp: bool = False, frequencies: List[str] = None):
        """下载所有指数数据"""
        if use_config:
            index_list = self.get_index_list(market, use_config_filter=True)
            indices_config = self.get_config_for_asset('indices')
            
            if not indices_config.get('enabled', True):
                self.logger.info("指数下载已禁用，跳过")
                return
            
            # 配置中的限制优先
            if limit is None:
                limit = indices_config.get('limits')
            
            # 配置中的频率优先
            if frequencies is None:
                frequencies = indices_config.get('frequencies', ['daily'])
        else:
            index_list = self.get_index_list(market, use_config_filter=False)
            if frequencies is None:
                frequencies = ['daily']
        
        if limit:
            index_list = index_list.head(limit)
        
        if index_list.empty:
            self.logger.error("指数列表为空，请先更新基础数据")
            return
        
        total_indices = len(index_list)
        self.logger.info(f"开始下载 {total_indices} 只指数的数据")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=total_indices, desc="下载指数数据", unit="只", ncols=100) as pbar:
            for idx, row in index_list.iterrows():
                try:
                    ts_code = row['ts_code']
                    name = row['name']
                    
                    # 更新进度条描述
                    pbar.set_description(f"下载 {ts_code} {name[:10]}")
                    self.download_single_index(ts_code, frequencies, save_to_temp)
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"处理指数失败 {row['ts_code']}: {e}")
                    pbar.update(1)  # 即使失败也更新进度
                    continue
        
        self.logger.info("所有指数数据下载完成")
    
    def download_major_indices(self, use_config: bool = True, save_to_temp: bool = False, frequencies: List[str] = None):
        """下载主要指数数据"""
        # 如果使用配置，检查指数是否启用
        if use_config:
            indices_config = self.get_config_for_asset('indices')
            if not indices_config.get('enabled', True):
                self.logger.info("指数下载已在配置中禁用，跳过")
                return
            
            # 配置中的频率优先
            if frequencies is None:
                frequencies = indices_config.get('frequencies', ['daily'])
        else:
            if frequencies is None:
                frequencies = ['daily']
        
        major_indices = self.get_major_indices()
        total_indices = len(major_indices)
        
        self.logger.info(f"开始下载 {total_indices} 只主要指数的数据")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=total_indices, desc="下载主要指数", unit="只", ncols=100) as pbar:
            for idx, ts_code in enumerate(major_indices):
                try:
                    # 更新进度条描述
                    pbar.set_description(f"下载 {ts_code}")
                    self.download_single_index(ts_code, frequencies, save_to_temp)
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"处理主要指数失败 {ts_code}: {e}")
                    pbar.update(1)  # 即使失败也更新进度
                    continue
        
        self.logger.info("主要指数数据下载完成")
    
    def download_index_list(self, ts_codes: List[str], save_to_temp: bool = False, frequencies: List[str] = None):
        """下载指定指数列表的数据"""
        if frequencies is None:
            frequencies = ['daily']
            
        total_indices = len(ts_codes)
        self.logger.info(f"开始下载指定的 {total_indices} 只指数数据")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=total_indices, desc="下载指数数据", unit="只", ncols=100) as pbar:
            for idx, ts_code in enumerate(ts_codes):
                try:
                    # 更新进度条描述
                    pbar.set_description(f"下载 {ts_code}")
                    self.download_single_index(ts_code, frequencies, save_to_temp)
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"处理指数失败 {ts_code}: {e}")
                    pbar.update(1)  # 即使失败也更新进度
                    continue
        
        self.logger.info("指定指数数据下载完成")


if __name__ == "__main__":
    # 测试指数下载功能
    downloader = IndexDownloader()
    
    # 更新基础数据
    downloader.update_reference_data()
    
    # 下载主要指数数据
    downloader.download_major_indices() 