# ⚡ Bybit Crypto Analyzer Pro

A powerful, real-time cryptocurrency analysis dashboard built with Streamlit that fetches live data from Bybit and provides advanced technical analysis, trade setups, and actionable insights.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

### 📊 Advanced Technical Analysis
- **Trend Indicators**: EMA (9, 21), SMA (200), Bollinger Bands
- **Momentum Indicators**: RSI (14), MACD (12, 26, 9)
- **Volatility Metrics**: ATR (14), Bollinger Bands
- **Volume Analysis**: Volume SMA, VWAP (Volume Weighted Average Price)

### 📈 Volume Profile Analysis
- **VPVR (Volume Profile Visible Range)**: Visualize where the most trading activity occurred
- **POC (Point of Control)**: Identify the price level with the highest traded volume
- **Value Area (VA)**: Highlight the price range where 70% of volume was traded
- **VAH/VAL**: Value Area High and Low levels for key support/resistance

### 🎯 Price Action Tools
- **Fair Value Gaps (FVG)**: Detect bullish and bearish imbalance zones
- **Candlestick Patterns**: Bullish/Bearish Engulfing, Hammer patterns
- **Support & Resistance**: Automatic detection of key price levels

### 📉 Market Data
- **Open Interest (OI)**: Track futures market positioning
- **Long/Short Ratio**: See trader sentiment in real-time
- **Funding Rate**: Monitor perpetual futures funding costs

### 🤖 Automated Trade Setups
- **Smart Entry Detection**: EMA crossovers and RSI-based signals
- **Risk Management**: Calculated Stop Loss and Take Profit levels (1:2 R/R)
- **DCA Strategy**: 3 Dollar-Cost-Averaging levels for both Long and Short positions
- **Confidence Scoring**: AI-powered confluence analysis (0-100%) with detailed reasoning
- **Strategy Filters**: Optional Trend (SMA 200), Volume, ADX, and MACD filters to refine signals

### 🧪 Backtesting Engine
- **Historical Simulation**: Test strategies on past data to verify performance
- **Performance Metrics**: Win Rate, Profit Factor, Total Return, Max Drawdown
- **Equity Curve**: Visual growth of capital over time
- **Advanced Filters**: Trend (SMA 200), Volume, ADX, and MACD filters to refine strategy
- **DCA Support**: Simulate Dollar-Cost Averaging logic in backtests

### 🔍 Multi-Symbol Screener
- **Bulk Analysis**: Scan multiple cryptocurrencies simultaneously
- **Trade Setup Detection**: Automatically identify high-confidence setups across all symbols
- **Complete Trade Data**: Entry, Stop Loss, Take Profit, and all 3 DCA levels for each setup
- **Confidence Ranking**: Results sorted by confidence score for quick decision-making
- **Customizable Symbol List**: Add or remove symbols to match watchlist
- **Synchronized Settings**: Uses the same timeframe and loopback settings as main analysis
- **Strategy Filters**: Apply the same Trend, Volume, ADX, and MACD filters as the Dashboard

### 🎨 Professional UI
- **Sidebar Navigation**: Easy access to Dashboard, Multi-Screener, and Backtester
- **Dark mode optimized interface**: Sleek, modern design
- **Interactive Plotly charts**: Multiple subplots for comprehensive analysis
- **Real-time price updates**: Stay on top of market movements

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

#### Option 1: Docker (Recommended)
Run the entire stack (Web App + Background Monitor) with a single command.

1. **Configure Environment**:
   - Copy `.env.example` to `.env` and add your Telegram API keys.
   - (Optional) Edit `config.yaml` to customize symbols and intervals.

2. **Run with Docker Compose**:
```bash
docker-compose up --build -d
```
- Web App: `http://localhost:8501`
- Monitor: Runs in background (check logs with `docker-compose logs -f monitor`)

#### Option 2: Local Python Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Run the application**
```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## 🎮 Usage

### Basic Workflow

1. **Navigate** (Sidebar):
   - Select **📊 Dashboard** for single-symbol analysis
   - Select **🔍 Multi-Screener** for bulk scanning
   - Select **🧪 Backtester** for strategy testing

2. **Configure Settings** (Sidebar):
   - **Global Settings**: Interval and Loopback apply to all views
   - **Strategy Filters**: Enable Trend, Volume, ADX, or MACD filters to refine your analysis

3. **Dashboard Analysis**:
   - Enter symbol (e.g., `BTCUSDT`)
   - Click "Analyze Market"
   - Review Charts, Metrics, and the **Trade Setup Card** with DCA levels

4. **Multi-Symbol Screener**:
   - Enter a comma-separated list of symbols
   - Click "Scan Market"
   - View a sorted table of high-confidence setups
   - **Continuous Monitor**: Information about the background Docker service is displayed here

5. **Backtesting**:
   - Configure capital, risk, and filters
   - Run backtest to validate your strategy before trading

6. **Configure Alerts**:
   - In the Sidebar, scroll to "🔔 Alerts Config"
   - Enable **Telegram Alerts**
   - Enter your Bot Token and Chat ID
   - **Manual Mode**: Alerts sent when you click "Scan Market"
   - **Continuous Mode**: The background Docker monitor uses settings from `config.yaml` to send alerts automatically

## 📁 Project Structure

```
perosnal_bybit_crypto_analyzer/
│
├── app.py                 # Main Streamlit application (Sidebar Navigation)
├── backtester.py          # Backtesting engine and logic
├── data_loader.py         # Bybit API data fetching functions
├── indicators.py          # Technical indicators and strategy logic
├── screener.py            # Multi-symbol market screener
├── alerts.py              # Telegram notification system
├── monitor.py             # Standalone background monitor script (Dockerized)
├── config.py              # Configuration loader
├── config.yaml            # User settings (Symbols, Interval)
├── .env.example           # Example secrets file (Telegram keys)
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker services orchestration
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Configuration

### Supported Symbols
Any Bybit USDT perpetual futures pair (e.g., `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`)

### Timeframes
- `5m` - 5 minutes
- `15m` - 15 minutes
- `1h` - 1 hour
- `2h` - 2 hours
- `4h` - 4 hours
- `1d` - 1 day

### Strategy Logic

**Long Signals**:
- EMA 9 crosses above EMA 21
- RSI < 35 (Oversold - Relaxed)

**Short Signals**:
- EMA 9 crosses below EMA 21
- RSI > 65 (Overbought - Relaxed)

**Confidence Factors** (0-100%):
- Trend Alignment (20%): Price vs SMA 200
- Momentum (20%): RSI room to move
- Volume (10%): Above average volume
- Pattern (15%): Candlestick pattern confluence
- Support/Resistance (20%): Near key levels
- FVG (15%): Inside Fair Value Gap

## 🛠️ Technical Details

### Dependencies
- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `plotly` - Interactive charting
- `pybit` - Bybit API wrapper
- `numpy` - Numerical computations
- `PyYAML` - Configuration parsing
- `python-dotenv` - Environment variable management

### API Usage
This app uses **public Bybit API endpoints** and does not require API keys for basic functionality. All data is fetched in real-time from Bybit's public market data.

## ⚠️ Disclaimer

**This tool is for educational and informational purposes only.**

- Not financial advice
- Past performance does not guarantee future results
- Cryptocurrency trading carries significant risk
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- The confidence score is algorithmic and should not be the sole basis for trading decisions

## 🔮 Roadmap

Planned features for future releases:

- [x] **Backtesting Engine**: Test strategies on historical data with win rate and profit factor
- [x] **Multi-Symbol Screener**: Scan multiple coins simultaneously for high-confidence setups with DCA levels
- [x] **Alerts System**: Telegram notifications for trade signals
- [x] **Docker Support**: Full containerization for easy deployment
- [ ] **AI Market Summary**: LLM-powered market analysis and insights
- [ ] **Portfolio Tracking**: Monitor your actual Bybit positions (requires API keys)
- [ ] **Custom Strategy Builder**: Create and test your own trading rules

## 📝 License

MIT License - feel free to use and modify for your own projects.

**Happy Trading! 📈**
