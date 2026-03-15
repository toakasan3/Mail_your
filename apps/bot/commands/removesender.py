"""
MailGuard OSS - Remove Sender Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /removesender command - delegates to senders.remove."""
    from apps.bot.commands.senders import remove
    await remove(update, context)