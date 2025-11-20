"""
Analytics Module
Provides performance analytics and insights.
"""

import database
import pandas as pd
from collections import defaultdict


def get_overall_stats():
    """
    Get overall system statistics.
    
    Returns:
        Dict with:
        - total_signals
        - signals_alerted
        - signals_taken
        - total_trades
        - win_rate
        - total_pnl
        - best_symbol
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Signal stats
    cursor.execute('SELECT COUNT(*) FROM signals')
    stats['total_signals'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "ALERTED"')
    stats['signals_alerted'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "TAKEN"')
    stats['signals_taken'] = cursor.fetchone()[0]
    
    # Trade stats
    cursor.execute('SELECT COUNT(*) FROM trades WHERE exit_price IS NOT NULL')
    stats['total_trades'] = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN outcome = "WIN" THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM trades 
        WHERE exit_price IS NOT NULL
    ''')
    result = cursor.fetchone()
    stats['win_rate'] = result[0] if result[0] else 0
    
    cursor.execute('SELECT SUM(pnl) FROM trades WHERE exit_price IS NOT NULL')
    result = cursor.fetchone()
    stats['total_pnl'] = result[0] if result[0] else 0
    
    # Best performing symbol
    cursor.execute('''
        SELECT symbol, SUM(pnl) as total_pnl
        FROM trades
        WHERE exit_price IS NOT NULL
        GROUP BY symbol
        ORDER BY total_pnl DESC
        LIMIT 1
    ''')
    result = cursor.fetchone()
    stats['best_symbol'] = result[0] if result else 'N/A'
    
    conn.close()
    return stats


def get_win_rate_by_symbol():
    """
    Calculate win rate for each symbol.
    
    Returns:
        List of dicts with symbol, win_rate, total_trades
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            symbol,
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome = "WIN" THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = "WIN" THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
            SUM(pnl) as total_pnl
        FROM trades
        WHERE exit_price IS NOT NULL
        GROUP BY symbol
        ORDER BY total_pnl DESC
    ''')
    
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        results.append({
            'symbol': row[0],
            'total_trades': row[1],
            'wins': row[2],
            'win_rate': row[3],
            'total_pnl': row[4]
        })
    
    conn.close()
    return results


def get_pattern_performance():
    """
    Analyze performance of different chart patterns.
    
    Returns:
        Dict mapping pattern names to performance stats
    """
    signals = database.get_signals(limit=1000)
    
    pattern_stats = defaultdict(lambda: {
        'count': 0,
        'avg_confluence': 0,
        'total_confluence': 0
    })
    
    for signal in signals:
        patterns = signal.get('chart_patterns') or []
        confluence = signal.get('confluence_score', 0)
        
        for pattern in patterns:
            if isinstance(pattern, dict):
                pattern_name = pattern.get('type', 'Unknown')
            else:
                pattern_name = str(pattern)
            
            pattern_stats[pattern_name]['count'] += 1
            pattern_stats[pattern_name]['total_confluence'] += confluence
    
    # Calculate averages
    for pattern in pattern_stats:
        count = pattern_stats[pattern]['count']
        total = pattern_stats[pattern]['total_confluence']
        pattern_stats[pattern]['avg_confluence'] = total / count if count > 0 else 0
    
    # Convert to sorted list
    result = []
    for pattern, stats in pattern_stats.items():
        result.append({
            'pattern': pattern,
            'count': stats['count'],
            'avg_confluence': stats['avg_confluence']
        })
    
    result.sort(key=lambda x: x['count'], reverse=True)
    return result


def get_confluence_effectiveness():
    """
    Analyze signal effectiveness by confluence score ranges.
    
    Returns:
        List of dicts with score_range, signal_count, avg_effectiveness
    """
    signals = database.get_signals(limit=1000)
    
    ranges = {
        '60-70%': {'count': 0, 'scores': []},
        '70-80%': {'count': 0, 'scores': []},
        '80-90%': {'count': 0, 'scores': []},
        '90-100%': {'count': 0, 'scores': []}
    }
    
    for signal in signals:
        score = signal.get('confluence_score', 0)
        
        if 60 <= score < 70:
            ranges['60-70%']['count'] += 1
            ranges['60-70%']['scores'].append(score)
        elif 70 <= score < 80:
            ranges['70-80%']['count'] += 1
            ranges['70-80%']['scores'].append(score)
        elif 80 <= score < 90:
            ranges['80-90%']['count'] += 1
            ranges['80-90%']['scores'].append(score)
        elif 90 <= score <= 100:
            ranges['90-100%']['count'] += 1
            ranges['90-100%']['scores'].append(score)
    
    result = []
    for range_name, data in ranges.items():
        result.append({
            'range': range_name,
            'count': data['count'],
            'avg_score': sum(data['scores']) / len(data['scores']) if data['scores'] else 0
        })
    
    return result


def generate_equity_curve(days=30):
    """
    Generate equity curve data.
    
    Args:
        days: Number of days to include
    
    Returns:
        DataFrame with Date and Cumulative PnL
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    
    query = '''
        SELECT DATE(exit_time) as date, SUM(pnl) as daily_pnl
        FROM trades
        WHERE exit_price IS NOT NULL
        AND exit_time > datetime("now", "-{} days")
        GROUP BY DATE(exit_time)
        ORDER BY date ASC
    '''.format(days)
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) > 0:
        # Calculate cumulative PnL
        df['cumulative_pnl'] = df['daily_pnl'].cumsum()
    else:
        # Return empty dataframe with correct columns
        df = pd.DataFrame(columns=['date', 'daily_pnl', 'cumulative_pnl'])
    
    return df


def get_signal_to_trade_conversion():
    """
    Calculate how many signals led to actual trades.
    
    Returns:
        Dict with conversion stats
    """
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "ALERTED"')
    alerted = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM signals WHERE status = "TAKEN"')
    taken = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM trades WHERE signal_id IS NOT NULL')
    trades_from_signals = cursor.fetchone()[0]
    
    conn.close()
    
    conversion_rate = (taken / alerted * 100) if alerted > 0 else 0
    
    return {
        'signals_alerted': alerted,
        'signals_taken': taken,
        'trades_from_signals': trades_from_signals,
        'conversion_rate': conversion_rate
    }


def get_top_confluence_reasons():
    """
    Find which confluence factors appear most in successful setups.
    
    Returns:
        List of most common confluence reasons
    """
    signals = database.get_signals(limit=500, min_confluence=70)
    
    reason_counts = defaultdict(int)
    
    for signal in signals:
        reasons = signal.get('confluence_reasons', [])
        for reason in reasons:
            reason_counts[reason] += 1
    
    # Sort by frequency
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    
    return [{'reason': r[0], 'count': r[1]} for r in sorted_reasons[:10]]
