#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化数据下载程序 - 快速启动脚本
支持交互式菜单界面和命令行参数
"""

import argparse
import json
import sys
import tempfile
import os
from pathlib import Path

from interactive_menu import InteractiveMenu


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='A股量化数据下载程序 - 快速启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python start.py                          # 启动交互式菜单
  python start.py --incremental            # 设置增量模式并启动交互菜单
  python start.py --123450                 # 自动执行菜单选项1,2,3,4,5,0
  python start.py --incremental --123450   # 设置增量模式并自动执行菜单选项
  python start.py --config my_config.json --12a0  # 使用自定义配置并执行选项

菜单选项说明:
  1: 更新基础数据    2: ETF日线数据      3: LOF日线数据
  4: A股日线数据     5: 指数日线数据     6: ETF 1分钟数据
  7: LOF 1分钟数据   8: A股 1分钟数据    9: 自定义下载
  a: 配置驱动下载    0: 退出程序
        """
    )
    
    # 基础参数
    parser.add_argument('--config', '-c', default='config.json',
                       help='配置文件路径 (默认: config.json)')
    
    # 模式设置
    parser.add_argument('--incremental', action='store_true',
                       help='设置为增量下载模式')
    parser.add_argument('--full', action='store_true',
                       help='设置为完整下载模式')
    parser.add_argument('--custom', action='store_true',
                       help='设置为自定义下载模式')
    
    # 自动执行参数（支持多种格式）
    parser.add_argument('--auto', '--sequence', '--seq',
                       help='自动执行菜单序列，如 123450 或 12a0')
    
    # 为了支持 --123450 这样的格式，我们需要特殊处理
    # 检查是否有以 -- 开头的数字序列参数
    for i, arg in enumerate(sys.argv):
        if arg.startswith('--') and len(arg) > 2:
            # 检查是否是纯数字+字母的序列（排除已知参数）
            potential_seq = arg[2:]  # 去掉 --
            if (potential_seq and 
                all(c.isdigit() or c.lower() in 'abcdefghijklmnopqrstuvwxyz' for c in potential_seq) and
                arg not in ['--config', '--incremental', '--full', '--custom', '--auto', '--sequence', '--seq', '--help']):
                # 这是一个序列参数，添加到参数列表
                parser.add_argument(arg, action='store_const', const=potential_seq,
                                   help=f'自动执行菜单序列: {potential_seq}')
    
    return parser.parse_args()


def modify_config_mode(config_file: str, mode: str) -> str:
    """修改配置文件的update_mode，返回修改后的配置文件路径"""
    try:
        # 读取原配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 修改update_mode
        if 'date_ranges' not in config:
            config['date_ranges'] = {}
        
        original_mode = config['date_ranges'].get('update_mode', 'incremental')
        config['date_ranges']['update_mode'] = mode
        
        print(f"📝 配置模式: {original_mode} → {mode}")
        
        # 如果是临时修改，创建临时配置文件
        if original_mode != mode:
            # 创建临时配置文件
            temp_fd, temp_config_file = tempfile.mkstemp(suffix='.json', prefix='config_temp_')
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"📄 临时配置文件: {temp_config_file}")
                return temp_config_file
            except Exception as e:
                os.close(temp_fd)
                os.unlink(temp_config_file)
                raise e
        else:
            print(f"📄 使用原配置文件: {config_file}")
            return config_file
            
    except Exception as e:
        print(f"❌ 修改配置文件失败: {e}")
        return config_file


def extract_sequence_from_args(args) -> str:
    """从参数中提取序列字符串"""
    # 首先检查 --auto 参数
    if hasattr(args, 'auto') and args.auto:
        return args.auto
    
    # 然后检查动态添加的序列参数
    for attr_name in dir(args):
        if not attr_name.startswith('_'):
            attr_value = getattr(args, attr_name)
            # 如果属性值是字符串且看起来像序列
            if (isinstance(attr_value, str) and 
                attr_value and 
                all(c.isdigit() or c.lower() in 'abcdefghijklmnopqrstuvwxyz' for c in attr_value) and
                attr_name not in ['config', 'auto', 'sequence', 'seq']):
                return attr_value
    
    return None


class AutoExecuteMenu(InteractiveMenu):
    """支持自动执行的菜单类"""
    
    def __init__(self, config_file: str = 'config.json', auto_sequence: str = None):
        super().__init__(config_file)
        self.auto_sequence = auto_sequence
        self.auto_mode = bool(auto_sequence)
    
    def run(self):
        """运行菜单，支持自动执行"""
        # 初始化下载器
        if not self._init_downloader():
            print("❌ 程序初始化失败")
            return
        
        if self.auto_mode and self.auto_sequence:
            self._auto_execute_sequence(self.auto_sequence)
        else:
            # 正常的交互式菜单
            super().run()
    
    def _auto_execute_sequence(self, sequence: str):
        """自动执行菜单序列"""
        print(f"🤖 自动执行模式")
        print(f"📋 执行序列: {sequence}")
        print("=" * 60)
        
        # 验证序列中的所有字符都是有效选项
        valid_choices = []
        invalid_chars = []
        
        for char in sequence:
            if char in self.menu_options:
                valid_choices.append(char)
            else:
                invalid_chars.append(char)
        
        if invalid_chars:
            print(f"❌ 序列中包含无效字符: {', '.join(invalid_chars)}")
            print(f"✅ 有效字符: {', '.join(self.menu_options.keys())}")
            return
        
        if not valid_choices:
            print("❌ 没有有效的执行选项")
            return
        
        # 显示将要执行的操作
        print(f"📋 将依次执行以下操作:")
        print("-" * 50)
        for i, choice in enumerate(valid_choices, 1):
            option = self.menu_options[choice]
            print(f"{i}. [{choice}] {option['title']}")
        print("-" * 50)
        print(f"共 {len(valid_choices)} 个操作")
        
        # 设置批量模式标志
        self._batch_mode = True
        
        # 执行序列
        for i, choice in enumerate(valid_choices, 1):
            option = self.menu_options[choice]
            
            print(f"\n{'='*60}")
            print(f"🔄 执行第 {i}/{len(valid_choices)} 个操作: [{choice}] {option['title']}")
            print(f"{'='*60}")
            
            # 如果是退出操作，直接执行并结束
            if choice == '0':
                option['function']()
                break
            
            try:
                option['function']()
                print(f"✅ 第 {i}/{len(valid_choices)} 个操作完成")
                
            except Exception as e:
                print(f"❌ 第 {i}/{len(valid_choices)} 个操作失败: {e}")
                
                # 询问是否继续
                if i < len(valid_choices):
                    print(f"⚠️ 还有 {len(valid_choices) - i} 个操作待执行")
                    continue_choice = input("是否继续执行后续操作？(y/n): ").strip().lower()
                    if continue_choice not in ['y', 'yes', '是']:
                        print("🛑 用户选择停止执行")
                        break
        
        print(f"\n🎉 自动执行完成！")


def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"❌ 配置文件 {args.config} 不存在")
        print("💡 请先创建配置文件或使用 python main.py 初始化")
        sys.exit(1)
    
    config_file = args.config
    temp_config_file = None
    
    try:
        # 处理模式设置
        mode_count = sum([args.incremental, args.full, args.custom])
        if mode_count > 1:
            print("❌ 只能指定一种模式：--incremental、--full 或 --custom")
            sys.exit(1)
        
        if args.incremental:
            config_file = modify_config_mode(args.config, 'incremental')
            temp_config_file = config_file if config_file != args.config else None
        elif args.full:
            config_file = modify_config_mode(args.config, 'full')
            temp_config_file = config_file if config_file != args.config else None
        elif args.custom:
            config_file = modify_config_mode(args.config, 'custom')
            temp_config_file = config_file if config_file != args.config else None
        
        # 提取自动执行序列
        auto_sequence = extract_sequence_from_args(args)
        
        # 创建并运行菜单
        menu = AutoExecuteMenu(config_file, auto_sequence)
        menu.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        sys.exit(1)
    finally:
        # 清理临时配置文件
        if temp_config_file and temp_config_file != args.config:
            try:
                os.unlink(temp_config_file)
                print(f"🗑️ 已清理临时配置文件")
            except Exception as e:
                print(f"⚠️ 清理临时配置文件失败: {e}")


if __name__ == "__main__":
    main() 