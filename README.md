# A股量化数据下载程序

基于Tushare接口的A股量化数据下载程序，按照"目录-命名-元数据"三位一体方案设计，支持股票、基金、指数的日线和分钟线数据下载。

## ✨ 功能特点

- **🎯 完整的数据覆盖**：支持股票、ETF、LOF、指数的日线和分钟线数据
- **⚡ 突破API限制**：智能分批算法突破stk_mins接口8000条限制
- **📊 双格式支持**：支持CSV和Parquet两种数据格式，满足不同场景需求
- **🔄 增量更新机制**：通过元数据管理，避免重复下载，支持断点续传
- **📈 后复权算法**：采用后复权算法，确保增量模式下数据一致性
- **🗂️ 灵活的目录结构**：按资产类别和数据频率组织，便于后续使用
- **🛡️ 稳健的错误处理**：支持重试、限流、异常恢复
- **🎮 友好的交互界面**：支持批量下载和精确控制
- **📝 详细的日志记录**：完整的下载过程记录和错误追踪
- **🔧 自定义连接**：支持自定义Tushare服务器地址

## 🆕 版本1.0新功能

### 📊 数据格式选择
支持CSV和Parquet两种数据保存格式：
- **CSV格式**：兼容性好，可读性强，适合小规模数据和调试分析
- **Parquet格式**：压缩率高，读取快速，适合大规模数据和生产环境

### ⚡ 突破分钟数据限制
- 智能分批下载算法，自动按月分批获取分钟数据
- 突破单次8000条限制，支持任意时间范围下载
- 自动拼接、去重、降序排列，确保数据完整性

### 📈 后复权算法改进
- 从前复权改为后复权，历史数据不会因新数据而改变
- 确保增量模式下数据一致性，适合长期数据维护

### 🎯 指数分钟数据支持
- 新增指数分钟数据下载功能
- 支持主要指数和全部指数的分钟数据
- 与股票、基金分钟数据使用相同的分批算法

### 🔧 自定义Tushare连接
- 支持自定义Tushare服务器地址
- 灵活适配不同的数据源环境

## 📁 目录结构

```
TushareData/
├─ config.json              # 配置文件（包含敏感信息，不会被Git跟踪）
├─ config.json.example      # 配置文件模板（可安全提交到Git）
├─ start.py                 # 快速启动脚本
├─ main.py                  # 主程序入口
├─ interactive_menu.py      # 交互式菜单
├─ data_downloader.py       # 核心下载模块
├─ stock_downloader.py      # 股票数据下载
├─ fund_downloader.py       # 基金数据下载
├─ index_downloader.py      # 指数数据下载
├─ update_reference.py      # 基础数据更新
├─ data/                    # 历史行情数据（data_root配置的目录，默认./data）
│  ├─ reference/            # 基础数据（股票列表、基金列表、交易日历）
│  │  ├─ stock_basic.csv
│  │  ├─ fund_basic.csv
│  │  ├─ index_basic.csv
│  │  └─ trade_cal.csv
│  ├─ data/                 # 历史行情数据
│  │  ├─ equities/          # 股票数据
│  │  │  ├─ daily/          # 日线数据（CSV格式）
│  │  │  ├─ minute_1/       # 1分钟数据（Parquet格式）
│  │  │  └─ minute_5/        # 5分钟数据（Parquet格式）
│  │  ├─ funds/             # 基金数据
│  │  │  ├─ daily/          # 日线数据（CSV格式）
│  │  │  └─ minute_1/       # 1分钟数据（Parquet格式）
│  │  └─ indices/           # 指数数据
│  │      ├─ daily/         # 日线数据（CSV格式）
│  │      └─ minute_1/      # 1分钟数据（Parquet格式）
│  └─ meta/                 # 元数据（同步状态）
│      ├─ last_sync_equities_daily.csv
│      ├─ last_sync_funds_daily.csv
│      └─ last_sync_indices_daily.csv
├─ logs/                    # 下载日志
│  └─ YYYYMMDD_download.log
└─ docs/                    # 文档目录
   ├─ 快速使用指南.md
   ├─ 筛选配置说明.md
   └─ 数据下载方案.md
```

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas tushare pathlib pyarrow  # pyarrow用于Parquet格式支持
```

### 配置设置

#### 创建配置文件

项目提供了 `config.json.example` 作为配置模板。首次使用时，需要从模板创建配置文件：

```bash
# 复制配置文件模板
cp config.json.example config.json
```

#### 配置Tushare Token

编辑 `config.json` 文件，将 `YOUR_TOKEN_HERE` 替换为你的真实 Tushare token：

```json
{
  "tushare_token": "你的真实token",
  "tushare_url": "",
  "data_root": "./data",
  "data_format": "Parquet",
  "sleep_secs": 0.12,
  "retry": 3,
  "threads": 4,
  "date_ranges": {
    "default_start_date": "20190101",
    "default_end_date": "20251231",
    "lookback_days": 1800,
    "update_mode": "full",
    "limits": null
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

**重要配置说明**：
- `tushare_token`: **必须**设置为您的真实Tushare令牌（从 [Tushare官网](https://tushare.pro/) 获取）
- `tushare_url`: 服务器地址，留空或设置为 `""` 使用默认Tushare官方服务器 (https://tushare.pro/)
- `data_format`: ⚠️ **注意**：此配置项当前未使用，程序会根据数据类型自动选择格式（基础数据和日线数据使用CSV，分钟数据使用Parquet）
- `update_mode`: 更新模式，可选 `"full"`（全量）、`"incremental"`（增量）、`"custom"`（自定义筛选）

> ⚠️ **安全提示**：`config.json` 包含敏感信息，已被 `.gitignore` 忽略，不会提交到版本控制系统。请妥善保管您的配置文件。

### 立即开始

```bash
# 启动交互式界面（推荐）
python start.py

# 首次使用推荐流程
python start.py
# 输入：1b0 （更新基础数据 → 配置驱动下载 → 退出）
```

**完整下载示例（命令行模式）**：
```bash
# 1. 先更新基础数据
python main.py --update-ref

# 2. 下载所有A股日线数据（2019-2025）
python main.py --all-stocks --frequencies daily --start-date 20190101 --end-date 20251231
```

## 🎮 使用方法

### 交互式界面（推荐）

最简单的使用方式是启动交互式菜单界面：

```bash
python start.py
```

**菜单选项**：
- **[1] 更新基础数据** - 📊 下载股票列表、基金列表、交易日历
- **[2] 基金日线数据（ETF+LOF）** - 📈 下载所有基金的日线行情
- **[3] A股日线数据** - 📈 下载A股股票的日线行情  
- **[4] 指数日线数据** - 📈 下载指数的日线行情
- **[5] 基金1分钟数据（ETF+LOF）** - ⏰ 下载所有基金的1分钟行情
- **[6] A股 1分钟数据** - ⏰ 下载A股的1分钟行情
- **[7] 指数1分钟数据** - ⏰ **新增**：下载指数的1分钟行情
- **[a] 自定义下载** - ⚙️ 自定义选择股票代码和数据频率
- **[b] 配置驱动下载** - 🧪 根据config.json配置批量下载
- **[c] 补齐缺失的分钟数据** - 🔧 检查并补齐未下载的股票1分钟数据
- **[d] 分钟数据健康检查** - 📊 生成分钟数据健康检查报告
- **[0] 退出程序**

**智能批量执行**：
```bash
# 推荐首次使用
1b0  # 更新基础数据 → 配置驱动下载 → 退出

# 日常增量更新
12340  # 下载所有日线数据后退出

# 包含分钟数据
12345670  # 下载所有数据类型（数据量巨大）
```

### 命令行模式

**完整下载示例**：
```bash
# 1. 先更新基础数据
python main.py --update-ref

# 2. 下载所有A股日线数据（2019-2025）
python main.py --all-stocks --frequencies daily --start-date 20190101 --end-date 20251231
```

**其他常用命令**：
```bash
# 更新基础数据
python main.py --update-ref

# 按日期范围下载部分股票（日线），用于测试
python main.py --stock-codes 000001.SZ 600000.SH --frequencies daily --start-date 20190101 --end-date 20251231

# 下载主要指数数据
python main.py --major-indices

# 下载所有ETF数据（限制50只）
python main.py --all-etfs --limit 50

# 下载指定股票数据
python main.py --stock-codes 000001.SZ 600000.SH 000002.SZ

# 下载指定基金数据
python main.py --fund-codes 510300.SH 159915.SZ

# 下载所有类型数据（小规模测试）
python main.py --all --limit 10

# 下载股票分钟线数据
python main.py --stock-codes 000001.SZ --frequencies daily minute_1 minute_5

# 使用自定义配置文件
python main.py --config my_config.json --major-indices
```

### 命令行参数说明

| 参数 | 说明 |
|------|------|
| `--config, -c` | 配置文件路径 |
| `--update-ref` | 更新基础数据 |
| `--stocks` | 下载股票数据 |
| `--funds` | 下载基金数据 |
| `--indices` | 下载指数数据 |
| `--all` | 下载所有类型数据 |
| `--stock-codes` | 指定股票代码列表 |
| `--all-stocks` | 下载所有股票 |
| `--fund-codes` | 指定基金代码列表 |
| `--all-etfs` | 下载所有ETF |
| `--index-codes` | 指定指数代码列表 |
| `--major-indices` | 下载主要指数 |
| `--index-market` | 指数市场筛选（SSE/SZSE/ALL） |
| `--frequencies, -f` | 数据频率（daily/minute_1/minute_5等） |
| `--limit, -l` | 限制下载数量 |
| `--start-date` | 覆盖配置中的默认开始日期（格式：YYYYMMDD），自动切换为full模式 |
| `--end-date` | 覆盖配置中的默认结束日期（格式：YYYYMMDD），自动切换为full模式 |
| `--fill-missing-minutes` | 补齐缺失的股票1分钟数据 |
| `--fill-missing-minutes` | 补齐缺失的股票1分钟数据 |

## 📊 数据格式

### 智能格式选择（v1.0新特性）

程序根据数据类型**自动选择**最优保存格式，无需手动配置：

| 数据类型 | 保存格式 | 说明 |
|---------|---------|------|
| **基础数据** | CSV | 股票列表、基金列表、交易日历等参考数据 |
| **日线数据** | CSV | 日线行情数据，便于查看和分析 |
| **分钟数据** | Parquet | 分钟线数据，自动使用Parquet格式，大幅减少存储空间 |

> 💡 **提示**：格式选择基于文件路径自动判断，确保不同类型数据使用最适合的存储格式。

### 股票日线数据字段
- `ts_code`: 股票代码
- `trade_date`: 交易日期
- `open/high/low/close`: 开高低收价格
- `pre_close`: 昨收价
- `change`: 涨跌额
- `pct_chg`: 涨跌幅
- `vol`: 成交量
- `amount`: 成交额
- `adj_factor`: 复权因子
- `adj_open/adj_high/adj_low/adj_close`: **后复权价格**（v1.0改进）

### 分钟线数据字段
- `ts_code`: 股票代码
- `trade_time`: 交易时间
- `open/high/low/close`: 开高低收价格
- `vol`: 成交量
- `amount`: 成交额

### 数据格式对比

| 格式 | 文件大小 | 读取速度 | 兼容性 | 适用场景 |
|------|---------|---------|--------|----------|
| CSV | 较大 | 较慢 | 极好 | 基础数据、日线数据、调试分析 |
| Parquet | 小（压缩率50-70%） | 快 | 需要专门库 | 分钟数据、大规模数据、生产环境 |

### 存储空间优化

采用智能格式选择后的存储空间对比：

| 数据类型 | 原CSV大小 | 新格式大小 | 节省空间 |
|---------|----------|-----------|---------|
| 基础数据 | 10MB | 10MB (CSV) | 0% |
| 日线数据 | 2.5GB | 2.5GB (CSV) | 0% |
| 分钟数据 | 50GB | 20GB (Parquet) | **60%** |

## 🔄 增量更新机制

程序通过元数据文件记录每个标的的最后同步日期：

1. **首次下载**：从配置的回溯天数开始下载全部历史数据
2. **增量更新**：从上次同步日期的下一天开始下载
3. **去重处理**：自动合并新旧数据并去除重复记录
4. **断点续传**：程序中断后重启可从断点继续
5. **后复权保证**：历史数据不会因新数据而改变

## ⚙️ 配置详解

### 更新模式配置

```json
{
  "date_ranges": {
    "update_mode": "full",  // full/incremental/custom
    "limits": 10,           // 全局数量限制
    "custom_ranges": {      // custom模式专用配置
      "stocks": {
        "enabled": true,
        "exchanges": ["SSE", "SZSE"],
        "markets": ["主板", "创业板", "科创板"],
        "min_list_date": "20100101",
        "exclude_st": true,
        "frequencies": ["daily", "minute_1"],
        "limits": 20
      }
    }
  }
}
```

### 数据格式说明

**重要**：数据格式是根据数据类型**自动选择**的，不需要在配置中指定：

| 数据类型 | 保存格式 | 说明 |
|---------|---------|------|
| **基础数据** | CSV | 股票列表、基金列表、交易日历等参考数据 |
| **日线数据** | CSV | 日线行情数据，便于查看和分析 |
| **分钟数据** | Parquet | 分钟线数据，自动使用Parquet格式，大幅减少存储空间 |

> ⚠️ **注意**：配置文件中的 `data_format` 字段当前未被使用，程序会根据文件路径自动判断数据类型并选择相应格式。

### 备份配置

```json
{
  "backup_enabled": false,  // 是否启用备份（功能预留）
  "backup_dir": "./backup"  // 备份目录（功能预留）
}
```

### 连接配置

```json
{
  "tushare_token": "your_token",
  "tushare_url": "",  // 空字符串使用默认官方服务器 (https://tushare.pro/)，非空使用自定义服务器
  "sleep_secs": 0.12, // API调用间隔
  "retry": 3,         // 重试次数
  "threads": 4        // 并发线程数
}
```

**Tushare连接说明**：
- `tushare_url`为空或空字符串：使用`tushare_token`直接连接官方服务器 (https://tushare.pro/)
- `tushare_url`非空：使用私有属性动态修改方式连接自定义服务器

## 🎯 使用场景

### 量化回测准备
```bash
# 配置：update_mode: "full"（数据格式会自动选择：日线CSV，分钟Parquet）
python start.py --full --123450
```

### 日常数据更新
```bash
# 配置：update_mode: "incremental"
python start.py --incremental --123450
```

### 高频交易数据
```bash
# 下载分钟数据
python start.py --incremental --167890
```

### 特定研究需求
```bash
# 配置custom模式，设置筛选条件
python start.py --custom --b0
```

## 📈 性能参考

### 数据量对比（以1000只股票3年数据为例）

| 数据类型 | CSV大小 | Parquet大小 | 压缩率 | 读取速度提升 |
|---------|---------|-------------|--------|-------------|
| 日线数据 | 2.5GB | 1.2GB | 52% | 3-5倍 |
| 分钟数据 | 50GB | 20GB | 60% | 5-8倍 |

### 下载时间参考

| 数据类型 | 数据量级 | 预估时间 | 网络要求 |
|---------|---------|---------|----------|
| 基础数据 | 10MB | 1-2分钟 | 一般 |
| ETF日线 | 500MB | 5-10分钟 | 一般 |
| 股票日线 | 5GB | 30-60分钟 | 稳定 |
| 分钟数据 | 50GB+ | 3-8小时 | 稳定 |

## ⚠️ 注意事项

1. **API限制**：请遵守Tushare的调用频率限制，默认设置为每次调用后休眠0.12秒
2. **存储空间**：全量下载所有股票数据需要较大存储空间，建议先小规模测试
3. **网络稳定**：长时间下载建议在网络稳定的环境下进行
4. **权限要求**：部分接口可能需要Tushare积分或会员权限
5. **格式选择**：数据格式由程序根据数据类型自动选择，分钟数据使用Parquet格式需要安装pyarrow包
6. **复权算法**：v1.0改为后复权算法，确保增量模式数据一致性

## 🆘 常见问题

### Q: 如何选择数据格式？
**A**: 
- ⚠️ **注意**：数据格式由程序根据数据类型**自动选择**，无需手动配置
- **基础数据和日线数据**：自动使用CSV格式，兼容性好，便于查看
- **分钟数据**：自动使用Parquet格式，节省60%存储空间，读取速度快
- **无法切换**：格式选择基于数据类型，无法通过配置修改

### Q: 分钟数据下载很慢怎么办？
**A**: 
- v1.0已优化分批算法，自动突破8000条限制
- 检查网络连接稳定性
- 确认有足够的API积分
- 可以先下载少量数据测试

### Q: 如何只下载特定板块的股票？
**A**: 
1. 设置update_mode为"custom"
2. 在custom_ranges中配置筛选条件
3. 可按交易所、板块、上市日期等筛选

### Q: 如何处理下载失败的数据？
**A**: 
- 程序会自动重试失败的请求
- 失败信息会记录在日志文件中
- 可以查看日志定位问题，然后重新运行程序继续下载

### Q: 增量更新时数据不一致怎么办？
**A**: 
- v1.0采用后复权算法，确保历史数据稳定
- 如果仍有问题，可以使用full模式重新下载
- 检查config.json中的复权设置

## 🔧 扩展开发

程序采用模块化设计，易于扩展：

- **添加新资产类型**：继承 `DataDownloader` 类，实现特定的下载逻辑
- **自定义数据处理**：重写 `save_data_to_file` 方法，支持更多格式
- **添加新接口**：在相应模块中添加新的API调用方法
- **集成其他数据源**：可以轻松集成其他数据提供商的接口
- **自定义筛选条件**：扩展筛选配置，支持更复杂的筛选逻辑

## 📚 文档索引

- **[快速使用指南](快速使用指南.md)** - 5分钟快速上手指南
- **[筛选配置说明](筛选配置说明.md)** - 详细的配置项说明
- **[数据下载方案](docs/数据下载方案.md)** - 技术架构和设计思路

## 🎉 版本更新

### v1.0 主要更新
- ✅ **新增数据格式支持**：CSV和Parquet格式可选
- ✅ **突破分钟数据限制**：智能分批算法解决8000条限制
- ✅ **指数分钟数据**：完整支持指数分钟线下载
- ✅ **后复权算法**：改进复权计算，确保增量模式数据一致性
- ✅ **自定义连接**：支持自定义Tushare服务器地址
- ✅ **完善交互界面**：新增指数分钟数据菜单选项
- ✅ **智能错误处理**：增强网络异常和数据异常处理能力
- ✅ **完善文档**：更新所有文档，包含最新功能说明

## 📄 许可证

MIT License

---

**🚀 立即开始**: `python start.py`

**📖 详细指南**: 查看 [快速使用指南.md](快速使用指南.md) 