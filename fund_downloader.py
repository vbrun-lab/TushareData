#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据下载模块
支持ETF等场内基金的日线和分钟线数据下载
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
from data_downloader import DataDownloader


class FundDownloader(DataDownloader):
    """基金数据下载器"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
    
    def get_fund_list(self, fund_type: str = 'ETF', use_config_filter: bool = True) -> pd.DataFrame:
        """获取基金列表"""
        fund_file = self.data_root / 'reference' / 'fund_basic.csv'
        if not fund_file.exists():
            self.logger.error("基金基础信息文件不存在，请先更新基础数据")
            return pd.DataFrame()
        
        fund_basic = pd.read_csv(fund_file)
        
        # 根据基金类型过滤
        if fund_type == 'ETF':
            filtered_funds = fund_basic[
                fund_basic['name'].str.contains('ETF', case=False, na=False)
            ].copy()
        elif fund_type == 'LOF':
            filtered_funds = fund_basic[
                fund_basic['name'].str.contains('LOF', case=False, na=False)
            ].copy()
        else:
            filtered_funds = fund_basic.copy()
        
        if not use_config_filter:
            return filtered_funds[['ts_code', 'name', 'list_date', 'fund_type', 'management']]
        
        # 检查update_mode，只有custom模式才使用详细筛选条件
        date_ranges = self.config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        if update_mode == 'custom':
            # custom模式：使用custom_ranges中的详细筛选条件
            fund_config = self.get_config_for_asset('funds')
            
            if not fund_config.get('enabled', True):
                self.logger.info("基金下载已禁用")
                return pd.DataFrame()
            
            # 基金类型筛选
            fund_types = fund_config.get('name', [])
            if fund_types and fund_type not in fund_types:
                self.logger.info(f"基金类型 {fund_type} 未在配置中启用")
                return pd.DataFrame()
            
            # 交易所筛选
            exchanges = fund_config.get('exchanges', [])
            if exchanges:
                exchange_filter = False
                for exchange in exchanges:
                    if exchange == 'SSE':
                        exchange_filter |= filtered_funds['ts_code'].str.startswith('5')
                    elif exchange == 'SZSE':
                        exchange_filter |= filtered_funds['ts_code'].str.startswith('1')
                if exchange_filter is not False:
                    filtered_funds = filtered_funds[exchange_filter]
            
            # 排除退市基金
            if fund_config.get('exclude_delisted', True):
                filtered_funds = filtered_funds[
                    filtered_funds['delist_date'].isna() | 
                    (filtered_funds['delist_date'] == '')
                ]
            
            # 最早上市日期筛选（之前）
            min_list_date = fund_config.get('min_list_date', '20100101')
            filtered_funds['list_date'] = pd.to_datetime(filtered_funds['list_date'].astype(str), format='%Y%m%d', errors='coerce')
            min_date = pd.to_datetime(min_list_date)
            filtered_funds = filtered_funds[filtered_funds['list_date'] <= min_date]
            
            # 退市日期筛选
            delist_date = fund_config.get('delist_date')
            if delist_date and 'delist_date' in filtered_funds.columns:
                # 如果设置了退市日期，筛选在此日期之前退市或未退市的基金
                # 空值表示未退市，符合条件
                filtered_funds = filtered_funds[
                    filtered_funds['delist_date'].isna() | 
                    (filtered_funds['delist_date'] == '') |
                    (filtered_funds['delist_date'].astype(str) >= str(delist_date))
                ]
            
            # 基金管理公司筛选
            managements = fund_config.get('management', [])
            if managements:
                filtered_funds = filtered_funds[filtered_funds['management'].isin(managements)]
            
            # 基金分类筛选
            categories = fund_config.get('categories', [])
            if categories and 'fund_type' in filtered_funds.columns:
                filtered_funds = filtered_funds[filtered_funds['fund_type'].isin(categories)]
            
            # 应用数量限制
            limits = fund_config.get('limits')
            if limits:
                filtered_funds = filtered_funds.head(limits)
            
            self.logger.info(f"custom模式：根据配置筛选后的{fund_type}基金数量: {len(filtered_funds)}")
        else:
            # full和incremental模式：只应用全局数量限制，不使用详细筛选条件
            limits = date_ranges.get('limits')
            if limits:
                filtered_funds = filtered_funds.head(limits)
            
            self.logger.info(f"{update_mode}模式：使用全局限制，{fund_type}基金数量: {len(filtered_funds)}")
        
        return filtered_funds[['ts_code', 'name', 'list_date', 'fund_type', 'management']]
    
    def download_fund_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载基金日线数据"""
        try:
            # 获取基金日线行情
            daily_data = self._retry_call(
                self.pro.fund_daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if daily_data.empty:
                return pd.DataFrame()
            
            # 获取基金复权因子
            adj_data = self._retry_call(
                self.pro.fund_adj,
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
            self.logger.error(f"下载基金日线数据失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def download_fund_minutes(self, ts_code: str, freq: str, start_date: str, end_date: str) -> pd.DataFrame:
        """下载基金分钟线数据（ETF使用stk_mins接口）"""
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
                asset_type='funds'
            )
            
            return minute_data
            
        except Exception as e:
            self.logger.error(f"下载基金分钟线数据失败 {ts_code} ({freq}): {e}")
            return pd.DataFrame()
    
    def download_single_fund(self, ts_code: str, frequencies: List[str] = None, save_to_temp: bool = False):
        """下载单只基金的所有频率数据"""
        fund_config = self.get_config_for_asset('funds')
        
        if frequencies is None:
            frequencies = fund_config.get('frequencies', ['daily'])
        
        self.logger.info(f"开始下载基金数据: {ts_code}")
        
        for freq in frequencies:
            try:
                # 计算下载日期范围
                start_date, end_date = self.calculate_download_range(ts_code, 'funds', freq)
                
                if start_date >= end_date:
                    self.logger.info(f"{ts_code} {freq} 数据已是最新，跳过")
                    continue
                
                # 下载数据
                if freq == 'daily':
                    data = self.download_fund_daily(ts_code, start_date, end_date)
                else:
                    data = self.download_fund_minutes(ts_code, freq, start_date, end_date)
                
                if not data.empty:
                    # 保存数据
                    if save_to_temp:
                        # 保存到临时目录
                        temp_dir = fund_config.get('directories', './temp_funds')
                        base_path = Path(temp_dir) / freq
                        base_path.mkdir(parents=True, exist_ok=True)
                        file_path = self.get_data_file_path(base_path, ts_code)
                    else:
                        # 保存到主数据目录
                        base_path = self.data_root / 'data' / 'funds' / freq
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
                    sync_info = self.get_last_sync_info('funds', freq)
                    sync_info = sync_info[sync_info['ts_code'] != ts_code]  # 移除旧记录
                    new_record = pd.DataFrame({'ts_code': [ts_code], 'last_date': [latest_date]})
                    sync_info = pd.concat([sync_info, new_record], ignore_index=True)
                    self.update_sync_info('funds', freq, sync_info)
                    
                    self.logger.info(f"{ts_code} {freq} 数据下载完成，记录数: {len(data)}")
                else:
                    self.logger.warning(f"{ts_code} {freq} 无数据")
                    
            except Exception as e:
                self.logger.error(f"下载基金数据失败 {ts_code} {freq}: {e}")
    
    def download_all_etfs(self, frequencies: List[str] = None, limit: int = None, use_config: bool = True, save_to_temp: bool = False):
        """下载所有ETF数据"""
        if use_config:
            etf_list = self.get_fund_list('ETF', use_config_filter=True)
            fund_config = self.get_config_for_asset('funds')
            
            if not fund_config.get('enabled', True):
                self.logger.info("基金下载已禁用，跳过")
                return
            
            if 'ETF' not in fund_config.get('name', ['ETF', 'LOF']):
                self.logger.info("ETF下载未在配置中启用，跳过")
                return
            
            if frequencies is None:
                frequencies = fund_config.get('frequencies', ['daily'])
            
            # 配置中的限制优先
            if limit is None:
                limit = fund_config.get('limits')
        else:
            etf_list = self.get_fund_list('ETF', use_config_filter=False)
        
        if etf_list.empty:
            self.logger.error("ETF列表为空，请先更新基础数据")
            return
        
        if limit:
            etf_list = etf_list.head(limit)
        
        total_etfs = len(etf_list)
        self.logger.info(f"开始下载 {total_etfs} 只ETF的数据")
        
        for idx, row in etf_list.iterrows():
            try:
                ts_code = row['ts_code']
                name = row['name']
                
                self.logger.info(f"[{idx+1}/{total_etfs}] 处理ETF: {ts_code} {name}")
                self.download_single_fund(ts_code, frequencies, save_to_temp)
                
            except Exception as e:
                self.logger.error(f"处理ETF失败 {row['ts_code']}: {e}")
                continue
        
        self.logger.info("所有ETF数据下载完成")
    
    def download_all_lofs(self, frequencies: List[str] = None, limit: int = None, use_config: bool = True, save_to_temp: bool = False):
        """下载所有LOF数据"""
        if use_config:
            lof_list = self.get_fund_list('LOF', use_config_filter=True)
            fund_config = self.get_config_for_asset('funds')
            
            if not fund_config.get('enabled', True):
                self.logger.info("基金下载已禁用，跳过")
                return
            
            if 'LOF' not in fund_config.get('name', ['ETF', 'LOF']):
                self.logger.info("LOF下载未在配置中启用，跳过")
                return
            
            if frequencies is None:
                frequencies = fund_config.get('frequencies', ['daily'])
            
            # 配置中的限制优先
            if limit is None:
                limit = fund_config.get('limits')
        else:
            lof_list = self.get_fund_list('LOF', use_config_filter=False)
        
        if lof_list.empty:
            self.logger.error("LOF列表为空，请先更新基础数据")
            return
        
        if limit:
            lof_list = lof_list.head(limit)
        
        total_lofs = len(lof_list)
        self.logger.info(f"开始下载 {total_lofs} 只LOF的数据")
        
        for idx, row in lof_list.iterrows():
            try:
                ts_code = row['ts_code']
                name = row['name']
                
                self.logger.info(f"[{idx+1}/{total_lofs}] 处理LOF: {ts_code} {name}")
                self.download_single_fund(ts_code, frequencies, save_to_temp)
                
            except Exception as e:
                self.logger.error(f"处理LOF失败 {row['ts_code']}: {e}")
                continue
        
        self.logger.info("所有LOF数据下载完成")
    
    def download_fund_list(self, ts_codes: List[str], frequencies: List[str] = None):
        """下载指定基金列表的数据"""
        total_funds = len(ts_codes)
        self.logger.info(f"开始下载指定的 {total_funds} 只基金数据")
        
        for idx, ts_code in enumerate(ts_codes):
            try:
                self.logger.info(f"[{idx+1}/{total_funds}] 处理基金: {ts_code}")
                self.download_single_fund(ts_code, frequencies)
                
            except Exception as e:
                self.logger.error(f"处理基金失败 {ts_code}: {e}")
                continue
        
        self.logger.info("指定基金数据下载完成")


if __name__ == "__main__":
    # 测试基金下载功能
    downloader = FundDownloader()
    
    # 更新基础数据
    downloader.update_reference_data()
    
    # 下载测试ETF数据
    test_etfs = ['510300.SH', '159915.SZ', '512100.SH']
    downloader.download_fund_list(test_etfs, ['daily']) 