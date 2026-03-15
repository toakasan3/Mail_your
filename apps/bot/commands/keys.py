"""
MailGuard OSS - List API Keys Command
"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

from core.config import settings
from core.db import list_api_keys, list_projects


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /keys command - list all API keys for a project."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        # List all projects with key counts
        projects = await list_projects()
        if not projects:
            await update.message.reply_text(
                "No projects configured\\.",
                parse_mode='MarkdownV2'
            )
            return
        
        message = "🔑 *API Keys by Project*\n\n"
        for p in projects:
            keys = await list_api_keys(p['id'])
            active_keys = len([k for k in keys if k['is_active']])
            message += f"• `{p['slug']}` \\- {active_keys} active keys\n"
        
        message += "\nUsage: `/keys <project_slug>`"
        await update.message.reply_text(message, parse_mode='MarkdownV2')
        return
    
    project_slug = context.args[0]
    
    from core.db import get_project_by_slug
    project = await get_project_by_slug(project_slug)
    
    if not project:
        await update.message.reply_text(
            "Project not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    keys = await list_api_keys(project['id'])
    
    if not keys:
        await update.message.reply_text(
            f"No API keys for project `{project_slug}`\\. Use /genkey to create one\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    message = f"🔑 *API Keys for `{project_slug}`*\n\n"
    
    for key in keys:
        status = "✅" if key['is_active'] else "❌"
        key_type = "🧪" if key['is_sandbox'] else "🔑"
        label = key.get('label', 'N/A')
        last_used = key.get('last_used_at')
        last_used_str = 'Never' if not last_used else datetime.fromisoformat(last_used.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        message += (
            f"{status} {key_type} `{key['key_prefix']}...`\n"
            f"   Label: {label}\n"
            f"   Last used: {last_used_str}\n"
            f"   ID: `{key['id'][:8]}...`\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')