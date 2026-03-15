"""
MailGuard OSS - Add Email Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addemail command - starts the add email wizard."""
    # This is handled by the ConversationHandler in main.py
    pass