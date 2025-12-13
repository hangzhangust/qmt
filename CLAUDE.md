# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **ETF Grid Trading Strategy System** based on XtQuant for automated ETF trading. The system implements a grid trading strategy that automatically places buy and sell orders based on predefined price levels configured in Table.xls.

### Core Components

- **XtQuant Integration**: Connects to Guojin Securities QMT trading system for real-time market data and order execution
- **Grid Trading Engine**: Implements grid trading strategy with configurable price levels and position sizing
- **Risk Management**: Comprehensive risk control including position limits, daily loss limits, and stop-loss mechanisms
- **Backtesting**: Historical data testing and performance analysis capabilities
- **Multi-ETF Support**: Currently supports 6 ETFs configured from Table.xls

## Common Development Commands

### Running the Application
```bash
# Main entry point - presents menu for different modes
python main.py

# Direct execution modes:
python -c "from main import ETFGridTradingSystem; system = ETFGridTradingSystem(); system.start('live')"  # Live trading
python -c "from main import ETFGridTradingSystem; system = ETFGridTradingSystem(); system.start('paper')" # Paper trading
python -c "from main import run_backtest; run_backtest()"  # Backtesting
```

### Testing and Development
```bash
# Since there's no explicit test framework, run individual modules for testing:
python -c "from config.settings import ETF_GRID_CONFIG; print(ETF_GRID_CONFIG.etf_universe)"
python -c "from data.xtquant_client import XtQuantClient; client = XtQuantClient(); print('Connection test')"
```

### Configuration Validation
```bash
# Validate ETF configuration
python -c "from config.settings import ETF_GRID_CONFIG; [print(f\"ETF: {config['etf_code']} - {config['etf_name']}\") for config in ETF_GRID_CONFIG.etf_universe]"
```

## Architecture Overview

### Module Structure
- **config/**: Configuration management (settings, ETF universe, risk parameters)
- **data/**: Data handling (XtQuant client, market data, data management)
- **strategy/**: Trading strategies (grid engine, signal generation)
- **execution/**: Order execution and tracking
- **risk/**: Risk management and position sizing
- **backtest/**: Historical testing and performance analysis
- **utils/**: Utilities (logging, helpers)

### Key Design Patterns
- **Strategy Pattern**: Separate strategy classes for different ETFs
- **Factory Pattern**: Configuration-driven ETF strategy creation
- **Observer Pattern**: Market data callbacks for real-time updates
- **Risk Management Layer**: Centralized risk checks before all trades

### Data Flow
1. **Market Data**: XtQuant client → Real-time price updates
2. **Signal Generation**: Grid strategy → Buy/sell signals based on price levels
3. **Risk Check**: Risk manager validates all trading signals
4. **Order Execution**: Executor places orders via XtQuant
5. **Position Tracking**: Continuous monitoring of portfolio state

## Configuration

### QMT Path Configuration
Critical: Must configure QMT data directory in `config/settings.py:14`:
```python
QMT_DATA_DIR = r"C:\Users\zhanghang\国金证券QMT交易端\datadir"
```

### ETF Configuration (Table.xls)
The system reads ETF configurations from Table.xls with these fields:
- ETF code and name
- Base price for grid calculation
- Up/down trigger percentages
- Buy/sell amounts
- Validity period

### Risk Parameters
Key risk settings in `config/settings.py:289-331`:
- Max daily loss: 5%
- Max position per ETF: 30%
- Stop loss: 15%
- Take profit: 20%

## Important Implementation Details

### Grid Trading Logic
- Grid levels are calculated from base price using trigger percentages
- Buy orders placed when price drops below grid levels
- Sell orders placed when price rises above grid levels
- Dynamic position sizing based on allocated capital

### XtQuant Integration
- Session ID: 123456 (configurable in settings)
- Requires QMT terminal to be running
- Handles connection failures and automatic reconnection

### Risk Management
- Pre-trade risk checks on all orders
- Real-time position monitoring
- Automatic trading suspension on risk breaches
- Daily loss limits and position concentration controls

### Encoding Note
The main.py file uses GBK encoding (`#coding:gbk`) which may cause issues with certain characters. When editing, preserve the encoding declaration.

## Development Guidelines

### Adding New ETFs
1. Update Table.xls with new ETF configuration
2. The system will automatically parse and create grid levels
3. Verify configuration using the validation command above

### Modifying Grid Strategy
- Grid logic implemented in `strategy/grid_engine.py`
- Signal generation in `strategy/signal_generator.py`
- Risk parameters in `config/risk_params.py`

### Extending Risk Management
- Core risk logic in `risk/risk_manager.py`
- Position sizing in `risk/position_sizer.py`
- Stop-loss logic in `risk/stop_loss.py`

## Debugging and Monitoring

### Logging
- Configurable log levels in settings
- Logs stored in `logs/etf_grid_trading.log`
- Automatic log rotation (10MB max, 5 backups)

### System Status
Real-time monitoring available through `get_system_status()` method:
- Running strategies and their states
- Risk metrics and alerts
- Execution statistics
- Portfolio P&L

### Common Issues
- **XtQuant Connection**: Verify QMT terminal is running and data path is correct
- **Order Failures**: Check account balance and market hours
- **Configuration Errors**: Validate Table.xls format and ETF codes