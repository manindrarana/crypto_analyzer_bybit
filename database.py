import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

# Database file location
DB_PATH = Path(__file__).parent / 'data' / 'trading.db'

def init_database():
    """Initialize the database with all required tables."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create signals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            dca_1 REAL,
            dca_2 REAL,
            dca_3 REAL,
            confluence_score INTEGER,
            confluence_reasons TEXT,
            chart_patterns TEXT,
            status TEXT DEFAULT 'NEW',
            alerted_at DATETIME
        )
    ''')
    
    # Create trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            symbol TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            entry_time DATETIME,
            entry_price REAL,
            exit_time DATETIME,
            exit_price REAL,
            quantity REAL,
            pnl REAL,
            pnl_percent REAL,
            outcome TEXT,
            notes TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        )
    ''')
    
    # Create backtest_results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            timeframe TEXT,
            start_date DATETIME,
            end_date DATETIME,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            win_rate REAL,
            total_pnl REAL,
            max_drawdown REAL,
            parameters TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def save_signal(symbol, timeframe, setup, confluence_score, confluence_reasons, chart_patterns=None):
    """
    Save a trading signal to the database.
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Candle timeframe
        setup: Dict with Entry, SL, TP, DCA levels, Type
        confluence_score: Score 0-100
        confluence_reasons: List of reason strings
        chart_patterns: List of detected patterns
    
    Returns:
        signal_id: ID of saved signal
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO signals (
            symbol, timeframe, signal_type, entry_price, stop_loss, take_profit,
            dca_1, dca_2, dca_3, confluence_score, confluence_reasons, chart_patterns
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        symbol,
        timeframe,
        setup['Type'],
        setup['Entry'],
        setup.get('SL'),
        setup.get('TP'),
        setup.get('DCA_1'),
        setup.get('DCA_2'),
        setup.get('DCA_3'),
        confluence_score,
        json.dumps(confluence_reasons),
        json.dumps(chart_patterns) if chart_patterns else None
    ))
    
    signal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return signal_id


def is_duplicate_signal(symbol, signal_type, entry_price, hours=24):
    """
    Check if a similar signal already exists in the last N hours.
    
    Args:
        symbol: Trading pair
        signal_type: LONG or SHORT
        entry_price: Entry price
        hours: Lookback period in hours
    
    Returns:
        bool: True if duplicate exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    price_tolerance = 0.01  # 1% price difference
    
    cursor.execute('''
        SELECT COUNT(*) FROM signals
        WHERE symbol = ?
        AND signal_type = ?
        AND timestamp > ?
        AND ABS(entry_price - ?) / entry_price < ?
    ''', (symbol, signal_type, cutoff_time, entry_price, price_tolerance))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0


def update_signal_status(signal_id, status, alerted_at=None):
    """
    Update signal status.
    
    Args:
        signal_id: Signal ID
        status: NEW, ALERTED, TAKEN, IGNORED
        alerted_at: Timestamp when alert was sent
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if alerted_at:
        cursor.execute('''
            UPDATE signals 
            SET status = ?, alerted_at = ?
            WHERE id = ?
        ''', (status, alerted_at, signal_id))
    else:
        cursor.execute('''
            UPDATE signals 
            SET status = ?
            WHERE id = ?
        ''', (status, signal_id))
    
    conn.commit()
    conn.close()


def get_signals(limit=100, symbol=None, status=None, min_confluence=None, days=None):
    """
    Retrieve signals from database with filters.
    
    Args:
        limit: Max number of results
        symbol: Filter by symbol
        status: Filter by status
        min_confluence: Minimum confluence score
        days: Only signals from last N days
    
    Returns:
        List of signal dicts
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM signals WHERE 1=1'
    params = []
    
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if min_confluence is not None:
        query += ' AND confluence_score >= ?'
        params.append(min_confluence)
    
    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        query += ' AND timestamp > ?'
        params.append(cutoff)
    
    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    signals = []
    for row in rows:
        signal = dict(row)
        # Parse JSON fields
        if signal['confluence_reasons']:
            signal['confluence_reasons'] = json.loads(signal['confluence_reasons'])
        if signal['chart_patterns']:
            signal['chart_patterns'] = json.loads(signal['chart_patterns'])
        signals.append(signal)
    
    conn.close()
    return signals


def save_trade(symbol, trade_type, entry_price, entry_time, exit_price=None, 
               exit_time=None, quantity=None, notes=None, signal_id=None):
    """
    Save a trade to the database.
    
    Args:
        symbol: Trading pair
        trade_type: LONG or SHORT
        entry_price: Entry price
        entry_time: Entry datetime
        exit_price: Exit price (optional)
        exit_time: Exit datetime (optional)
        quantity: Trade size (optional)
        notes: User notes (optional)
        signal_id: Link to signal (optional)
    
    Returns:
        trade_id: ID of saved trade
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculate PnL if exit exists
    pnl = None
    pnl_percent = None
    outcome = None
    
    if exit_price and entry_price and quantity:
        if trade_type == 'LONG':
            pnl = (exit_price - entry_price) * quantity
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl = (entry_price - exit_price) * quantity
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        if pnl > 0:
            outcome = 'WIN'
        elif pnl < 0:
            outcome = 'LOSS'
        else:
            outcome = 'BREAKEVEN'
    
    cursor.execute('''
        INSERT INTO trades (
            signal_id, symbol, trade_type, entry_time, entry_price,
            exit_time, exit_price, quantity, pnl, pnl_percent, outcome, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        signal_id, symbol, trade_type, entry_time, entry_price,
        exit_time, exit_price, quantity, pnl, pnl_percent, outcome, notes
    ))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return trade_id


def update_trade_exit(trade_id, exit_price, exit_time, quantity=None):
    """
    Update trade with exit information and calculate PnL.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get trade details
    cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
    trade = dict(cursor.fetchone())
    
    # Use provided quantity or existing
    qty = quantity or trade['quantity'] or 1.0
    
    # Calculate PnL
    if trade['trade_type'] == 'LONG':
        pnl = (exit_price - trade['entry_price']) * qty
        pnl_percent = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
    else:  # SHORT
        pnl = (trade['entry_price'] - exit_price) * qty
        pnl_percent = ((trade['entry_price'] - exit_price) / trade['entry_price']) * 100
    
    outcome = 'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BREAKEVEN')
    
    cursor.execute('''
        UPDATE trades
        SET exit_price = ?, exit_time = ?, quantity = ?, 
            pnl = ?, pnl_percent = ?, outcome = ?
        WHERE id = ?
    ''', (exit_price, exit_time, qty, pnl, pnl_percent, outcome, trade_id))
    
    conn.commit()
    conn.close()


def get_trades(limit=100, symbol=None, outcome=None, days=None):
    """
    Retrieve trades from database with filters.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM trades WHERE 1=1'
    params = []
    
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    
    if outcome:
        query += ' AND outcome = ?'
        params.append(outcome)
    
    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        query += ' AND entry_time > ?'
        params.append(cutoff)
    
    query += ' ORDER BY entry_time DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    trades = [dict(row) for row in rows]
    conn.close()
    
    return trades


def save_backtest_result(symbol, timeframe, start_date, end_date, metrics, parameters):
    """
    Save backtest results to database.
    
    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        start_date: Backtest start
        end_date: Backtest end
        metrics: Dict with total_trades, win_rate, etc.
        parameters: Dict with filter settings
    
    Returns:
        result_id
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO backtest_results (
            symbol, timeframe, start_date, end_date, total_trades,
            winning_trades, losing_trades, win_rate, total_pnl, max_drawdown, parameters
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        symbol, timeframe, start_date, end_date,
        metrics.get('total_trades', 0),
        metrics.get('winning_trades', 0),
        metrics.get('losing_trades', 0),
        metrics.get('win_rate', 0),
        metrics.get('total_pnl', 0),
        metrics.get('max_drawdown', 0),
        json.dumps(parameters)
    ))
    
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return result_id


# Initialize database on module import
init_database()
