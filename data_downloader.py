#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化数据下载程序
按照"目录-命名-元数据"三位一体方案设计
支持股票、指数、基金的日线和分钟线数据下载
"""

import os
import time
import pandas as pd
import tushare as ts
import json
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

CONFIG_FILE = 'config.json'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataDownloader:
    """数据下载核心类"""
    
    def __init__(self, config_file: str = 'config.json'):
        """初始化下载器"""
        self.config = self._load_config(config_file)
        self._setup_logging()
        self._setup_tushare()
        self._setup_directories()
        
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_file} 不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {config_file} 格式错误")
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger = logging.getLogger(__name__)
        
        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 添加文件处理器
        log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}_download.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_config.get('format')))
        self.logger.addHandler(file_handler)
    
    def _setup_tushare(self):
        """设置Tushare API"""
        token = self.config.get('tushare_token', '')
        url = self.config.get('tushare_url', '')
        
        if not token or token == 'YOUR_TOKEN_HERE':
            raise ValueError("请在config.json中设置正确的tushare_token")
        
        # 判断是否使用自定义URL
        if url and url.strip():
            # 使用自定义URL，通过私有属性动态修改
            ts.set_token(token)
            self.pro = ts.pro_api()
            self.pro._DataApi__token = token
            self.pro._DataApi__http_url = url
            self.logger.info(f"Tushare API初始化完成，使用自定义URL: {url}")
        else:
            # 使用默认URL，直接连接
            ts.set_token(token)
            self.pro = ts.pro_api()
            self.logger.info("Tushare API初始化完成，使用默认URL")
    
    def _setup_directories(self):
        """创建目录结构"""
        data_root = Path(self.config.get('data_root', './data'))
        
        # 创建主要目录
        directories = [
            data_root / 'reference',
            data_root / 'data' / 'equities' / 'daily',
            data_root / 'data' / 'equities' / 'minute_1',
            data_root / 'data' / 'equities' / 'minute_5',
            data_root / 'data' / 'indices' / 'daily',
            data_root / 'data' / 'indices' / 'minute_1',
            data_root / 'data' / 'indices' / 'minute_5',
            data_root / 'data' / 'funds' / 'daily',
            data_root / 'data' / 'funds' / 'minute_1',
            data_root / 'data' / 'funds' / 'minute_5',
            data_root / 'meta',
            Path('logs')
        ]
        
        # 创建临时目录（从新配置中读取）
        date_ranges = self.config.get('date_ranges', {})
        custom_ranges = date_ranges.get('custom_ranges', {})
        
        for asset_type, config in custom_ranges.items():
            temp_dir = config.get('directories')
            if temp_dir:
                directories.append(Path(temp_dir))
        
        # 创建备份目录
        if self.config.get('backup_enabled', False):
            backup_dir = self.config.get('backup_dir', './backup')
            directories.append(Path(backup_dir))
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.data_root = data_root
        self.logger.info(f"目录结构创建完成: {data_root}")
    
    def _sleep(self):
        """API调用间隔休眠"""
        time.sleep(self.config.get('sleep_secs', 0.12))
    
    def _retry_call(self, func, *args, **kwargs):
        """带重试的API调用"""
        retry_count = self.config.get('retry', 3)
        for attempt in range(retry_count):
            try:
                result = func(*args, **kwargs)
                self._sleep()
                return result
            except Exception as e:
                if attempt == retry_count - 1:
                    self.logger.error(f"API调用失败，已重试{retry_count}次: {e}")
                    raise
                else:
                    self.logger.warning(f"API调用失败，第{attempt+1}次重试: {e}")
                    time.sleep(1)
    
    def download_minutes_batch(self, ts_code: str, freq: str, start_date: str, end_date: str, 
                              interface_func, max_records: int = 8000, asset_type: str = 'stocks') -> pd.DataFrame:
        """
        分批下载分钟数据，解决单次请求8000条限制
        
        Args:
            ts_code: 股票/基金/指数代码
            freq: 频率 (1min, 5min等)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            interface_func: 接口函数 (如 self.pro.stk_mins)
            max_records: 单次最大记录数，默认8000
            asset_type: 资产类型 ('stocks', 'funds', 'indices')
        
        Returns:
            合并后的DataFrame
        """
        try:
            # 转换日期格式
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            if start_dt > end_dt:
                self.logger.warning(f"{ts_code} 开始日期 {start_date} 晚于结束日期 {end_date}，跳过")
                return pd.DataFrame()
            
            # 检查list_date，避免空下载
            list_date = self.get_asset_list_date(ts_code, asset_type)
            if list_date:
                list_dt = pd.to_datetime(list_date, format='%Y%m%d')
                if start_dt < list_dt:
                    self.logger.info(f"{ts_code} 调整开始日期：从 {start_date} 调整为 {list_date}（上市日期）")
                    start_dt = list_dt
                    start_date = list_date
                    
                    # 重新检查日期范围
                    if start_dt > end_dt:
                        self.logger.warning(f"{ts_code} 上市日期 {list_date} 晚于结束日期 {end_date}，跳过")
                        return pd.DataFrame()
            
            self.logger.info(f"开始分批下载 {ts_code} {freq} 分钟数据: {start_date} 到 {end_date}")
            
            # 计算需要分批的时间段
            # 8000条1分钟数据大约是33个交易日，为了安全起见，我们按月分批
            all_data = []
            current_start = start_dt
            batch_count = 0
            
            while current_start <= end_dt:
                batch_count += 1
                
                # 计算当前批次的结束时间（月末或总结束时间，取较小者）
                # 按月分批，每次获取一个月的数据
                if current_start.month == 12:
                    next_month_start = current_start.replace(year=current_start.year + 1, month=1, day=1)
                else:
                    next_month_start = current_start.replace(month=current_start.month + 1, day=1)
                
                # 当前批次的结束时间是下个月第一天的前一天，但不超过总结束时间
                current_end = min(next_month_start - timedelta(days=1), end_dt)
                
                # 转换为API需要的格式
                batch_start_str = f"{current_start.strftime('%Y-%m-%d')} 09:00:00"
                batch_end_str = f"{current_end.strftime('%Y-%m-%d')} 19:00:00"
                
                self.logger.debug(f"批次 {batch_count}: 获取 {ts_code} 分钟数据 {batch_start_str} 到 {batch_end_str}")
                
                try:
                    # 调用接口获取数据
                    batch_data = self._retry_call(
                        interface_func,
                        ts_code=ts_code,
                        freq=freq,
                        start_date=batch_start_str,
                        end_date=batch_end_str
                    )
                    
                    if not batch_data.empty:
                        all_data.append(batch_data)
                        self.logger.debug(f"批次 {batch_count}: 获取到 {len(batch_data)} 条记录")
                    else:
                        self.logger.debug(f"批次 {batch_count}: 无数据")
                        
                except Exception as e:
                    self.logger.warning(f"批次 {batch_count} 下载失败，跳过: {e}")
                    # 继续处理下一个批次，不因为单个批次失败而中断整个过程
                
                # 移动到下一个批次
                current_start = next_month_start
                
                # 如果已经超过结束日期，退出循环
                if current_start > end_dt:
                    break
            
            # 合并所有数据
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                
                # 去重并排序
                if 'trade_time' in combined_data.columns:
                    # 记录去重前的数量
                    original_count = len(combined_data)
                    
                    # 按ts_code和trade_time去重，保留最新的记录
                    combined_data = combined_data.drop_duplicates(
                        subset=['ts_code', 'trade_time'], keep='last'
                    )
                    
                    # 按时间降序排列（最新的在前）
                    combined_data = combined_data.sort_values(
                        ['ts_code', 'trade_time'], ascending=[True, False]
                    )
                    
                    deduplicated_count = len(combined_data)
                    if original_count != deduplicated_count:
                        self.logger.debug(f"去重: {original_count} -> {deduplicated_count} 条记录")
                
                self.logger.info(f"{ts_code} {freq} 分钟数据分批获取完成，共 {batch_count} 个批次，总记录数: {len(combined_data)}")
                return combined_data
            else:
                self.logger.warning(f"{ts_code} {freq} 分钟数据分批获取无数据")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"分批下载分钟数据失败 {ts_code} ({freq}): {e}")
            return pd.DataFrame()
    
    def update_reference_data(self):
        """更新基础数据（股票列表、基金列表、交易日历等）"""
        self.logger.info("开始更新基础数据...")
        
        reference_dir = self.data_root / 'reference'
        
        # 更新股票基础信息
        try:
            stock_basic = self._retry_call(self.pro.stock_basic, 
                                         exchange='', 
                                         list_status='L',
                                         fields='ts_code,symbol,name,area,industry,list_date,market,exchange')
            stock_basic.to_csv(reference_dir / 'stock_basic.csv', index=False, encoding='utf-8-sig')
            self.logger.info(f"股票基础信息更新完成，共{len(stock_basic)}只股票")
        except Exception as e:
            self.logger.error(f"更新股票基础信息失败: {e}")
        
        # 更新基金基础信息
        try:
            fund_basic = self._retry_call(self.pro.fund_basic, market='E')
            fund_basic.to_csv(reference_dir / 'fund_basic.csv', index=False, encoding='utf-8-sig')
            self.logger.info(f"基金基础信息更新完成，共{len(fund_basic)}只基金")
        except Exception as e:
            self.logger.error(f"更新基金基础信息失败: {e}")
        
        # 更新指数基础信息
        try:
            index_basic = self._retry_call(self.pro.index_basic, market='SSE')
            index_basic_szse = self._retry_call(self.pro.index_basic, market='SZSE')
            index_basic = pd.concat([index_basic, index_basic_szse], ignore_index=True)
            index_basic.to_csv(reference_dir / 'index_basic.csv', index=False, encoding='utf-8-sig')
            self.logger.info(f"指数基础信息更新完成，共{len(index_basic)}只指数")
        except Exception as e:
            self.logger.error(f"更新指数基础信息失败: {e}")
        
        # 更新交易日历（获取完整交易日历，不受配置时间范围限制）
        try:
            # 获取更广泛的交易日历范围，确保覆盖所有可能的数据需求
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y%m%d')
            start_date = '20050101'  # 从2005年开始，覆盖所有可能的历史数据需求
            trade_cal = self._retry_call(self.pro.trade_cal, 
                                       exchange='SSE',
                                       start_date=start_date,
                                       end_date=end_date)
            trade_cal.to_csv(reference_dir / 'trade_cal.csv', index=False, encoding='utf-8-sig')
            self.logger.info(f"交易日历更新完成，日期范围: {start_date} - {end_date}")
        except Exception as e:
            self.logger.error(f"更新交易日历失败: {e}")
    
    def get_last_sync_info(self, asset_type: str, freq: str) -> pd.DataFrame:
        """获取上次同步信息"""
        meta_file = self.data_root / 'meta' / f'last_sync_{asset_type}_{freq}.csv'
        if meta_file.exists():
            try:
                return pd.read_csv(meta_file)
            except Exception as e:
                self.logger.warning(f"读取元数据文件失败: {e}")
                return pd.DataFrame(columns=['ts_code', 'last_date'])
        else:
            return pd.DataFrame(columns=['ts_code', 'last_date'])
    
    def update_sync_info(self, asset_type: str, freq: str, sync_data: pd.DataFrame):
        """更新同步信息"""
        meta_file = self.data_root / 'meta' / f'last_sync_{asset_type}_{freq}.csv'
        sync_data.to_csv(meta_file, index=False, encoding='utf-8-sig')
    
    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日期列表"""
        trade_cal_file = self.data_root / 'reference' / 'trade_cal.csv'
        if trade_cal_file.exists():
            trade_cal = pd.read_csv(trade_cal_file)
            trade_dates = trade_cal[
                (trade_cal['cal_date'] >= start_date) & 
                (trade_cal['cal_date'] <= end_date) & 
                (trade_cal['is_open'] == 1)
            ]['cal_date'].tolist()
            return trade_dates
        else:
            self.logger.warning("交易日历文件不存在，使用默认日期范围")
            return []
    
    def get_config_for_asset(self, asset_type: str) -> Dict:
        """获取指定资产类型的配置，根据update_mode决定使用哪套配置"""
        date_ranges = self.config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        # asset_type映射：将内部使用的类型映射到配置文件中的类型
        asset_type_mapping = {
            'equities': 'stocks',
            'stocks': 'stocks',
            'funds': 'funds',
            'indices': 'indices'
        }
        config_asset_type = asset_type_mapping.get(asset_type, asset_type)
        
        if update_mode == 'custom':
            # custom模式：使用custom_ranges中的配置
            custom_ranges = date_ranges.get('custom_ranges', {})
            
            if config_asset_type in custom_ranges:
                # 合并全局配置和特定资产配置
                asset_config = custom_ranges[config_asset_type].copy()
                
                # 如果资产配置中没有指定，使用全局默认值
                if 'start_date' not in asset_config or asset_config['start_date'] == 'auto':
                    asset_config['start_date'] = date_ranges.get('default_start_date', '20100101')
                if 'end_date' not in asset_config or asset_config['end_date'] == 'auto':
                    asset_config['end_date'] = datetime.now().strftime('%Y%m%d')
                if 'limits' not in asset_config:
                    asset_config['limits'] = date_ranges.get('limits', None)
                    
                return asset_config
            else:
                # 使用默认配置
                return {
                    'enabled': True,
                    'start_date': date_ranges.get('default_start_date', '20100101'),
                    'end_date': datetime.now().strftime('%Y%m%d'),
                    'limits': date_ranges.get('limits', None),
                    'frequencies': ['daily']
                }
        else:
            # full和incremental模式：使用全局默认配置
            # 处理auto日期
            start_date = date_ranges.get('default_start_date', '20100101')
            if start_date == 'auto':
                start_date = datetime.now().strftime('%Y%m%d')
            
            end_date = date_ranges.get('default_end_date', 'auto')
            if end_date == 'auto':
                end_date = datetime.now().strftime('%Y%m%d')
            
            return {
                'enabled': True,
                'start_date': start_date,
                'end_date': end_date,
                'limits': date_ranges.get('limits', None),
                'frequencies': ['daily'],
                'lookback_days': date_ranges.get('lookback_days', 1800)
            }
    
    def calculate_download_range(self, ts_code: str, asset_type: str, freq: str) -> Tuple[str, str]:
        """计算下载日期范围"""
        date_ranges = self.config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        if update_mode == 'full':
            # 全量下载模式：使用全局默认配置，不使用custom_ranges
            start_date = date_ranges.get('default_start_date', '20100101')
            if start_date == 'auto':
                start_date = datetime.now().strftime('%Y%m%d')
            
            end_date = date_ranges.get('default_end_date', 'auto')
            if end_date == 'auto':
                end_date = datetime.now().strftime('%Y%m%d')
                
        elif update_mode == 'custom':
            # 自定义模式：强制使用custom_ranges中的配置，忽略同步信息
            asset_config = self.get_config_for_asset(asset_type)
            start_date = asset_config.get('start_date', '20100101')
            end_date = asset_config.get('end_date', datetime.now().strftime('%Y%m%d'))
            
        else:
            # 增量下载模式（默认）：基于同步记录+全局默认配置
            sync_info = self.get_last_sync_info(asset_type, freq)
            last_sync = sync_info[sync_info['ts_code'] == ts_code]
            
            if not last_sync.empty:
                # 从最后同步日期的下一天开始
                last_date = last_sync.iloc[0]['last_date']
                # 确保last_date是字符串格式，避免pd.to_datetime将整数误解为纳秒时间戳
                last_date_str = str(last_date)
                start_date = (pd.to_datetime(last_date_str) + timedelta(days=1)).strftime('%Y%m%d')
            else:
                # 首次下载：使用全局默认配置
                default_start = date_ranges.get('default_start_date', '20100101')
                if default_start == 'auto':
                    # 使用lookback_days计算
                    lookback_days = date_ranges.get('lookback_days', 1800)
                    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')
                else:
                    start_date = default_start
            
            # 结束日期使用全局默认配置
            end_date = date_ranges.get('default_end_date', 'auto')
            if end_date == 'auto':
                end_date = datetime.now().strftime('%Y%m%d')
        
        return start_date, end_date
    
    def save_data_to_file(self, data: pd.DataFrame, file_path: Path, append: bool = None):
        """保存数据到文件
        
        Args:
            data: 要保存的数据
            file_path: 保存路径
            append: 是否追加模式，如果为None则根据update_mode自动决定
        """
        if data.empty:
            return
        
        # 根据数据类型选择保存格式
        data_format = self._get_data_format_by_type(file_path)
        
        # 根据格式调整文件扩展名
        if data_format == 'parquet':
            file_path = file_path.with_suffix('.parquet')
        else:
            file_path = file_path.with_suffix('.csv')
        
        # 如果append参数为None，根据update_mode自动决定保存策略
        if append is None:
            date_ranges = self.config.get('date_ranges', {})
            update_mode = date_ranges.get('update_mode', 'incremental')
            
            if update_mode == 'incremental':
                append = True  # incremental模式：合并数据
            else:
                append = False  # custom和full模式：覆盖数据
        
        if append and file_path.exists():
            # 合并模式：读取现有数据，合并去重，降序排列
            try:
                # 根据格式读取现有数据
                if data_format == 'parquet':
                    existing_data = pd.read_parquet(file_path)
                else:
                    existing_data = pd.read_csv(file_path)
                
                # 确保数据类型一致，避免去重失败
                if 'trade_date' in existing_data.columns and 'trade_date' in data.columns:
                    # 统一转换为字符串类型
                    existing_data['trade_date'] = existing_data['trade_date'].astype(str)
                    data = data.copy()  # 避免修改原始数据
                    data['trade_date'] = data['trade_date'].astype(str)
                elif 'trade_time' in existing_data.columns and 'trade_time' in data.columns:
                    # 分钟数据的时间字段也需要统一类型
                    existing_data['trade_time'] = existing_data['trade_time'].astype(str)
                    data = data.copy()
                    data['trade_time'] = data['trade_time'].astype(str)
                
                combined_data = pd.concat([existing_data, data], ignore_index=True)
                
                # 根据数据类型选择去重字段和排序
                if 'trade_date' in combined_data.columns:
                    self.logger.debug(f"合并前数据量: 现有{len(existing_data)}, 新增{len(data)}, 合并后{len(combined_data)}")
                    
                    # 去重：基于ts_code和trade_date，保留最新的记录
                    combined_data = combined_data.drop_duplicates(
                        subset=['ts_code', 'trade_date'], keep='last'
                    )
                    self.logger.debug(f"去重后数据量: {len(combined_data)}")
                    
                    # 排序：按ts_code升序，trade_date降序排列（最新的在前）
                    combined_data = combined_data.sort_values(
                        ['ts_code', 'trade_date'], ascending=[True, False]
                    )
                    self.logger.debug(f"排序后前5条日期: {combined_data['trade_date'].head().tolist()}")
                elif 'trade_time' in combined_data.columns:
                    # 分钟数据：基于ts_code和trade_time去重
                    combined_data = combined_data.drop_duplicates(
                        subset=['ts_code', 'trade_time'], keep='last'
                    )
                    # 排序：按时间降序排列（最新的在前）
                    combined_data = combined_data.sort_values(
                        ['ts_code', 'trade_time'], ascending=[True, False]
                    )
                
                # 根据格式保存合并后的数据
                self._save_dataframe(combined_data, file_path, data_format)
                self.logger.debug(f"数据合并保存成功: {file_path}, 合并后记录数: {len(combined_data)}")
            except Exception as e:
                self.logger.error(f"合并数据失败: {e}，直接覆盖保存新数据")
                self._save_dataframe(data, file_path, data_format)
        else:
            # 覆盖模式：直接保存新数据
            # 对新数据也进行排序（降序）
            if 'trade_date' in data.columns:
                data = data.sort_values(['ts_code', 'trade_date'], ascending=[True, False])
            elif 'trade_time' in data.columns:
                data = data.sort_values(['ts_code', 'trade_time'], ascending=[True, False])
            
            self._save_dataframe(data, file_path, data_format)
            self.logger.debug(f"数据覆盖保存成功: {file_path}, 记录数: {len(data)}")
    
    def _get_data_format_by_type(self, file_path: Path) -> str:
        """根据数据类型选择保存格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            数据格式 ('csv' 或 'parquet')
        """
        path_str = str(file_path).replace('\\', '/')  # 统一使用正斜杠
        
        # 基础数据保存为CSV格式
        if '/reference/' in path_str:
            return 'csv'
        
        # 日线数据保存为CSV格式
        if '/daily/' in path_str:
            return 'csv'
        
        # 分钟数据保存为Parquet格式
        if '/minute_' in path_str:
            return 'parquet'
        
        # 默认使用CSV格式
        return 'csv'
    
    def _save_dataframe(self, data: pd.DataFrame, file_path: Path, data_format: str):
        """根据格式保存DataFrame
        
        Args:
            data: 要保存的数据
            file_path: 保存路径
            data_format: 数据格式 ('csv' 或 'parquet')
        """
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if data_format == 'parquet':
            # 保存为Parquet格式
            data.to_parquet(file_path, index=False, engine='pyarrow')
        else:
            # 保存为CSV格式（默认）
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
    
    def get_data_file_path(self, base_path: Path, ts_code: str) -> Path:
        """根据数据类型获取正确的文件路径
        
        Args:
            base_path: 基础路径（不含文件名）
            ts_code: 股票/基金/指数代码
            
        Returns:
            完整的文件路径，包含正确的扩展名
        """
        # 使用base_path来判断数据类型
        data_format = self._get_data_format_by_type(base_path)
        
        if data_format == 'parquet':
            return base_path / f"{ts_code}.parquet"
        else:
            return base_path / f"{ts_code}.csv"

    def get_asset_list_date(self, ts_code: str, asset_type: str) -> str:
        """
        获取资产的上市日期
        
        Args:
            ts_code: 资产代码
            asset_type: 资产类型 ('stocks', 'funds', 'indices')
        
        Returns:
            上市日期字符串 (YYYYMMDD格式)，如果找不到则返回None
        """
        try:
            # 根据资产类型确定参考文件
            if asset_type in ['stocks', 'equities']:
                ref_file = self.data_root / 'reference' / 'stock_basic.csv'
            elif asset_type == 'funds':
                ref_file = self.data_root / 'reference' / 'fund_basic.csv'
            elif asset_type == 'indices':
                ref_file = self.data_root / 'reference' / 'index_basic.csv'
            else:
                self.logger.warning(f"未知的资产类型: {asset_type}")
                return None
            
            if not ref_file.exists():
                self.logger.warning(f"参考文件不存在: {ref_file}")
                return None
            
            # 读取参考数据
            ref_data = pd.read_csv(ref_file)
            
            # 查找对应的ts_code
            asset_info = ref_data[ref_data['ts_code'] == ts_code]
            
            if asset_info.empty:
                self.logger.debug(f"未找到 {ts_code} 的信息")
                return None
            
            # 获取list_date
            list_date = asset_info.iloc[0]['list_date']
            
            # 处理不同的日期格式
            if pd.isna(list_date) or list_date == '':
                return None
            
            # 转换为字符串格式
            list_date_str = str(int(list_date)) if isinstance(list_date, float) else str(list_date)
            
            # 验证日期格式
            if len(list_date_str) == 8 and list_date_str.isdigit():
                return list_date_str
            else:
                self.logger.debug(f"{ts_code} list_date格式异常: {list_date_str}")
                return None
                
        except Exception as e:
            self.logger.debug(f"获取 {ts_code} list_date失败: {e}")
            return None

def main():
    config = load_config()
    ts_token = config.get('tushare_token', '')
    ts_url = config.get('tushare_url', '')
    
    if not ts_token:
        raise RuntimeError('请在config文件中配置tushare_token')
    
    # 判断是否使用自定义URL
    if ts_url and ts_url.strip():
        # 使用自定义URL，通过私有属性动态修改
        ts.set_token(ts_token)
        pro = ts.pro_api()
        pro._DataApi__token = ts_token
        pro._DataApi__http_url = ts_url
    else:
        # 使用默认URL，直接连接
        ts.set_token(ts_token)
        pro = ts.pro_api()
    
    data_root = setup_directories(config)
    frequencies = config.get('frequencies', ['daily'])
    
    # Get reference data if not exists or outdated
    stock_basic_file = os.path.join(data_root, 'reference', 'stock_basic.csv')
    if not os.path.exists(stock_basic_file):
        get_reference_data(pro, data_root)
    
    # Read stock list
    stock_basic = pd.read_csv(stock_basic_file)
    logger.info(f"Found {len(stock_basic)} stocks to process.")
    
    # Process each stock
    for idx, row in stock_basic.iterrows():
        ts_code = row['ts_code']
        name = row['name']
        logger.info(f"Processing [{idx+1}/{len(stock_basic)}] {ts_code} - {name}")
        
        for freq in frequencies:
            start_date, end_date = get_download_range(pro, ts_code, freq, data_root)
            if start_date > end_date:
                logger.info(f"  {freq}: Data up to date, skipping.")
                continue
            
            logger.info(f"  Downloading {freq} data from {start_date} to {end_date}...")
            df = download_equity_data(pro, ts_code, freq, start_date, end_date, data_root)
            if not df.empty:
                save_data(df, ts_code, freq, data_root)
                last_date = df['trade_date'].max() if 'trade_date' in df.columns else end_date
                update_metadata(data_root, ts_code, freq, last_date)
                logger.info(f"  {freq} data saved, last date: {last_date}")
            else:
                logger.warning(f"  No {freq} data downloaded for {ts_code}")
        
        time.sleep(config.get('sleep_secs', 0.12))  # Throttle requests
    
    logger.info("All downloads completed!")

if __name__ == '__main__':
    main()
