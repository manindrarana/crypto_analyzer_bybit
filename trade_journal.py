"""
Trade Journal Module
Provides high-level functions for trade tracking and statistics.
"""

import database
from datetime import datetime


def log_trade_entry(symbol, trade_type, entry_price, quantity=None, notes=None, signal_id=None):
    """
    Log a new trade entry.
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        trade_type: LONG or SHORT
        entry_price: Entry price
        quantity: Position size (optional)
        notes: User notes (optional)
        signal_id: Link to signal that generated this trade (optional)
    
    Returns:
        trade_id: ID of the created trade
    """
    entry_time = datetime.now()
    
    trade_id = database.save_trade(
        symbol=symbol,
        trade_type=trade_type,
        entry_price=entry_price,
        entry_time=entry_time,
        quantity=quantity,
        notes=notes,
        signal_id=signal_id
    )
    
    return trade_id


def log_trade_exit(trade_id, exit_price, quantity=None):
    """
    Log trade exit and calculate PnL.
    
    Args:
        trade_id: ID of the trade to close
        exit_price: Exit price
        quantity: Position size if not set on entry
    
    Returns:
        Updated trade dict with PnL
    """
    exit_time = datetime.now()
    
    database.update_trade_exit(
        trade_id=trade_id,
        exit_price=exit_price,
        exit_time=exit_time,
        quantity=quantity
    )
    
    # Return updated trade
    trades = database.get_trades(limit=1)
    return trades[0] if trades else None


def get_open_trades(symbol=None):
    """
    Get all trades without exit prices (still open).
    
    Args:
        symbol: Filter by symbol (optional)
    
    Returns:
        List of open trade dicts
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM trades WHERE exit_price IS NULL'
    params = []
    
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    
    query += ' ORDER BY entry_time DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    trades = [dict(row) for row in rows]
    conn.close()
    
    return trades


def get_closed_trades(symbol=None, limit=100):
    """
    Get all closed trades with PnL.
    
    Args:
        symbol: Filter by symbol (optional)
        limit: Max results
    
    Returns:
        List of closed trade dicts
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM trades WHERE exit_price IS NOT NULL'
    params = []
    
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    
    query += ' ORDER BY exit_time DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    trades = [dict(row) for row in rows]
    conn.close()
    
    return trades


def get_trade_statistics(symbol=None, days=None):
    """
    Calculate comprehensive trade statistics.
    
    Args:
        symbol: Filter by symbol (optional)
        days: Only trades from last N days (optional)
    
    Returns:
        Dict with statistics:
        - total_trades
        - open_trades
        - closed_trades
        - winning_trades
        - losing_trades
        - win_rate
        - total_pnl
        - avg_win
        - avg_loss
        - profit_factor
        - largest_win
        - largest_loss
    """
    # Get closed trades
    trades = database.get_trades(symbol=symbol, days=days)
    closed_trades = [t for t in trades if t['exit_price'] is not None]
    open_trades = [t for t in trades if t['exit_price'] is None]
    
    stats = {
        'total_trades': len(trades),
        'open_trades': len(open_trades),
        'closed_trades': len(closed_trades),
        'winning_trades': 0,
        'losing_trades': 0,
        'breakeven_trades': 0,
        'win_rate': 0,
        'total_pnl': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'profit_factor': 0,
        'largest_win': 0,
        'largest_loss': 0,
        'avg_win_percent': 0,
        'avg_loss_percent': 0
    }
    
    if not closed_trades:
        return stats
    
    wins = []
    losses = []
    
    for trade in closed_trades:
        if trade['outcome'] == 'WIN':
            stats['winning_trades'] += 1
            wins.append(trade['pnl'])
        elif trade['outcome'] == 'LOSS':
            stats['losing_trades'] += 1
            losses.append(trade['pnl'])
        else:
            stats['breakeven_trades'] += 1
        
        if trade['pnl']:
            stats['total_pnl'] += trade['pnl']
    
    # Calculate win rate
    if stats['closed_trades'] > 0:
        stats['win_rate'] = (stats['winning_trades'] / stats['closed_trades']) * 100
    
    # Calculate averages
    if wins:
        stats['avg_win'] = sum(wins) / len(wins)
        stats['largest_win'] = max(wins)
        win_percents = [t['pnl_percent'] for t in closed_trades if t['outcome'] == 'WIN' and t['pnl_percent']]
        if win_percents:
            stats['avg_win_percent'] = sum(win_percents) / len(win_percents)
    
    if losses:
        stats['avg_loss'] = sum(losses) / len(losses)
        stats['largest_loss'] = min(losses)
        loss_percents = [t['pnl_percent'] for t in closed_trades if t['outcome'] == 'LOSS' and t['pnl_percent']]
        if loss_percents:
            stats['avg_loss_percent'] = sum(loss_percents) / len(loss_percents)
    
    # Calculate profit factor
    if wins and losses:
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        if gross_loss > 0:
            stats['profit_factor'] = gross_profit / gross_loss
    
    return stats


def get_daily_pnl(symbol=None, days=30):
    """
    Get daily PnL for equity curve.
    
    Args:
        symbol: Filter by symbol (optional)
        days: Number of days to retrieve
    
    Returns:
        List of dicts with date and pnl
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT DATE(exit_time) as date, SUM(pnl) as daily_pnl
        FROM trades
        WHERE exit_price IS NOT NULL
    '''
    params = []
    
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    
    if days:
        query += ' AND exit_time > datetime("now", "-{} days")'.format(days)
    
    query += ' GROUP BY DATE(exit_time) ORDER BY date ASC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    result = [{'date': row[0], 'pnl': row[1]} for row in rows]
    conn.close()
    
    return result
