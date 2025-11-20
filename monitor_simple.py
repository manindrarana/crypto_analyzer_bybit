import time
import logging
import config
import screener
import alerts
import database
import indicators
from datetime import datetime
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting Crypto Monitor Service with Database...")
    
    # Initialize database
    try:
        database.init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return
    
    # Load Config
    cfg = config.load_config()
    telegram_creds = config.get_telegram_creds()
    
    symbols = cfg.get('symbols', [])
    interval = cfg.get('interval', '1h')
    loopback = cfg.get('loopback', 200)
    use_closed_candles = cfg.get('use_closed_candles', True)
    freq_minutes = cfg.get('monitor_frequency_minutes', 15)
    
    logger.info(f"Loaded {len(symbols)} symbols. Interval: {interval}, Freq: {freq_minutes}m")
    
    while True:
        try:
            logger.info("🔍 Scanning market...")
            
            results_df = screener.scan_market(
                symbols, 
                interval, 
                loopback=loopback, 
                use_closed_candles=use_closed_candles
            )
            
            if not results_df.empty:
                logger.info(f"Found {len(results_df)} active setups.")
                
                for index, row in results_df.iterrows():
                    symbol = row['Symbol']
                    signal_type = row['Type']
                    entry_price = row['Entry']
                    
                    # Check for duplicate before processing
                    if database.is_duplicate_signal(symbol, signal_type, entry_price, hours=24):
                        logger.info(f"⏭️  Skipping duplicate signal: {symbol} {signal_type}")
                        continue
                    
                    # Extract setup details
                    setup = {
                        'Type': signal_type,
                        'Entry': entry_price,
                        'SL': row.get('SL'),
                        'TP': row.get('TP'),
                        'DCA_1': row.get('DCA_1'),
                        'DCA_2': row.get('DCA_2'),
                        'DCA_3': row.get('DCA_3')
                    }
                    
                    confluence_score = row.get('Confluence', 0)
                    confluence_reasons = []
                    
                    # Try to parse JSON reasons if stored
                    reasons_str = row.get('Reasons', '')
                    if isinstance(reasons_str, list):
                        confluence_reasons = reasons_str
                    elif isinstance(reasons_str, str) and reasons_str:
                        # Parse string representation
                        confluence_reasons = [r.strip() for r in reasons_str.split(',')]
                    
                    # Save signal to database
                    try:
                        signal_id = database.save_signal(
                            symbol=symbol,
                            timeframe=interval,
                            setup=setup,
                            confluence_score=confluence_score,
                            confluence_reasons=confluence_reasons,
                            chart_patterns=None  # Could extract from df if available
                        )
                        logger.info(f"💾 Signal saved to database (ID: {signal_id})")
                    except Exception as e:
                        logger.error(f"Failed to save signal to database: {e}")
                        signal_id = None
                    
                    # Format and send alert
                    msg = alerts.format_setup_message(row)
                    
                    # Send Telegram
                    if telegram_creds['token'] and telegram_creds['chat_id']:
                        success, err = alerts.send_telegram_message(
                            telegram_creds['token'], 
                            telegram_creds['chat_id'], 
                            msg
                        )
                        if success:
                            logger.info(f"✅ Telegram alert sent for {symbol}")
                            
                            # Update signal status to ALERTED
                            if signal_id:
                                try:
                                    database.update_signal_status(
                                        signal_id, 
                                        'ALERTED', 
                                        alerted_at=datetime.now()
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to update signal status: {e}")
                        else:
                            logger.error(f"❌ Telegram failed for {symbol}: {err}")
            else:
                logger.info("No active setups found.")
                
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            import traceback
            traceback.print_exc()
            
        logger.info(f"💤 Sleeping for {freq_minutes} minutes...")
        time.sleep(freq_minutes * 60)

if __name__ == "__main__":
    main()
