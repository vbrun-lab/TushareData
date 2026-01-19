#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化数据下载程序主入口
整合股票、基金、指数数据下载功能
支持命令行参数和配置文件
"""

import argparse
import sys
import json
import pandas as pd
import logging
from pathlib import Path
from typing import List
from tqdm import tqdm

from data_downloader import DataDownloader
from stock_downloader import StockDownloader
from fund_downloader import FundDownloader
from index_downloader import IndexDownloader


class MainDownloader:
    """主下载器，整合所有功能"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.stock_downloader = StockDownloader(config_file)
        self.fund_downloader = FundDownloader(config_file)
        self.index_downloader = IndexDownloader(config_file)
        self.logger = self.stock_downloader.logger
    
    def update_all_reference_data(self):
        """更新所有基础数据"""
        self.logger.info("开始更新所有基础数据...")
        self.stock_downloader.update_reference_data()
        self.logger.info("所有基础数据更新完成")
    
    def download_stocks(self, ts_codes: List[str] = None, frequencies: List[str] = None, 
                       limit: int = None, all_stocks: bool = False, use_config: bool = True, save_to_temp: bool = False):
        """下载股票数据"""
        if all_stocks:
            self.stock_downloader.download_all_stocks(frequencies, limit, use_config, save_to_temp)
        elif ts_codes:
            self.stock_downloader.download_stock_list(ts_codes, frequencies)
        else:
            self.logger.warning("未指定要下载的股票")
    
    def download_funds(self, ts_codes: List[str] = None, frequencies: List[str] = None,
                      limit: int = None, all_etfs: bool = False, all_lofs: bool = False, all_funds: bool = False, use_config: bool = True, save_to_temp: bool = False):
        """下载基金数据"""
        if all_funds:
            # 下载所有基金（ETF + LOF）
            self.fund_downloader.download_all_etfs(frequencies, limit, use_config, save_to_temp)
            self.fund_downloader.download_all_lofs(frequencies, limit, use_config, save_to_temp)
        elif all_etfs:
            self.fund_downloader.download_all_etfs(frequencies, limit, use_config, save_to_temp)
        elif all_lofs:
            self.fund_downloader.download_all_lofs(frequencies, limit, use_config, save_to_temp)
        elif ts_codes:
            self.fund_downloader.download_fund_list(ts_codes, frequencies)
        else:
            self.logger.warning("未指定要下载的基金")
    
    def download_indices(self, ts_codes: List[str] = None, major_only: bool = False,
                        market: str = 'ALL', limit: int = None, use_config: bool = True, save_to_temp: bool = False, frequencies: List[str] = None):
        """下载指数数据"""
        if major_only:
            self.index_downloader.download_major_indices(use_config=use_config, save_to_temp=save_to_temp, frequencies=frequencies)
        elif ts_codes:
            self.index_downloader.download_index_list(ts_codes, save_to_temp=save_to_temp, frequencies=frequencies)
        else:
            self.index_downloader.download_all_indices(market, limit, use_config=use_config, save_to_temp=save_to_temp, frequencies=frequencies)
    
    def download_by_config(self, save_to_temp: bool = False):
        """根据配置文件下载数据"""
        self.logger.info("开始根据配置文件下载数据...")
        
        # 读取配置
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        date_ranges = config.get('date_ranges', {})
        custom_ranges = date_ranges.get('custom_ranges', {})
        
        # 更新基础数据
        self.update_all_reference_data()
        
        # 下载股票数据
        if 'stocks' in custom_ranges and custom_ranges['stocks'].get('enabled', True):
            self.logger.info("下载股票数据...")
            self.download_stocks(all_stocks=True, use_config=True, save_to_temp=save_to_temp)
        
        # 下载基金数据
        if 'funds' in custom_ranges and custom_ranges['funds'].get('enabled', True):
            fund_config = custom_ranges['funds']
            fund_types = fund_config.get('name', ['ETF', 'LOF'])
            
            if 'ETF' in fund_types:
                self.logger.info("下载ETF数据...")
                self.download_funds(all_etfs=True, use_config=True, save_to_temp=save_to_temp)
            
            if 'LOF' in fund_types:
                self.logger.info("下载LOF数据...")
                self.download_funds(all_lofs=True, use_config=True, save_to_temp=save_to_temp)
        
        # 下载指数数据
        if 'indices' in custom_ranges and custom_ranges['indices'].get('enabled', True):
            self.logger.info("下载指数数据...")
            
            # 根据update_mode决定指数下载策略
            update_mode = date_ranges.get('update_mode', 'incremental')
            if update_mode == 'custom':
                # custom模式：使用custom_ranges中的major_only设置
                indices_config = custom_ranges['indices']
                major_only = indices_config.get('major_only', True)
                limit = indices_config.get('limits')
            else:
                # full/incremental模式：下载全部指数，不使用major_only限制
                major_only = False  # 强制下载全部指数
                limit = date_ranges.get('limits')
            
            if major_only:
                self.download_indices(major_only=True, use_config=True, save_to_temp=save_to_temp)
            else:
                # 下载全部指数，使用配置筛选
                self.download_indices(major_only=False, limit=limit, use_config=True, save_to_temp=save_to_temp)
        
        self.logger.info("配置驱动的数据下载完成")
    
    def download_all(self, frequencies: List[str] = None, limit: int = None):
        """下载所有类型的数据"""
        self.logger.info("开始下载所有类型的数据...")
        
        # 更新基础数据
        self.update_all_reference_data()
        
        # 下载全部指数
        self.logger.info("下载全部指数数据...")
        self.download_indices(major_only=False, use_config=False)
        
        # 下载ETF数据
        self.logger.info("下载ETF数据...")
        self.download_funds(all_etfs=True, frequencies=frequencies, limit=limit, use_config=False)
        
        # 下载股票数据（可以设置限制数量避免下载时间过长）
        stock_limit = limit or 100  # 默认限制100只股票
        self.logger.info(f"下载股票数据（限制{stock_limit}只）...")
        self.download_stocks(all_stocks=True, frequencies=frequencies, limit=stock_limit, use_config=False)
        
        self.logger.info("所有数据下载完成")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='A股量化数据下载程序')
    
    # 基础参数
    parser.add_argument('--config', '-c', default='config.json', 
                       help='配置文件路径 (默认: config.json)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='启动交互式菜单界面')
    parser.add_argument('--update-ref', action='store_true',
                       help='更新基础数据（股票列表、基金列表、交易日历等）')
    
    # 数据类型选择
    parser.add_argument('--stocks', action='store_true', help='下载股票数据')
    parser.add_argument('--funds', action='store_true', help='下载基金数据')
    parser.add_argument('--indices', action='store_true', help='下载指数数据')
    parser.add_argument('--all', action='store_true', help='下载所有类型数据')
    
    # 股票相关参数
    parser.add_argument('--stock-codes', nargs='+', help='指定股票代码列表')
    parser.add_argument('--all-stocks', action='store_true', help='下载所有股票')
    
    # 基金相关参数
    parser.add_argument('--fund-codes', nargs='+', help='指定基金代码列表')
    parser.add_argument('--all-etfs', action='store_true', help='下载所有ETF')
    
    # 指数相关参数
    parser.add_argument('--index-codes', nargs='+', help='指定指数代码列表')
    parser.add_argument('--major-indices', action='store_true', help='下载主要指数')
    parser.add_argument('--index-market', choices=['SSE', 'SZSE', 'ALL'], 
                       default='ALL', help='指数市场筛选')
    
    # 通用参数
    parser.add_argument('--frequencies', '-f', nargs='+', 
                       choices=['daily', 'minute_1', 'minute_5', 'minute_15', 'minute_30', 'minute_60'],
                       default=['daily'], help='数据频率')
    parser.add_argument('--limit', '-l', type=int, help='限制下载数量')
    parser.add_argument('--start-date', type=str, 
                       help='开始日期 (格式: YYYYMMDD, 如: 20190101)')
    parser.add_argument('--end-date', type=str, 
                       help='结束日期 (格式: YYYYMMDD, 如: 20251231)')
    parser.add_argument('--fill-missing-minutes', action='store_true',
                       help='补齐缺失的股票1分钟数据')
    
    return parser.parse_args()


def check_config_file(config_file: str):
    """检查配置文件"""
    if not Path(config_file).exists():
        print(f"配置文件 {config_file} 不存在，正在创建默认配置文件...")
        
        default_config = {
            "tushare_token": "YOUR_TOKEN_HERE",
            "data_root": "./data",
            "sleep_secs": 0.12,
            "retry": 3,
            "threads": 4,
            "frequencies": ["daily", "minute_1"],
            "etf_filter": {
                "min_list_date": "20100101",
                "include_delisted": False
            },
            "download_settings": {
                "lookback_days": 1800,
                "batch_size": 100,
                "max_records_per_call": 8000
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        print(f"默认配置文件已创建: {config_file}")
        print("请编辑配置文件，设置您的tushare_token，然后重新运行程序")
        return False
    
    # 检查token配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        token = config.get('tushare_token', '')
        if not token or token == 'YOUR_TOKEN_HERE':
            print("请在配置文件中设置正确的tushare_token")
            return False
            
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return False
    
    return True


def apply_date_args_to_config(config_file: str, start_date: str = None, end_date: str = None) -> str:
    """应用命令行日期参数到配置文件，返回修改后的配置文件路径"""
    if not start_date and not end_date:
        return config_file  # 没有日期参数，直接返回原配置
    
    try:
        # 读取原配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 修改日期范围
        if 'date_ranges' not in config:
            config['date_ranges'] = {}
        
        if start_date:
            config['date_ranges']['default_start_date'] = start_date
            print(f"📅 设置开始日期: {start_date}")
        
        if end_date:
            config['date_ranges']['default_end_date'] = end_date
            print(f"📅 设置结束日期: {end_date}")
        
        # 如果提供了日期参数，强制使用full模式
        if start_date or end_date:
            config['date_ranges']['update_mode'] = 'full'
            print(f"🔄 更新模式: full (全量下载)")
        
        # 创建临时配置文件
        import tempfile
        import os
        temp_fd, temp_config_file = tempfile.mkstemp(suffix='.json', prefix='config_temp_')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return temp_config_file
        except Exception as e:
            os.close(temp_fd)
            if os.path.exists(temp_config_file):
                os.unlink(temp_config_file)
            raise e
            
    except Exception as e:
        print(f"⚠️ 应用日期参数失败: {e}，使用原配置文件")
        return config_file


def fill_missing_minutes(config_file: str = 'config.json'):
    """补齐缺失的股票1分钟数据"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    try:
        # 创建下载器
        downloader = StockDownloader(config_file)
        
        # 读取股票基础信息
        stock_basic_path = Path('data/reference/stock_basic.csv')
        if not stock_basic_path.exists():
            logger.error("未找到 data/reference/stock_basic.csv，请先执行 [1] 更新基础数据")
            return
        
        stock_basic = pd.read_csv(stock_basic_path)
        total_stocks = len(stock_basic)
        logger.info(f'总股票数量: {total_stocks:,}')
        
        # 统计已下载的1分钟数据文件
        minute_1_dir = Path('data/data/equities/minute_1')
        minute_1_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files = list(minute_1_dir.glob('*.parquet'))
        downloaded_count = len(downloaded_files)
        logger.info(f'已下载1分钟数据的股票数量: {downloaded_count:,}')
        
        # 计算未下载的股票
        downloaded_codes = set()
        for file in downloaded_files:
            ts_code = file.stem
            downloaded_codes.add(ts_code)
        
        all_codes = set(stock_basic['ts_code'].tolist())
        missing_codes = all_codes - downloaded_codes
        missing_count = len(missing_codes)
        
        logger.info(f'未下载1分钟数据的股票数量: {missing_count:,}')
        if total_stocks > 0:
            completion_rate = downloaded_count / total_stocks * 100
            logger.info(f'下载完成率: {completion_rate:.1f}%')
        
        if missing_count == 0:
            logger.info('✅ 所有股票的1分钟数据都已下载完成！')
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
        logger.info(f'开始补充下载 {missing_count:,} 只股票的1分钟数据...')
        
        # 将缺失的股票代码转换为列表
        missing_list = sorted(list(missing_codes))
        
        # 分批下载，每批100只股票
        batch_size = 100
        total_batches = (len(missing_list) + batch_size - 1) // batch_size
        
        success_count = 0
        error_count = 0
        
        # 使用 tqdm 显示进度条
        with tqdm(total=len(missing_list), desc="补齐分钟数据", unit="只", ncols=100) as pbar:
            for i in range(0, len(missing_list), batch_size):
                batch_codes = missing_list[i:i+batch_size]
                batch_num = i // batch_size + 1
                
                # 更新进度条描述
                pbar.set_description(f"批次 {batch_num}/{total_batches}")
                
                try:
                    # 下载这批股票的1分钟数据
                    downloader.download_stock_list(batch_codes, ['minute_1'])
                    success_count += len(batch_codes)
                    pbar.update(len(batch_codes))
                except Exception as e:
                    logger.error(f'❌ 第 {batch_num} 批下载失败: {e}')
                    error_count += len(batch_codes)
                    pbar.update(len(batch_codes))  # 即使失败也更新进度
                    continue
        
        logger.info(f'补充下载完成！成功: {success_count:,}, 失败: {error_count:,}')
        
    except Exception as e:
        logger.error(f'补齐分钟数据失败: {e}')
        raise


def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查配置文件
    if not check_config_file(args.config):
        sys.exit(1)
    
    # 应用命令行日期参数
    actual_config_file = apply_date_args_to_config(
        args.config, 
        args.start_date, 
        args.end_date
    )
    
    # 启动交互式界面
    if args.interactive:
        from interactive_menu import InteractiveMenu
        menu = InteractiveMenu(actual_config_file)
        menu.run()
        # 清理临时配置文件
        if actual_config_file != args.config:
            import os
            try:
                os.unlink(actual_config_file)
            except:
                pass
        return
    
    try:
        # 创建主下载器
        downloader = MainDownloader(actual_config_file)
        
        # 更新基础数据
        if args.update_ref:
            downloader.update_all_reference_data()
            return
        
        # 补齐缺失的分钟数据
        if args.fill_missing_minutes:
            fill_missing_minutes(actual_config_file)
            return
        
        # 下载所有数据
        if args.all:
            downloader.download_all(args.frequencies, args.limit)
            return
        
        # 下载股票数据
        if args.stocks or args.stock_codes or args.all_stocks:
            downloader.download_stocks(
                ts_codes=args.stock_codes,
                frequencies=args.frequencies,
                limit=args.limit,
                all_stocks=args.all_stocks
            )
        
        # 下载基金数据
        if args.funds or args.fund_codes or args.all_etfs:
            downloader.download_funds(
                ts_codes=args.fund_codes,
                frequencies=args.frequencies,
                limit=args.limit,
                all_etfs=args.all_etfs
            )
        
        # 下载指数数据
        if args.indices or args.index_codes or args.major_indices:
            downloader.download_indices(
                ts_codes=args.index_codes,
                major_only=args.major_indices,
                market=args.index_market,
                limit=args.limit
            )
        
        # 如果没有指定任何下载选项，显示帮助信息
        if not any([args.stocks, args.funds, args.indices, args.all,
                   args.stock_codes, args.fund_codes, args.index_codes,
                   args.all_stocks, args.all_etfs, args.major_indices]):
            print("请指定要下载的数据类型，使用 --help 查看帮助信息")
            print("\n常用命令示例:")
            print("  python main.py --interactive                   # 启动交互式菜单（推荐）")
            print("  python main.py --update-ref                    # 更新基础数据")
            print("  python main.py --major-indices                 # 下载主要指数")
            print("  python main.py --all-etfs --limit 50           # 下载50只ETF")
            print("  python main.py --stock-codes 000001.SZ 600000.SH  # 下载指定股票")
            print("  python main.py --all --limit 10                # 下载所有类型数据（限制数量）")
            print("  python main.py --all-stocks --start-date 20190101 --end-date 20251231  # 指定日期范围下载")
            print("  python main.py --fill-missing-minutes                    # 补齐缺失的分钟数据")
            
    except Exception as e:
        print(f"程序执行失败: {e}")
        sys.exit(1)
    finally:
        # 清理临时配置文件
        if actual_config_file != args.config:
            import os
            try:
                os.unlink(actual_config_file)
            except:
                pass


if __name__ == "__main__":
    main() 