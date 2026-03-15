"""
MailGuard OSS - Start Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.effective_user.id
    
    # Admin gate
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return  # Silent rejection
    
    welcome_message = (
        "🛡️ *Welcome to MailGuard OSS\\!*\n\n"
        "I'm your OTP and email automation server admin bot\\.\n\n"
        "*Available Commands:*\n\n"
        "📧 *Sender Management:*\n"
        "/addemail – Add a new sender email\n"
        "/senders – List all sender emails\n"
        "/testsender – Test a sender email\n"
        "/removesender – Remove a sender\n\n"
        "📁 *Project Management:*\n"
        "/newproject – Create a new project\n"
        "/projects – List all projects\n\n"
        "🔑 *API Keys:*\n"
        "/genkey – Generate a new API key\n"
        "/keys – List API keys\n"
        "/revokekey – Revoke an API key\n"
        "/testkey – Test an API key\n\n"
        "📊 *Monitoring:*\n"
        "/logs – View email logs\n"
        "/stats – View statistics\n\n"
        "Use /help \\<command\\> for more info\\."
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='MarkdownV2'
    )