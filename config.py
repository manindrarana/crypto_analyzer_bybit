import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config(config_path="config.yaml"):
    """
    Loads configuration from a YAML file and overrides with environment variables if present.
    """
    if not os.path.exists(config_path):
        # Return default config if file doesn't exist
        return {
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
            "interval": "1h",
            "loopback": 200,
            "monitor_frequency_minutes": 15
        }

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config

def get_telegram_creds():
    """
    Returns Telegram credentials from environment variables.
    """
    return {
        "token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID")
    }

def get_email_creds():
    """
    Returns Email credentials from environment variables.
    """
    return {
        "sender": os.getenv("EMAIL_SENDER"),
        "password": os.getenv("EMAIL_PASSWORD"),
        "receiver": os.getenv("EMAIL_RECEIVER")
    }
