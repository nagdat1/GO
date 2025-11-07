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

# قائمة Chat IDs للمجموعات - يمكن إضافة أي عدد من المجموعات
# List of Chat IDs for groups - you can add any number of groups
# ═══════════════════════════════════════════════════════════════════════════
# 📝 كيفية إضافة مجموعة جديدة:
# 1. أضف Chat ID للمجموعة في القائمة أدناه
# 2. يمكن إضافة Chat IDs من متغيرات البيئة أو مباشرة في القائمة
# 3. مثال: TELEGRAM_CHAT_IDS = ['-1003214062626', '-1001234567890', '-1009876543210']
# ═══════════════════════════════════════════════════════════════════════════

# الحصول على Chat IDs من متغير البيئة (مفصولة بفواصل) أو استخدام القائمة الافتراضية
_chat_ids_env = os.getenv('TELEGRAM_CHAT_IDS', '')
if _chat_ids_env:
    # إذا كان متغير البيئة موجود، استخدمه (مفصول بفواصل)
    TELEGRAM_CHAT_IDS = [cid.strip() for cid in _chat_ids_env.split(',') if cid.strip()]
else:
    # القائمة الافتراضية - يمكنك إضافة مجموعات هنا مباشرة
    TELEGRAM_CHAT_IDS = [
        '-1003214062626',  # Crypto Insight (المجموعة الأساسية)
        '-5066290933',  
        # '-1009876543210',  # مثال: مجموعة ثالثة
    ]

# للحفاظ على التوافق مع الكود القديم (اختياري)
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_IDS[0] if TELEGRAM_CHAT_IDS else None

# Webhook Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')  # Optional: for security
WEBHOOK_PORT = int(os.getenv('PORT', 5000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # URL للبوت (اختياري)

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
        "telegram_chat_ids": TELEGRAM_CHAT_IDS,
        "chat_ids_count": len(TELEGRAM_CHAT_IDS),
        "all_set": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS)
    }
    return status

