"""
MailGuard OSS - Telegram Bot Main Entry Point
Admin bot for managing MailGuard via Telegram
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

from core.config import settings
from apps.bot.commands import (
    start, addemail, senders, testsender, removesender,
    newproject, projects, genkey, keys, revokekey, testkey,
    logs, stats
)
from apps.bot.wizards import addemail_wizard, newproject_wizard

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Admin gate middleware
async def admin_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Middleware to ensure only the admin can use the bot.
    Returns True if the user is authorized, False otherwise.
    """
    user_id = update.effective_user.id if update.effective_user else None
    
    if user_id is None:
        return False
    
    # Check against configured admin UID
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        # Silent rejection - don't reveal bot exists
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return False
    
    return True


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre_checkout for payments (if needed)."""
    pass


def create_bot_app() -> Application:
    """Create and configure the bot application."""
    
    # Create application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handlers for wizards
    # Add email wizard
    addemail_handler = ConversationHandler(
        entry_points=[CommandHandler("addemail", addemail_wizard.start)],
        states={
            addemail_wizard.EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, addemail_wizard.receive_email)],
            addemail_wizard.PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, addemail_wizard.receive_password)],
            addemail_wizard.PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, addemail_wizard.receive_provider)],
            addemail_wizard.CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, addemail_wizard.confirm)],
        },
        fallbacks=[CommandHandler("cancel", addemail_wizard.cancel)],
    )
    
    # New project wizard
    newproject_handler = ConversationHandler(
        entry_points=[CommandHandler("newproject", newproject_wizard.start)],
        states={
            newproject_wizard.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, newproject_wizard.receive_name)],
            newproject_wizard.SLUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, newproject_wizard.receive_slug)],
            newproject_wizard.SENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, newproject_wizard.receive_sender)],
            newproject_wizard.CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, newproject_wizard.confirm)],
        },
        fallbacks=[CommandHandler("cancel", newproject_wizard.cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start.handle))
    application.add_handler(addemail_handler)
    application.add_handler(newproject_handler)
    
    # Simple command handlers
    application.add_handler(CommandHandler("senders", senders.handle))
    application.add_handler(CommandHandler("testsender", testsender.handle))
    application.add_handler(CommandHandler("removesender", removesender.handle))
    application.add_handler(CommandHandler("assignsender", senders.assign))
    application.add_handler(CommandHandler("editsender", senders.edit))
    
    application.add_handler(CommandHandler("projects", projects.handle))
    application.add_handler(CommandHandler("genkey", genkey.handle))
    application.add_handler(CommandHandler("keys", keys.handle))
    application.add_handler(CommandHandler("revokekey", revokekey.handle))
    application.add_handler(CommandHandler("testkey", testkey.handle))
    
    application.add_handler(CommandHandler("logs", logs.handle))
    application.add_handler(CommandHandler("stats", stats.handle))
    
    return application


def main():
    """Run the bot."""
    if not settings.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set")
        return
    
    if not settings.TELEGRAM_ADMIN_UID:
        print("WARNING: TELEGRAM_ADMIN_UID not set - bot will be accessible to anyone!")
    
    # Create application
    application = create_bot_app()
    
    # Initialize database and redis
    from core.db import init_db
    from core.redis_client import init_redis
    
    init_db(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    # Run bot
    print("✓ MailGuard Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()