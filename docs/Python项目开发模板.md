# Python项目开发模板

## 概述
本文档基于TushareData项目总结了一套完整的Python项目开发模板，涵盖架构设计、功能实现、界面设计等各个方面的最佳实践，可供其他项目开发借鉴。

## 项目架构概览

### 核心设计理念
- **分层架构**：清晰的业务逻辑分层
- **配置驱动**：通过配置文件控制程序行为
- **模块化设计**：功能模块独立且可复用
- **多界面支持**：命令行 + 交互式菜单
- **扩展性优先**：便于功能扩展和维护

### 项目结构模板
```
project_name/
├── main.py                 # 主程序入口
├── start.py                # 快速启动器
├── config.json             # 配置文件
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── base_processor.py   # 基础处理器
│   └── config_manager.py   # 配置管理器
├── modules/                # 业务模块
│   ├── __init__.py
│   ├── module_a.py
│   └── module_b.py
├── ui/                     # 用户界面
│   ├── __init__.py
│   ├── interactive_menu.py
│   └── cli_parser.py
├── data/                   # 数据目录
├── logs/                   # 日志目录
├── tests/                  # 测试代码
├── docs/                   # 文档
├── requirements.txt        # 依赖包
└── README.md              # 项目说明
```

## 一、核心架构设计

### 1.1 基础处理器模式

```python
# core/base_processor.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class BaseProcessor:
    """基础处理器类 - 所有业务模块的基类"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self._setup_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {self.config_file} 不存在")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        log_config = self.config.get('logging', {})
        
        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 配置日志格式
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', 
                   '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        logger = logging.getLogger(self.__class__.__name__)
        
        # 添加文件处理器
        log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter(log_config.get('format'))
        )
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_directories(self):
        """创建必要的目录结构"""
        directories = [
            Path('data'),
            Path('logs'),
            Path('temp'),
            Path('backup')
        ]
        
        # 从配置中读取额外目录
        extra_dirs = self.config.get('directories', [])
        directories.extend([Path(d) for d in extra_dirs])
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """获取配置文件的指定段落"""
        return self.config.get(section, {})
    
    def retry_operation(self, func, *args, max_retries: int = 3, **kwargs):
        """带重试的操作执行"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"操作失败，已重试{max_retries}次: {e}")
                    raise
                else:
                    self.logger.warning(f"操作失败，第{attempt+1}次重试: {e}")
```

### 1.2 配置管理系统

```python
# core/config_manager.py
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.temp_configs = []  # 临时配置文件列表
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, config: Dict[str, Any], file_path: Optional[Path] = None):
        """保存配置"""
        target_file = file_path or self.config_file
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def create_temp_config(self, modifications: Dict[str, Any]) -> str:
        """创建临时配置文件"""
        config = self.load_config()
        
        # 应用修改
        for key, value in modifications.items():
            self._set_nested_value(config, key, value)
        
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.json', prefix='config_temp_'
        )
        
        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.temp_configs.append(temp_path)
            return temp_path
        except Exception as e:
            os.close(temp_fd)
            os.unlink(temp_path)
            raise e
    
    def _set_nested_value(self, config: Dict, key: str, value: Any):
        """设置嵌套配置值"""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def cleanup_temp_configs(self):
        """清理临时配置文件"""
        for temp_config in self.temp_configs:
            try:
                os.unlink(temp_config)
            except Exception:
                pass
        self.temp_configs.clear()
    
    def __del__(self):
        """析构时自动清理"""
        self.cleanup_temp_configs()
```

### 1.3 主程序架构

```python
# main.py
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from core.base_processor import BaseProcessor
from modules.module_a import ModuleA
from modules.module_b import ModuleB
from ui.interactive_menu import InteractiveMenu

class MainApplication(BaseProcessor):
    """主应用程序类"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
        self.module_a = ModuleA(config_file)
        self.module_b = ModuleB(config_file)
    
    def process_all(self, options: Dict[str, Any]):
        """处理所有任务"""
        self.logger.info("开始处理所有任务...")
        
        if options.get('module_a'):
            self.module_a.process()
        
        if options.get('module_b'):
            self.module_b.process()
        
        self.logger.info("所有任务处理完成")
    
    def process_by_config(self):
        """根据配置文件处理"""
        config = self.get_config_section('processing')
        
        for module_name, module_config in config.items():
            if module_config.get('enabled', False):
                self.logger.info(f"处理模块: {module_name}")
                # 根据模块名称调用相应处理器
                getattr(self, f"_{module_name}_process")(module_config)

def parse_arguments():
    """命令行参数解析"""
    parser = argparse.ArgumentParser(description='项目描述')
    
    # 基础参数
    parser.add_argument('--config', '-c', default='config.json',
                       help='配置文件路径')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='启动交互式界面')
    
    # 功能参数
    parser.add_argument('--module-a', action='store_true',
                       help='处理模块A')
    parser.add_argument('--module-b', action='store_true',
                       help='处理模块B')
    parser.add_argument('--all', action='store_true',
                       help='处理所有模块')
    
    # 通用参数
    parser.add_argument('--limit', type=int, help='处理数量限制')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"配置文件 {args.config} 不存在")
        sys.exit(1)
    
    try:
        app = MainApplication(args.config)
        
        if args.interactive:
            # 启动交互式界面
            menu = InteractiveMenu(args.config)
            menu.run()
        else:
            # 命令行模式
            options = {
                'module_a': args.module_a or args.all,
                'module_b': args.module_b or args.all,
                'limit': args.limit
            }
            app.process_all(options)
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 二、业务模块设计

### 2.1 业务模块模板

```python
# modules/module_a.py
import pandas as pd
from typing import List, Dict, Any
from core.base_processor import BaseProcessor

class ModuleA(BaseProcessor):
    """业务模块A - 继承基础处理器"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
        self.module_config = self.get_config_section('module_a')
    
    def get_data_list(self, use_filter: bool = True) -> pd.DataFrame:
        """获取数据列表"""
        # 从文件或API获取数据
        data_file = Path('data/reference/data_list.csv')
        if not data_file.exists():
            self.logger.error("数据文件不存在")
            return pd.DataFrame()
        
        data = pd.read_csv(data_file)
        
        if use_filter:
            data = self._apply_filters(data)
        
        return data
    
    def _apply_filters(self, data: pd.DataFrame) -> pd.DataFrame:
        """应用过滤条件"""
        filters = self.module_config.get('filters', {})
        
        # 示例过滤逻辑
        if 'status' in filters:
            data = data[data['status'].isin(filters['status'])]
        
        if 'date_range' in filters:
            start_date = filters['date_range'].get('start')
            end_date = filters['date_range'].get('end')
            if start_date:
                data = data[data['date'] >= start_date]
            if end_date:
                data = data[data['date'] <= end_date]
        
        # 数量限制
        limit = filters.get('limit')
        if limit:
            data = data.head(limit)
        
        return data
    
    def process_single_item(self, item_id: str) -> Dict[str, Any]:
        """处理单个项目"""
        self.logger.info(f"处理项目: {item_id}")
        
        try:
            # 具体业务逻辑
            result = self._do_process(item_id)
            
            # 保存结果
            self._save_result(item_id, result)
            
            return {'status': 'success', 'data': result}
        
        except Exception as e:
            self.logger.error(f"处理项目失败 {item_id}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _do_process(self, item_id: str) -> Dict[str, Any]:
        """执行具体处理逻辑"""
        # 这里实现具体的业务逻辑
        return {'processed_data': f'result for {item_id}'}
    
    def _save_result(self, item_id: str, result: Dict[str, Any]):
        """保存处理结果"""
        output_dir = Path('data/output')
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f'{item_id}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    def process_batch(self, item_ids: List[str] = None):
        """批量处理"""
        if item_ids is None:
            data_list = self.get_data_list()
            item_ids = data_list['id'].tolist()
        
        self.logger.info(f"开始批量处理，共{len(item_ids)}个项目")
        
        success_count = 0
        error_count = 0
        
        for i, item_id in enumerate(item_ids, 1):
            self.logger.info(f"处理进度: {i}/{len(item_ids)}")
            
            result = self.process_single_item(item_id)
            
            if result['status'] == 'success':
                success_count += 1
            else:
                error_count += 1
        
        self.logger.info(f"批量处理完成: 成功{success_count}个，失败{error_count}个")
    
    def process(self):
        """主处理入口"""
        if self.module_config.get('enabled', True):
            self.process_batch()
        else:
            self.logger.info("模块A已禁用")
```

### 2.2 数据处理模式

```python
# 数据处理通用模式
class DataProcessor:
    """数据处理器基类"""
    
    def extract(self) -> Any:
        """数据提取"""
        raise NotImplementedError
    
    def transform(self, data: Any) -> Any:
        """数据转换"""
        raise NotImplementedError
    
    def load(self, data: Any) -> bool:
        """数据加载"""
        raise NotImplementedError
    
    def process(self) -> bool:
        """ETL流程"""
        try:
            # Extract
            raw_data = self.extract()
            if not raw_data:
                return False
            
            # Transform
            processed_data = self.transform(raw_data)
            
            # Load
            return self.load(processed_data)
        
        except Exception as e:
            self.logger.error(f"数据处理失败: {e}")
            return False
```

## 三、交互界面设计

### 3.1 交互式菜单模板

```python
# ui/interactive_menu.py
import os
from typing import Dict, Callable
from core.base_processor import BaseProcessor

class InteractiveMenu(BaseProcessor):
    """交互式菜单基类"""
    
    def __init__(self, config_file: str = 'config.json'):
        super().__init__(config_file)
        self.menu_options = self._setup_menu_options()
        self._batch_mode = False
    
    def _setup_menu_options(self) -> Dict[str, Dict]:
        """设置菜单选项 - 子类重写此方法"""
        return {
            '1': {
                'title': '功能1',
                'function': self._function1,
                'description': '功能1描述'
            },
            '2': {
                'title': '功能2', 
                'function': self._function2,
                'description': '功能2描述'
            },
            '0': {
                'title': '退出程序',
                'function': self._exit_program,
                'description': '退出程序'
            }
        }
    
    def _clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self):
        """打印头部信息"""
        print("=" * 60)
        print("🚀 项目名称")
        print("=" * 60)
        print("项目描述")
        print("-" * 60)
    
    def _print_menu(self):
        """打印菜单"""
        print("\n📋 请选择功能:")
        print("-" * 60)
        
        for key, option in self.menu_options.items():
            if key == '0':
                print()
            print(f"[{key}] {option['title']}")
            print(f"    {option['description']}")
        
        print("-" * 60)
        print("💡 提示：可输入多个选项进行批量执行，如 '123'")
    
    def _get_user_choice(self) -> str:
        """获取用户选择"""
        while True:
            choice = input("\n请输入选项编号: ").strip()
            
            if not choice:
                print("❌ 请输入选项编号")
                continue
            
            # 验证所有字符都是有效选项
            valid_chars = []
            invalid_chars = []
            
            for char in choice:
                if char in self.menu_options:
                    valid_chars.append(char)
                else:
                    invalid_chars.append(char)
            
            if invalid_chars:
                print(f"❌ 无效字符: {', '.join(invalid_chars)}")
                continue
            
            return choice
    
    def _confirm_action(self, description: str) -> bool:
        """操作确认"""
        if self._batch_mode:
            return True
        
        print(f"\n📌 即将执行: {description}")
        while True:
            confirm = input("确认执行吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                return True
            elif confirm in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y/n")
    
    def _execute_choices(self, choices: str):
        """执行选择"""
        if len(choices) > 1:
            self._batch_mode = True
            print(f"\n🔄 批量执行模式，共{len(choices)}个操作")
        
        for i, choice in enumerate(choices, 1):
            option = self.menu_options[choice]
            
            if len(choices) > 1:
                print(f"\n{'='*60}")
                print(f"🔄 执行第{i}/{len(choices)}个操作: {option['title']}")
                print(f"{'='*60}")
            
            try:
                option['function']()
                if len(choices) > 1:
                    print(f"✅ 第{i}/{len(choices)}个操作完成")
            except Exception as e:
                print(f"❌ 操作失败: {e}")
                if len(choices) > 1 and i < len(choices):
                    continue_choice = input("是否继续执行？(y/n): ").strip().lower()
                    if continue_choice not in ['y', 'yes', '是']:
                        break
        
        self._batch_mode = False
    
    def run(self):
        """运行菜单"""
        while True:
            try:
                self._clear_screen()
                self._print_header()
                self._print_menu()
                
                choice = self._get_user_choice()
                self._execute_choices(choice)
                
                if '0' in choice:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 程序被用户中断")
                break
            except Exception as e:
                print(f"\n❌ 程序错误: {e}")
                input("\n按回车键继续...")
    
    # 示例功能函数
    def _function1(self):
        """功能1实现"""
        if not self._confirm_action("执行功能1"):
            return
        
        print("\n🔄 正在执行功能1...")
        # 具体业务逻辑
        print("✅ 功能1执行完成")
        
        if not self._batch_mode:
            input("\n按回车键继续...")
    
    def _function2(self):
        """功能2实现"""
        if not self._confirm_action("执行功能2"):
            return
        
        print("\n🔄 正在执行功能2...")
        # 具体业务逻辑
        print("✅ 功能2执行完成")
        
        if not self._batch_mode:
            input("\n按回车键继续...")
    
    def _exit_program(self):
        """退出程序"""
        print("\n👋 感谢使用，再见！")
```

### 3.2 命令行增强启动器

```python
# start.py
import argparse
import sys
from pathlib import Path
from ui.interactive_menu import InteractiveMenu
from core.config_manager import ConfigManager

def parse_arguments():
    """动态参数解析"""
    parser = argparse.ArgumentParser(description='项目启动器')
    
    # 基础参数
    parser.add_argument('--config', '-c', default='config.json',
                       help='配置文件路径')
    
    # 模式参数
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--mode-a', action='store_true',
                           help='设置为模式A')
    mode_group.add_argument('--mode-b', action='store_true',
                           help='设置为模式B')
    
    # 自动执行参数
    parser.add_argument('--auto', help='自动执行序列')
    
    # 动态序列参数识别
    for arg in sys.argv:
        if (arg.startswith('--') and len(arg) > 2 and
            all(c.isdigit() or c.isalpha() for c in arg[2:]) and
            arg not in ['--config', '--mode-a', '--mode-b', '--auto', '--help']):
            parser.add_argument(arg, action='store_const', const=arg[2:],
                               help=f'自动执行序列: {arg[2:]}')
    
    return parser.parse_args()

class AutoExecuteMenu(InteractiveMenu):
    """支持自动执行的菜单"""
    
    def __init__(self, config_file: str, auto_sequence: str = None):
        super().__init__(config_file)
        self.auto_sequence = auto_sequence
    
    def run(self):
        """运行菜单"""
        if self.auto_sequence:
            self._auto_execute()
        else:
            super().run()
    
    def _auto_execute(self):
        """自动执行序列"""
        print(f"🤖 自动执行模式: {self.auto_sequence}")
        
        # 验证序列
        valid_chars = [c for c in self.auto_sequence if c in self.menu_options]
        invalid_chars = [c for c in self.auto_sequence if c not in self.menu_options]
        
        if invalid_chars:
            print(f"❌ 无效字符: {', '.join(invalid_chars)}")
            return
        
        # 显示执行计划
        print("📋 执行计划:")
        for i, char in enumerate(valid_chars, 1):
            print(f"{i}. [{char}] {self.menu_options[char]['title']}")
        
        # 执行序列
        self._batch_mode = True
        self._execute_choices(self.auto_sequence)

def main():
    """主函数"""
    args = parse_arguments()
    
    if not Path(args.config).exists():
        print(f"❌ 配置文件 {args.config} 不存在")
        sys.exit(1)
    
    config_manager = ConfigManager(args.config)
    config_file = args.config
    
    try:
        # 处理模式设置
        if args.mode_a:
            config_file = config_manager.create_temp_config({'mode': 'a'})
        elif args.mode_b:
            config_file = config_manager.create_temp_config({'mode': 'b'})
        
        # 提取自动执行序列
        auto_sequence = getattr(args, 'auto', None)
        if not auto_sequence:
            for attr in dir(args):
                if not attr.startswith('_'):
                    value = getattr(args, attr)
                    if (isinstance(value, str) and value and
                        all(c.isdigit() or c.isalpha() for c in value)):
                        auto_sequence = value
                        break
        
        # 运行菜单
        menu = AutoExecuteMenu(config_file, auto_sequence)
        menu.run()
    
    finally:
        config_manager.cleanup_temp_configs()

if __name__ == "__main__":
    main()
```

## 四、配置文件设计

### 4.1 配置文件模板

```json
{
  "api_config": {
    "api_key": "YOUR_API_KEY_HERE",
    "base_url": "https://api.example.com",
    "timeout": 30,
    "retry_count": 3,
    "rate_limit": 0.1
  },
  "data_config": {
    "data_root": "./data",
    "backup_enabled": true,
    "backup_dir": "./backup",
    "temp_dir": "./temp"
  },
  "processing_config": {
    "mode": "incremental",
    "batch_size": 100,
    "parallel_workers": 4,
    "filters": {
      "enabled": true,
      "status": ["active"],
      "date_range": {
        "start": "20200101",
        "end": "auto"
      }
    }
  },
  "module_a": {
    "enabled": true,
    "parameters": {
      "param1": "value1",
      "param2": 100
    },
    "filters": {
      "limit": 50,
      "status": ["active", "pending"]
    }
  },
  "module_b": {
    "enabled": false,
    "parameters": {
      "param1": "value1"
    }
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_enabled": true
  },
  "directories": [
    "./custom_dir1",
    "./custom_dir2"
  ]
}
```

## 五、错误处理和日志系统

### 5.1 异常处理模式

```python
# 自定义异常类
class ProjectException(Exception):
    """项目基础异常类"""
    pass

class ConfigError(ProjectException):
    """配置错误"""
    pass

class DataProcessingError(ProjectException):
    """数据处理错误"""
    pass

class APIError(ProjectException):
    """API调用错误"""
    pass

# 异常处理装饰器
def handle_exceptions(logger=None):
    """异常处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ProjectException as e:
                if logger:
                    logger.error(f"业务异常: {e}")
                raise
            except Exception as e:
                if logger:
                    logger.error(f"未知异常: {e}")
                raise ProjectException(f"操作失败: {e}")
        return wrapper
    return decorator

# 使用示例
@handle_exceptions(logger)
def risky_operation():
    """可能出错的操作"""
    pass
```

### 5.2 日志系统设计

```python
# 日志配置
import logging
from logging.handlers import RotatingFileHandler

def setup_advanced_logging(config: Dict[str, Any]) -> logging.Logger:
    """高级日志配置"""
    logger = logging.getLogger('project')
    logger.setLevel(getattr(logging, config.get('level', 'INFO')))
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(config.get('format'))
    )
    logger.addHandler(console_handler)
    
    # 文件输出（带轮转）
    if config.get('file_enabled', True):
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(
            logging.Formatter(config.get('format'))
        )
        logger.addHandler(file_handler)
    
    return logger
```

## 六、测试和部署

### 6.1 测试框架

```python
# tests/test_base.py
import unittest
import tempfile
import json
from pathlib import Path
from core.base_processor import BaseProcessor

class TestBaseProcessor(unittest.TestCase):
    """基础处理器测试"""
    
    def setUp(self):
        """测试准备"""
        self.test_config = {
            "logging": {"level": "DEBUG"},
            "data_root": "./test_data"
        }
        
        # 创建临时配置文件
        self.config_fd, self.config_file = tempfile.mkstemp(suffix='.json')
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """测试清理"""
        os.close(self.config_fd)
        os.unlink(self.config_file)
    
    def test_config_loading(self):
        """测试配置加载"""
        processor = BaseProcessor(self.config_file)
        self.assertEqual(processor.config['logging']['level'], 'DEBUG')
    
    def test_directory_creation(self):
        """测试目录创建"""
        processor = BaseProcessor(self.config_file)
        self.assertTrue(Path('test_data').exists())

if __name__ == '__main__':
    unittest.main()
```

### 6.2 部署脚本

```python
# deploy.py
import subprocess
import sys
from pathlib import Path

def check_requirements():
    """检查依赖"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ 依赖安装完成")
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        sys.exit(1)

def setup_directories():
    """创建目录"""
    directories = ['data', 'logs', 'temp', 'backup']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ 目录创建完成")

def check_config():
    """检查配置"""
    config_file = Path('config.json')
    if not config_file.exists():
        print("❌ 配置文件不存在，请先创建 config.json")
        sys.exit(1)
    print("✅ 配置文件检查通过")

def main():
    """部署主函数"""
    print("🚀 开始部署...")
    
    check_requirements()
    setup_directories()
    check_config()
    
    print("🎉 部署完成！")
    print("运行 python start.py 启动程序")

if __name__ == "__main__":
    main()
```

## 七、开发最佳实践

### 7.1 代码组织原则
- **单一职责**：每个类和函数只负责一个功能
- **依赖注入**：通过构造函数传入依赖
- **配置外置**：所有配置都在配置文件中
- **错误处理**：完善的异常处理机制
- **日志记录**：关键操作都要记录日志

### 7.2 扩展性设计
- **插件架构**：支持动态加载模块
- **事件驱动**：使用事件机制解耦
- **接口抽象**：定义清晰的接口规范
- **配置驱动**：通过配置控制行为

### 7.3 性能优化
- **懒加载**：按需加载资源
- **缓存机制**：缓存频繁访问的数据
- **批量处理**：减少IO操作次数
- **并发处理**：合理使用多线程/多进程

## 总结

这套Python项目开发模板基于TushareData项目的最佳实践，提供了：

1. **完整的架构设计**：分层架构、模块化设计
2. **灵活的配置系统**：支持动态配置和临时配置
3. **友好的用户界面**：命令行 + 交互式菜单
4. **健壮的错误处理**：完善的异常处理和日志系统
5. **良好的扩展性**：便于功能扩展和维护

开发者可以根据具体需求调整和扩展这套模板，快速构建高质量的Python项目。 