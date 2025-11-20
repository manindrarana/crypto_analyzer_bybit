import time
import logging
import config
import screener
import alerts
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
    logger.info("🚀 Starting Crypto Monitor Service...")
    
    # Load Config
    cfg = config.load_config()
    telegram_creds = config.get_telegram_creds()
    email_creds = config.get_email_creds()
    
    symbols = cfg.get('symbols', [])
    interval = cfg.get('interval', '1h')
    loopback = cfg.get('loopback', 200)
    use_closed_candles = cfg.get('use_closed_candles', True)
    freq_minutes = cfg.get('monitor_frequency_minutes', 15)
    
    logger.info(f"Loaded {len(symbols)} symbols. Interval: {interval}, Freq: {freq_minutes}m")
    
    alerted_setups = set()
    
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
                    setup_id = (row['Symbol'], row['Type'], row['Entry'])
                    
                    if setup_id not in alerted_setups:
                        msg = alerts.format_setup_message(row)
                        
                        # Send Telegram
                        if telegram_creds['token'] and telegram_creds['chat_id']:
                            success, err = alerts.send_telegram_message(
                                telegram_creds['token'], 
                                telegram_creds['chat_id'], 
                                msg
                            )
                            if success:
                                logger.info(f"✅ Telegram alert sent for {row['Symbol']}")
                            else:
                                logger.error(f"❌ Telegram failed for {row['Symbol']}: {err}")
                                
                        # Send Email
                        if email_creds['sender'] and email_creds['password'] and email_creds['receiver']:
                            subject = f"Trade Setup: {row['Symbol']} ({row['Type']})"
                            success, err = alerts.send_email(
                                "smtp.gmail.com", 587, 
                                email_creds['sender'], 
                                email_creds['password'], 
                                email_creds['receiver'], 
                                subject, 
                                msg
                            )
                            if success:
                                logger.info(f"✅ Email alert sent for {row['Symbol']}")
                            else:
                                logger.error(f"❌ Email failed for {row['Symbol']}: {err}")
                        
                        alerted_setups.add(setup_id)
            else:
                logger.info("No active setups found.")
                
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            
        logger.info(f"💤 Sleeping for {freq_minutes} minutes...")
        time.sleep(freq_minutes * 60)

if __name__ == "__main__":
    main()
