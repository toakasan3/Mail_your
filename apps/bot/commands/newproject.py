"""
MailGuard OSS - New Project Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newproject command - starts the new project wizard."""
    # This is handled by the ConversationHandler in main.py
    pass