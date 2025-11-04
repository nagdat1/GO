"""
Configuration file for TradingView Webhook to Telegram Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
# ⚠️ WARNING: Never commit your tokens to git!
# Use environment variables in Railway or .env file for local development
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8361920962:AAFkWchaQStjaD09ayMI8VYm1vadr4p6zEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '8169000394')

# Webhook Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')  # Optional: for security
WEBHOOK_PORT = int(os.getenv('PORT', 5000))

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Validation
def validate_config():
    """Validate that required configuration is set"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True


def get_config_status():
    """Get configuration status without raising errors"""
    status = {
        "telegram_bot_token": bool(TELEGRAM_BOT_TOKEN),
        "telegram_chat_id": bool(TELEGRAM_CHAT_ID),
        "all_set": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    }
    return status

