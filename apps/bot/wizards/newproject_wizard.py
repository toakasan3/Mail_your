"""
MailGuard OSS - New Project Wizard
Multi-step conversation for creating a new project
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import re

from core.config import settings
from core.db import create_project, get_project_by_slug, list_sender_emails

# States
NAME, SLUG, SENDER, CONFIRM = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the new project wizard."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return ConversationHandler.END
    
    # Check if there are senders available
    senders = await list_sender_emails()
    if not senders:
        await update.message.reply_text(
            "❌ No sender emails configured\\.\n\n"
            "Use /addemail to add a sender email first\\.",
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📁 *Create New Project*\n\n"
        "Enter a name for your project:\n\n"
        "Use /cancel to abort\\.",
        parse_mode='MarkdownV2'
    )
    
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive project name."""
    name = update.message.text.strip()
    
    if len(name) > 100:
        await update.message.reply_text(
            "Name too long\\. Maximum 100 characters\\.",
            parse_mode='MarkdownV2'
        )
        return NAME
    
    context.user_data['project_name'] = name
    
    await update.message.reply_text(
        f"Project name: *{name}*\n\n"
        f"Enter a URL\\-friendly slug \\(lowercase letters, numbers, hyphens\\):\n"
        f"Example: `my\\-awesome\\-app`",
        parse_mode='MarkdownV2'
    )
    
    return SLUG


async def receive_slug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate project slug."""
    slug = update.message.text.strip().lower()
    
    # Validate slug format
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', slug):
        await update.message.reply_text(
            "Invalid slug\\. Use only lowercase letters, numbers, and hyphens\\.\n"
            "Must start and end with a letter or number\\.",
            parse_mode='MarkdownV2'
        )
        return SLUG
    
    # Check if slug already exists
    existing = await get_project_by_slug(slug)
    if existing:
        await update.message.reply_text(
            "This slug is already taken\\. Please choose another\\.",
            parse_mode='MarkdownV2'
        )
        return SLUG
    
    context.user_data['project_slug'] = slug
    
    # Show available senders
    senders = await list_sender_emails()
    
    message = f"Slug: `{slug}`\n\nSelect a sender email:\n\n"
    for i, sender in enumerate(senders, 1):
        status = "✅" if sender['is_verified'] else "⚠️"
        message += f"{i}\\. {status} `{sender['email_address']}`\n"
    
    message += "\nReply with the number\\."
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')
    
    # Store senders for selection
    context.user_data['available_senders'] = senders
    
    return SENDER


async def receive_sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive sender selection."""
    text = update.message.text.strip()
    
    senders = context.user_data.get('available_senders', [])
    
    try:
        index = int(text) - 1
        if index < 0 or index >= len(senders):
            raise ValueError()
        selected_sender = senders[index]
    except ValueError:
        await update.message.reply_text(
            "Invalid selection\\. Reply with a number from the list\\.",
            parse_mode='MarkdownV2'
        )
        return SENDER
    
    context.user_data['selected_sender'] = selected_sender
    
    # Show confirmation
    name = context.user_data['project_name']
    slug = context.user_data['project_slug']
    
    await update.message.reply_text(
        f"📁 *Confirm Project*\n\n"
        f"Name: *{name}*\n"
        f"Slug: `{slug}`\n"
        f"Sender: `{selected_sender['email_address']}`\n\n"
        f"*Default Settings:*\n"
        f"• OTP Length: 6 digits\n"
        f"• OTP Expiry: 10 minutes\n"
        f"• Max Attempts: 5\n"
        f"• Rate Limit: 10/hour\n\n"
        f"Reply 'yes' to create the project, or 'no' to cancel\\.",
        parse_mode='MarkdownV2'
    )
    
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and create the project."""
    text = update.message.text.strip().lower()
    
    if text not in ['yes', 'y']:
        await update.message.reply_text(
            "Cancelled\\. Use /newproject to start over\\.",
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    name = context.user_data['project_name']
    slug = context.user_data['project_slug']
    sender = context.user_data['selected_sender']
    
    try:
        project = await create_project(
            name=name,
            slug=slug,
            sender_email_id=sender['id']
        )
        
        await update.message.reply_text(
            f"✅ *Project Created*\n\n"
            f"Name: *{name}*\n"
            f"Slug: `{slug}`\n"
            f"ID: `{project['id'][:8]}...`\n\n"
            f"Use /genkey `{slug}` to create an API key\\.",
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to create project: `{str(e)}`",
            parse_mode='MarkdownV2'
        )
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the wizard."""
    await update.message.reply_text(
        "Cancelled\\.",
        parse_mode='MarkdownV2'
    )
    return ConversationHandler.END