# All-Weather Strategy Backtest System User Guide
# 全天候策略回测系统使用指南

## Quick Start / 快速开始

### 1. Environment Setup / 环境准备

#### Install Dependencies / 安装依赖
```bash
pip install -r requirements.txt
```

#### Verify Environment / 验证环境
```bash
python setup_environment.py
```

Expected output / 预期输出:
```
============================================================
Environment Dependency Check / 环境依赖检查
============================================================
[OK] backtrader        - Backtrader Backtesting Framework
[OK] xtquant          - XtQuant Data Interface
[OK] pandas           - Pandas Data Processing
[OK] numpy            - Numpy Numerical Computing
[OK] matplotlib       - Matplotlib Plotting Library

Installed: 5/5 / 已安装: 5/5
Missing: 0/5 / 缺失: 0/5

============================================================
XtQuant Connection Check / XtQuant 连接检查
============================================================
[OK] XtQuant connection successful / XtQuant 连接成功

============================================================
[OK] Environment check passed / 环境检查通过，可以运行回测系统
```

### 2. Quick Test / 快速测试
```bash
python quick_test.py
```

### 3. Run Backtest / 运行回测

#### Basic Backtest / 基础回测
```bash
python run_backtest.py --start 20230101 --end 20231231
```

#### With Visualization / 带可视化
```bash
python run_backtest.py --start 20230101 --end 20231231 --plot
```

#### Save Charts / 保存图表
```bash
python run_backtest.py --start 20230101 --end 20231231 --save_plot results.png
```

#### Show Enhanced Metrics / 显示详细指标
```bash
python run_backtest.py --start 20230101 --end 20231231 --show_metrics
```

#### All Features / 所有功能
```bash
python run_backtest.py \
  --start 20230101 \
  --end 20231231 \
  --cash 1000000 \
  --plot \
  --save_plot results.png \
  --show_metrics
```

## Command Line Arguments / 命令行参数

### Required / 必需参数
- `--start`: Start date (YYYYMMDD) / 开始日期
- `--end`: End date (YYYYMMDD) / 结束日期

### Optional / 可选参数
- `--cash`: Initial cash (default: 1000000) / 初始资金
- `--position_ratio`: Position ratio (default: use config) / 仓位比例
- `--rebalance_period`: Rebalance period in days (default: use config) / 再平衡周期(天)
- `--commission`: Commission rate (default: 0.0001) / 手续费率
- `--no_cache`: Disable data cache / 禁用数据缓存
- `--plot`: Display visualization charts / 显示可视化图表
- `--save_plot PATH`: Save chart to file / 保存图表到文件
- `--show_metrics`: Show enhanced performance metrics / 显示增强性能指标

## Configuration / 配置

Configuration file location / 配置文件位置: `~/QMT_Strategy_Data/strategy_config.json`

Example / 示例:
```json
{
  "all_weather_position_ratio": 0.5,
  "rebalance_period": 60,
  "rebalance_threshold": 0.05,
  "cache_enabled": true,
  "cache_expire_days": 7
}
```

## Output Files / 输出文件

### Backtest Result Report / 回测结果报告
- Filename format / 文件名格式: `backtest_result_YYYYMMDD_HHMMSS.txt`
- Includes / 包含:
  - Backtest period / 回测区间
  - Initial and final value / 初始和最终资金
  - Total return / 总收益率
  - Enhanced metrics (if --show_metrics) / 增强性能指标

### Visualization Charts / 可视化图表 (if using --plot or --save_plot)
- PNG format / PNG格式
- 4 subplots / 4个子图:
  1. Equity curve / 净值曲线
  2. Drawdown curve / 回撤曲线
  3. Returns distribution / 收益分布
  4. Asset allocation / 资产配置

## Troubleshooting / 常见问题

### Q1: ModuleNotFoundError: No module named 'backtrader'
**A**: Run / 运行: `pip install -r requirements.txt`

### Q2: XtQuant connection failed
**A**:
1. Check if XtQuant client is running / 检查XtQuant客户端是否运行
2. Check account login / 检查账号是否登录
3. Run / 运行: `python setup_environment.py`

### Q3: Chinese display garbled / 中文显示乱码
**A**:
- Windows: Use PowerShell or Git Bash
- Set environment variable / 设置环境变量: `set PYTHONIOENCODING=utf-8`

### Q4: Chart not displayed / 图表不显示
**A**:
- Check matplotlib / 检查matplotlib: `pip show matplotlib`
- Use / 使用: `--save_plot results.png`
- Check backend / 检查后端: `export MPLBACKEND=TkAgg`

## Performance Metrics / 性能指标说明

### Basic Metrics / 基础指标
- **Total Return / 总收益率**: (Final - Initial) / Initial
- **Annual Return / 年化收益率**: (Final/Initial)^(365/Days) - 1

### Risk Metrics / 风险指标
- **Max Drawdown / 最大回撤**: Maximum peak-to-trough decline
- **Volatility / 波动率**: Daily return standard deviation × √252

### Risk-Adjusted Return / 风险调整收益
- **Sharpe Ratio / 夏普比率**: (Annual Return - Risk Free) / Volatility
- **Sortino Ratio / 索提诺比率**: (Annual Return - Risk Free) / Downside Deviation

### Trading Statistics / 交易统计
- **Total Trades / 总交易次数**: Total number of trades
- **Won/Lost Trades / 盈利亏损次数**: Winning and losing trades
- **Win Rate / 胜率**: Won trades / Total trades

## Example Scenarios / 示例场景

### Test Different Position Ratios / 测试不同仓位比例
```bash
python run_backtest.py --start 20230101 --end 20231231 --position_ratio 0.3 --save_plot test_30.png
python run_backtest.py --start 20230101 --end 20231231 --position_ratio 0.5 --save_plot test_50.png
python run_backtest.py --start 20230101 --end 20231231 --position_ratio 0.7 --save_plot test_70.png
```

### Annual Backtests / 年度回测
```bash
# 2021
python run_backtest.py --start 20210101 --end 20211231 --show_metrics --save_plot 2021.png
# 2022
python run_backtest.py --start 20220101 --end 20221231 --show_metrics --save_plot 2022.png
# 2023
python run_backtest.py --start 20230101 --end 20231231 --show_metrics --save_plot 2023.png
```

### Parameter Optimization / 参数优化
```bash
for period in 30 60 90; do
  python run_backtest.py --start 20230101 --end 20231231 \
    --rebalance_period $period \
    --show_metrics \
    --save_plot rebalance_${period}.png
done
```

## Technical Support / 技术支持

If you encounter issues / 如遇问题:
1. Run / 运行: `python setup_environment.py`
2. Check / 查看: `backtest_result_*.txt` files
3. Check / 查看: `~/QMT_Strategy_Data/logs/` log files
