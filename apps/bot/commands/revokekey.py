"""
MailGuard OSS - Revoke API Key Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings
from core.db import list_api_keys, revoke_api_key, list_projects


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /revokekey command - revoke an API key."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/revokekey <key_id>`\n\n"
            "Use /keys to find the key ID\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    key_id = context.args[0]
    
    # Find key across all projects
    projects = await list_projects()
    key_found = None
    
    for project in projects:
        keys = await list_api_keys(project['id'])
        for k in keys:
            if k['id'].startswith(key_id):
                key_found = k
                break
        if key_found:
            break
    
    if not key_found:
        await update.message.reply_text(
            "Key not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    if not key_found['is_active']:
        await update.message.reply_text(
            "This key is already revoked\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Revoke the key
    await revoke_api_key(key_found['id'])
    
    await update.message.reply_text(
        f"✅ API key `{key_found['key_prefix']}...` has been revoked\\.",
        parse_mode='MarkdownV2'
    )