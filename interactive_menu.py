#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式菜单界面
提供用户友好的数据下载选择界面
"""

import os
import sys
from typing import Dict, List, Callable
from main import MainDownloader


class InteractiveMenu:
    """交互式菜单类"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.downloader = None
        self.menu_options = self._setup_menu_options()
    
    def _setup_menu_options(self) -> Dict[str, Dict]:
        """设置菜单选项"""
        return {
            '1': {
                'title': '更新基础数据（股票列表、基金列表、交易日历）',
                'function': self._update_reference_data,
                'description': '下载最新的股票列表、基金列表和交易日历'
            },
            '2': {
                'title': '基金日线数据下载（ETF+LOF）',
                'function': self._download_fund_daily,
                'description': '下载所有基金（ETF和LOF）的日线行情数据'
            },
            '3': {
                'title': 'A股日线数据下载',
                'function': self._download_stock_daily,
                'description': '下载A股股票的日线行情数据'
            },
            '4': {
                'title': '指数日线数据下载',
                'function': self._download_index_daily,
                'description': '下载主要指数的日线行情数据'
            },
            '5': {
                'title': '基金1分钟数据下载（ETF+LOF）',
                'function': self._download_fund_minute,
                'description': '下载所有基金（ETF和LOF）的1分钟行情数据'
            },
            '6': {
                'title': 'A股 1分钟数据下载',
                'function': self._download_stock_minute,
                'description': '下载A股股票的1分钟行情数据'
            },
            '7': {
                'title': '指数 1分钟数据下载',
                'function': self._download_index_minute,
                'description': '下载指数的1分钟行情数据'
            },
            'a': {
                'title': '自定义下载',
                'function': self._custom_download,
                'description': '自定义选择股票代码和数据频率'
            },
            'b': {
                'title': '配置驱动下载',
                'function': self._config_driven_download,
                'description': '根据config.json配置文件自动下载数据'
            },
            'c': {
                'title': '补齐缺失的分钟数据',
                'function': self._fill_missing_minutes,
                'description': '检查并补齐未下载的股票1分钟数据'
            },
            'd': {
                'title': '分钟数据健康检查',
                'function': self._minute_data_report,
                'description': '生成分钟数据健康检查报告'
            },
            '0': {
                'title': '退出程序',
                'function': self._exit_program,
                'description': '退出数据下载程序'
            }
        }
    
    def _init_downloader(self):
        """初始化下载器"""
        if self.downloader is None:
            try:
                self.downloader = MainDownloader(self.config_file)
                print("✓ 程序初始化成功")
            except Exception as e:
                print(f"✗ 程序初始化失败: {e}")
                print("请检查配置文件是否正确设置")
                return False
        return True
    
    def _clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self):
        """打印程序头部信息"""
        print("=" * 60)
        print("🚀 A股量化数据下载程序")
        print("=" * 60)
        print("基于Tushare接口的专业数据下载工具")
        print("支持股票、ETF、指数的日线和分钟线数据")
        print("-" * 60)
    
    def _print_menu(self):
        """打印菜单选项"""
        print("\n📋 请选择下载任务:")
        print("-" * 60)
        
        for key, option in self.menu_options.items():
            if key == '0':
                print()  # 退出选项前加空行
            print(f"[{key}] {option['title']}")
            print(f"    {option['description']}")
        
        print("-" * 60)
        print("💡 提示：可以输入多个选项编号进行批量执行，如 '12340' 表示依次执行选项1、2、3、4")
    
    def _get_user_choice(self) -> str:
        """获取用户选择，支持单个选项或字符序列"""
        while True:
            choice = input("\n请输入选项编号 (0-7,a,b) 或字符序列 (如12340): ").strip()
            
            # 检查是否为空
            if not choice:
                print("❌ 请输入选项编号")
                continue
            
            # 检查每个字符是否都是有效选项
            valid_choices = []
            invalid_chars = []
            
            for char in choice:
                if char in self.menu_options:
                    valid_choices.append(char)
                else:
                    invalid_chars.append(char)
            
            if invalid_chars:
                print(f"❌ 无效字符: {', '.join(invalid_chars)}，请输入有效的选项编号 (0-7,a,b)")
                continue
            
            if not valid_choices:
                print("❌ 请输入有效的选项编号")
                continue
                
            return choice
    
    def _confirm_batch_actions(self, choices: str) -> bool:
        """确认批量操作"""
        if len(choices) == 1:
            return True  # 单个操作不需要特殊确认
        
        print(f"\n📋 即将批量执行以下操作:")
        print("-" * 50)
        
        for i, choice in enumerate(choices, 1):
            option = self.menu_options[choice]
            print(f"{i}. [{choice}] {option['title']}")
        
        print("-" * 50)
        print(f"共 {len(choices)} 个操作")
        
        while True:
            confirm = input("\n确认批量执行吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是', '确认']:
                return True
            elif confirm in ['n', 'no', '否', '取消']:
                return False
            else:
                print("请输入 y/n 或 是/否")
    
    def _execute_batch_choices(self, choices: str):
        """执行批量选择"""
        total = len(choices)
        
        for i, choice in enumerate(choices, 1):
            option = self.menu_options[choice]
            
            print(f"\n{'='*60}")
            print(f"🔄 执行第 {i}/{total} 个操作: [{choice}] {option['title']}")
            print(f"{'='*60}")
            
            # 如果是退出操作，直接执行
            if choice == '0':
                option['function']()
                break  # 退出后不再执行后续操作
            
            try:
                # 对于批量执行，跳过单个操作的确认步骤
                if hasattr(self, '_batch_mode'):
                    delattr(self, '_batch_mode')
                
                # 设置批量模式标志，让子函数知道当前是批量执行
                self._batch_mode = True
                option['function']()
                
                print(f"✅ 第 {i}/{total} 个操作完成")
                
                # 批量执行时，操作间稍作停顿
                if i < total:
                    print("⏳ 准备执行下一个操作...")
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ 第 {i}/{total} 个操作失败: {e}")
                
                # 询问是否继续
                if i < total:
                    while True:
                        continue_choice = input(f"\n还有 {total-i} 个操作未执行，是否继续？(y/n): ").strip().lower()
                        if continue_choice in ['y', 'yes', '是', '继续']:
                            break
                        elif continue_choice in ['n', 'no', '否', '停止']:
                            print("🛑 批量执行已停止")
                            return
                        else:
                            print("请输入 y/n 或 是/否")
            finally:
                # 清除批量模式标志
                if hasattr(self, '_batch_mode'):
                    delattr(self, '_batch_mode')
        
        print(f"\n🎉 批量执行完成！共执行了 {total} 个操作")
        input("\n按回车键继续...")
    
    def _is_batch_mode(self) -> bool:
        """检查是否为批量模式"""
        return hasattr(self, '_batch_mode') and self._batch_mode
    
    def _confirm_action(self, action_description: str) -> bool:
        """确认操作（批量模式下自动确认）"""
        # 批量模式下自动确认，避免重复询问
        if self._is_batch_mode():
            print(f"📌 批量模式 - 自动执行: {action_description}")
            return True
        
        print(f"\n📌 即将执行: {action_description}")
        while True:
            confirm = input("确认执行吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是', '确认']:
                return True
            elif confirm in ['n', 'no', '否', '取消']:
                return False
            else:
                print("请输入 y/n 或 是/否")
    
    def _get_limit_input(self, default: int = 50) -> int:
        """获取数量限制输入"""
        # 批量模式下使用配置文件中的limits值
        if self._is_batch_mode():
            # 从配置文件获取默认limits值
            with open(self.downloader.config_file, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
            config_limits = config.get('date_ranges', {}).get('limits', 20)
            print(f"📌 批量模式 - 使用配置限制: {config_limits}")
            return config_limits
        
        while True:
            try:
                limit_str = input(f"请输入下载数量限制 (默认 {default}, 输入0表示全部): ").strip()
                if not limit_str:
                    return default
                limit = int(limit_str)
                if limit < 0:
                    print("❌ 数量不能为负数")
                    continue
                return limit if limit > 0 else None
            except ValueError:
                print("❌ 请输入有效的数字")
    
    def _update_reference_data(self):
        """更新基础数据"""
        if not self._confirm_action("更新基础数据（股票列表、基金列表、交易日历）"):
            return
        
        print("\n🔄 正在更新基础数据...")
        try:
            self.downloader.update_all_reference_data()
            print("✅ 基础数据更新完成")
        except Exception as e:
            print(f"❌ 基础数据更新失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_fund_daily(self):
        """下载基金日线数据"""
        limit = self._get_limit_input(50)
        action_desc = f"下载基金日线数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n📈 正在下载基金日线数据...")
        try:
            self.downloader.download_funds(all_funds=True, frequencies=['daily'], limit=limit)
            print("✅ 基金日线数据下载完成")
        except Exception as e:
            print(f"❌ 基金日线数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_stock_daily(self):
        """下载A股日线数据"""
        limit = self._get_limit_input(100)
        action_desc = f"下载A股日线数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n📊 正在下载A股日线数据...")
        try:
            self.downloader.download_stocks(all_stocks=True, frequencies=['daily'], limit=limit)
            print("✅ A股日线数据下载完成")
        except Exception as e:
            print(f"❌ A股日线数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_index_daily(self):
        """下载指数日线数据"""
        # 批量模式下根据update_mode决定默认行为
        if self._is_batch_mode():
            # 检查配置文件中的update_mode
            with open(self.downloader.config_file, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
            date_ranges = config.get('date_ranges', {})
            update_mode = date_ranges.get('update_mode', 'incremental')
            
            if update_mode == 'custom':
                # custom模式：检查配置中的major_only设置
                custom_ranges = date_ranges.get('custom_ranges', {})
                indices_config = custom_ranges.get('indices', {})
                major_only = indices_config.get('major_only', True)
                if major_only:
                    choice = '1'
                    print("📌 批量模式 - 自动选择主要指数")
                else:
                    choice = '2'
                    limit = indices_config.get('limits', 100)
                    print(f"📌 批量模式 - 自动选择所有指数（限制{limit}只）")
            else:
                # full/incremental模式：默认下载全部指数
                choice = '2'
                limit = date_ranges.get('limits', 100)
                print(f"📌 批量模式 - 自动选择所有指数（限制{limit}只）")
        else:
            print("\n选择下载范围:")
            print("[1] 主要指数（推荐）")
            print("[2] 所有指数")
            
            while True:
                choice = input("请选择 (1-2): ").strip()
                if choice in ['1', '2']:
                    break
                print("❌ 请输入 1 或 2")
        
        if choice == '1':
            action_desc = "下载主要指数日线数据"
            if not self._confirm_action(action_desc):
                return
            
            print(f"\n📈 正在下载主要指数日线数据...")
            try:
                self.downloader.download_indices(major_only=True, use_config=False)
                print("✅ 主要指数日线数据下载完成")
            except Exception as e:
                print(f"❌ 主要指数日线数据下载失败: {e}")
        else:
            # 如果不是批量模式，需要获取用户输入的limit
            if not self._is_batch_mode():
                limit = self._get_limit_input(100)
            
            action_desc = f"下载所有指数日线数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
            
            if not self._confirm_action(action_desc):
                return
            
            print(f"\n📈 正在下载所有指数日线数据...")
            try:
                self.downloader.download_indices(limit=limit, use_config=False)
                print("✅ 所有指数日线数据下载完成")
            except Exception as e:
                print(f"❌ 所有指数日线数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_fund_minute(self):
        """下载基金1分钟数据"""
        limit = self._get_limit_input(20)
        action_desc = f"下载基金1分钟数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n⏱️ 正在下载基金1分钟数据...")
        print("⚠️ 注意：分钟线数据量较大，下载时间较长")
        try:
            self.downloader.download_funds(all_funds=True, frequencies=['minute_1'], limit=limit)
            print("✅ 基金1分钟数据下载完成")
        except Exception as e:
            print(f"❌ 基金1分钟数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_stock_minute(self):
        """下载A股 1分钟数据"""
        limit = self._get_limit_input(20)
        action_desc = f"下载A股 1分钟数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n⏱️ 正在下载A股 1分钟数据...")
        print("⚠️ 注意：分钟线数据量较大，下载时间较长")
        try:
            self.downloader.download_stocks(all_stocks=True, frequencies=['minute_1'], limit=limit)
            print("✅ A股 1分钟数据下载完成")
        except Exception as e:
            print(f"❌ A股 1分钟数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _download_index_minute(self):
        """下载指数 1分钟数据"""
        # 批量模式下根据update_mode决定默认行为
        if self._is_batch_mode():
            # 检查配置文件中的update_mode
            with open(self.downloader.config_file, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
            date_ranges = config.get('date_ranges', {})
            update_mode = date_ranges.get('update_mode', 'incremental')
            
            if update_mode == 'custom':
                # custom模式：检查配置中的major_only设置
                custom_ranges = date_ranges.get('custom_ranges', {})
                indices_config = custom_ranges.get('indices', {})
                major_only = indices_config.get('major_only', True)
                if major_only:
                    choice = '1'
                    limit = 10
                    print("📌 批量模式 - 自动选择主要指数（限制10只）")
                else:
                    choice = '2'
                    limit = indices_config.get('limits', 20)
                    print(f"📌 批量模式 - 自动选择所有指数（限制{limit}只）")
            else:
                # full/incremental模式：默认下载全部指数
                choice = '2'
                limit = date_ranges.get('limits', 20)
                print(f"📌 批量模式 - 自动选择所有指数（限制{limit}只）")
        else:
            print("\n选择下载范围:")
            print("[1] 主要指数（推荐）")
            print("[2] 所有指数")
            
            while True:
                choice = input("请选择 (1-2): ").strip()
                if choice in ['1', '2']:
                    break
                print("❌ 请输入 1 或 2")
            
            if choice == '2':
                limit = self._get_limit_input(20)
            else:
                limit = None
        
        if choice == '1':
            action_desc = "下载主要指数 1分钟数据"
            if not self._confirm_action(action_desc):
                return
            
            print(f"\n⏱️ 正在下载主要指数 1分钟数据...")
            print("⚠️ 注意：分钟线数据量较大，下载时间较长")
            try:
                self.downloader.download_indices(major_only=True, use_config=False, frequencies=['minute_1'])
                print("✅ 主要指数 1分钟数据下载完成")
            except Exception as e:
                print(f"❌ 主要指数 1分钟数据下载失败: {e}")
        else:
            action_desc = f"下载所有指数 1分钟数据{'（全部）' if limit is None else f'（限制{limit}只）'}"
            
            if not self._confirm_action(action_desc):
                return
            
            print(f"\n⏱️ 正在下载所有指数 1分钟数据...")
            print("⚠️ 注意：分钟线数据量较大，下载时间较长")
            try:
                self.downloader.download_indices(limit=limit, use_config=False, frequencies=['minute_1'])
                print("✅ 所有指数 1分钟数据下载完成")
            except Exception as e:
                print(f"❌ 所有指数 1分钟数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _custom_download(self):
        """自定义下载"""
        # 批量模式下跳过自定义下载，因为需要交互输入
        if self._is_batch_mode():
            print("📌 批量模式 - 跳过自定义下载（需要交互输入）")
            return
        
        print("\n🔧 自定义下载设置")
        print("-" * 40)
        
        # 选择资产类型
        print("选择资产类型:")
        print("[1] 股票")
        print("[2] ETF基金")
        print("[3] 指数")
        
        while True:
            asset_choice = input("请选择资产类型 (1-3): ").strip()
            if asset_choice in ['1', '2', '3']:
                break
            print("❌ 请输入 1-3")
        
        # 选择数据频率
        print("\n选择数据频率:")
        print("[1] 日线")
        print("[2] 1分钟")
        print("[3] 5分钟")
        
        while True:
            freq_choice = input("请选择数据频率 (1-3): ").strip()
            if freq_choice in ['1', '2', '3']:
                break
            print("❌ 请输入 1-3")
        
        freq_map = {'1': 'daily', '2': 'minute_1', '3': 'minute_5'}
        frequency = freq_map[freq_choice]
        
        # 输入股票代码
        print("\n输入股票代码（多个代码用空格分隔，如: 000001.SZ 600000.SH）:")
        codes_input = input("股票代码: ").strip()
        if not codes_input:
            print("❌ 未输入股票代码")
            input("\n按回车键继续...")
            return
        
        codes = codes_input.split()
        
        # 确认下载
        asset_names = {'1': '股票', '2': 'ETF基金', '3': '指数'}
        freq_names = {'1': '日线', '2': '1分钟', '3': '5分钟'}
        action_desc = f"下载 {len(codes)} 只{asset_names[asset_choice]}的{freq_names[freq_choice]}数据"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n🎯 正在下载自定义数据...")
        try:
            if asset_choice == '1':  # 股票
                self.downloader.download_stocks(ts_codes=codes, frequencies=[frequency])
            elif asset_choice == '2':  # ETF
                self.downloader.download_funds(ts_codes=codes, frequencies=[frequency])
            else:  # 指数
                self.downloader.download_indices(ts_codes=codes, frequencies=[frequency])
            
            print("✅ 自定义数据下载完成")
        except Exception as e:
            print(f"❌ 自定义数据下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _config_driven_download(self):
        """配置驱动下载"""
        # 检查配置文件中的update_mode
        with open(self.downloader.config_file, 'r', encoding='utf-8') as f:
            import json
            config = json.load(f)
        date_ranges = config.get('date_ranges', {})
        update_mode = date_ranges.get('update_mode', 'incremental')
        
        # 批量模式下默认选择正式数据目录
        if self._is_batch_mode():
            save_to_temp = False
            print("📌 批量模式 - 自动选择保存到正式数据目录")
        else:
            print("\n选择保存位置:")
            print("[1] 正式数据目录（./data）")
            print("[2] 临时目录（配置中指定的临时目录）")
            
            while True:
                choice = input("请选择保存位置 (1-2): ").strip()
                if choice in ['1', '2']:
                    break
                print("❌ 请输入 1 或 2")
            
            save_to_temp = (choice == '2')
        
        save_location = "临时目录" if save_to_temp else "正式数据目录"
        action_desc = f"根据配置文件下载数据（保存到{save_location}）"
        
        if not self._confirm_action(action_desc):
            return
        
        print(f"\n⚙️ 正在根据配置文件下载数据...")
        print(f"💾 保存位置: {save_location}")
        print(f"🔄 更新模式: {update_mode}")
        
        if update_mode == 'custom':
            print("📋 将按照custom_ranges中的设置进行筛选和下载")
        else:
            print("📋 将根据config.json中的设置自动筛选和下载数据")
        
        try:
            self.downloader.download_by_config(save_to_temp=save_to_temp)
            print(f"\n✅ 配置驱动下载完成")
            
        except Exception as e:
            print(f"❌ 配置驱动下载失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _fill_missing_minutes(self):
        """补齐缺失的分钟数据"""
        print("\n" + "=" * 60)
        print("🔧 补齐缺失的股票1分钟数据")
        print("=" * 60)
        
        if not self._confirm_action("补齐缺失的股票1分钟数据"):
            return
        
        try:
            from main import fill_missing_minutes
            fill_missing_minutes(self.config_file)
            print("\n✅ 补齐完成")
        except Exception as e:
            print(f"\n❌ 补齐失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _minute_data_report(self):
        """生成分钟数据健康检查报告"""
        print("\n" + "=" * 60)
        print("📊 分钟数据健康检查报告")
        print("=" * 60)
        
        try:
            import subprocess
            import sys
            
            print("正在生成报告...")
            result = subprocess.run(
                [sys.executable, 'minute_data_report.py'],
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\n✅ 报告生成完成")
            else:
                print("\n⚠️  报告生成过程中出现警告")
        except FileNotFoundError:
            print("❌ 未找到 minute_data_report.py 文件")
        except Exception as e:
            print(f"\n❌ 生成报告失败: {e}")
        
        if not self._is_batch_mode():
            input("\n按回车键继续...")
    
    def _exit_program(self):
        """退出程序"""
        print("\n👋 感谢使用A股量化数据下载程序！")
        sys.exit(0)
    
    def run(self):
        """运行交互式菜单"""
        # 初始化下载器
        if not self._init_downloader():
            input("\n按回车键退出...")
            return
        
        while True:
            try:
                self._clear_screen()
                self._print_header()
                self._print_menu()
                
                choices = self._get_user_choice()
                
                # 处理单个选择或批量选择
                if len(choices) == 1:
                    # 单个操作
                    choice = choices
                    option = self.menu_options[choice]
                    print(f"\n➤ 您选择了: {option['title']}")
                    option['function']()
                else:
                    # 批量操作
                    print(f"\n➤ 您选择了批量执行: {', '.join([f'[{c}]' for c in choices])}")
                    
                    # 确认批量操作
                    if self._confirm_batch_actions(choices):
                        self._execute_batch_choices(choices)
                    else:
                        print("❌ 批量执行已取消")
                        input("\n按回车键继续...")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序被用户中断，正在退出...")
                break
            except Exception as e:
                print(f"\n❌ 程序运行出错: {e}")
                input("\n按回车键继续...")


def main():
    """主函数"""
    menu = InteractiveMenu()
    menu.run()


if __name__ == "__main__":
    main() 