"""
MailGuard OSS - Generate API Key Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings
from core.crypto import generate_api_key, hash_api_key, get_key_prefix
from core.db import list_projects, create_api_key, list_api_keys


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /genkey command - generate a new API key."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        # List available projects
        projects = await list_projects()
        if not projects:
            await update.message.reply_text(
                "No projects configured\\. Use /newproject to create one first\\.",
                parse_mode='MarkdownV2'
            )
            return
        
        message = "📁 *Available Projects*\n\n"
        for p in projects:
            message += f"• `{p['slug']}` \\- {p['name']}\n"
        
        message += "\nUsage: `/genkey <project_slug> [label] [--test]`"
        await update.message.reply_text(message, parse_mode='MarkdownV2')
        return
    
    project_slug = context.args[0]
    label = None
    is_sandbox = False
    
    # Parse arguments
    for arg in context.args[1:]:
        if arg == '--test':
            is_sandbox = True
        else:
            label = arg
    
    # Find project
    from core.db import get_project_by_slug
    project = await get_project_by_slug(project_slug)
    
    if not project:
        await update.message.reply_text(
            "Project not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Generate API key
    api_key = generate_api_key(is_sandbox)
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key)
    
    # Store in database
    key_record = await create_api_key(
        project_id=project['id'],
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=label,
        is_sandbox=is_sandbox
    )
    
    key_type = "🧪 Sandbox" if is_sandbox else "🔑 Live"
    
    # Send the key (only time it's shown in plaintext!)
    await update.message.reply_text(
        f"{key_type} API Key Generated\n\n"
        f"Project: `{project['slug']}`\n"
        f"Key: `{api_key}`\n\n"
        f"⚠️ *This is the only time this key will be shown\\!* "
        f"Store it securely\\.",
        parse_mode='MarkdownV2'
    )