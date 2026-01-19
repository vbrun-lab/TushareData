# TushareData - A股量化数据下载程序

## 版本信息

### v1.0.0 (2025-07-04)

#### 🎉 主要特性
- **智能格式选择**：基础数据和日线数据保存为CSV格式，分钟数据自动保存为Parquet格式，节省60%存储空间
- **灵活连接方式**：支持官方Tushare服务器和自定义服务器连接
- **菜单整合优化**：将ETF和LOF数据下载合并为基金数据下载，界面更简洁
- **智能下载优化**：根据上市日期避免空下载，提升下载效率
- **后复权算法**：确保增量模式数据一致性

#### 🔧 技术改进
- 根据数据类型自动选择最优保存格式
- 优化Tushare连接逻辑，支持空URL判断
- 改进分钟数据下载逻辑，按月分批避免API限制
- 完善错误处理和重试机制

#### 📁 项目结构
```
TushareData - 1.0/
├── start.py                 # 主启动文件
├── data_downloader.py       # 核心下载器
├── stock_downloader.py      # 股票下载器
├── fund_downloader.py       # 基金下载器
├── index_downloader.py      # 指数下载器
├── interactive_menu.py      # 交互式菜单
├── main.py                  # 主下载逻辑
├── config.json              # 配置文件
├── requirements.txt         # 依赖包列表
├── README.md                # 详细说明文档
├── 快速使用指南.md          # 快速入门指南
└── 筛选配置说明.md          # 配置详解
```

#### 📦 依赖要求
- Python >= 3.8
- pandas >= 1.5.0
- tushare >= 1.2.89
- pyarrow >= 10.0.0

#### 🚀 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 配置token
# 编辑config.json，设置您的tushare_token

# 启动程序
python start.py
```

#### 📊 数据格式
- **基础数据**：CSV格式（股票列表、基金列表、交易日历）
- **日线数据**：CSV格式（便于查看和分析）
- **分钟数据**：Parquet格式（大幅减少存储空间）

#### 🎯 适用场景
- 量化交易策略回测
- 金融数据分析
- 投资研究
- 学术研究

---
**开发者**: 量化数据团队  
**许可证**: MIT  
**支持**: 欢迎提交Issue和PR 