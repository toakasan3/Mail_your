"""
MailGuard OSS - Sender Email Commands
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional

from core.config import settings
from core.db import list_sender_emails, get_sender_email, delete_sender_email, update_sender_email
from core.crypto import mask_email


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /senders command - list all sender emails."""
    user_id = update.effective_user.id
    
    # Admin gate
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    senders = await list_sender_emails(active_only=False)
    
    if not senders:
        await update.message.reply_text(
            "No sender emails configured\\. Use /addemail to add one\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    message = "📧 *Sender Emails*\n\n"
    
    for sender in senders:
        status = "✅" if sender['is_active'] and sender['is_verified'] else "⚠️"
        daily_usage = f"{sender.get('emails_sent_today', 0)}/{sender.get('daily_limit', 500)}"
        
        message += (
            f"{status} `{sender['email_address']}`\n"
            f"   Provider: {sender['provider']}\n"
            f"   Daily: {daily_usage}\n"
            f"   ID: `{sender['id'][:8]}...`\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /testsender command - test a sender email."""
    from apps.bot.commands.testsender import handle as test_handle
    await test_handle(update, context)


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /removesender command."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/removesender <sender_id>`",
            parse_mode='MarkdownV2'
        )
        return
    
    sender_id = context.args[0]
    
    # Try to find by partial ID or email
    senders = await list_sender_emails(active_only=False)
    sender = None
    for s in senders:
        if s['id'].startswith(sender_id) or s['email_address'] == sender_id:
            sender = s
            break
    
    if not sender:
        await update.message.reply_text(
            "Sender not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Soft delete by setting is_active = False
    await update_sender_email(sender['id'], {'is_active': False})
    
    await update.message.reply_text(
        f"✅ Sender `{sender['email_address']}` has been removed\\.",
        parse_mode='MarkdownV2'
    )


async def assign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /assignsender command - assign sender to project."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/assignsender <project_slug> <sender_id>`",
            parse_mode='MarkdownV2'
        )
        return
    
    project_slug = context.args[0]
    sender_id = context.args[1]
    
    from core.db import get_project_by_slug
    
    project = await get_project_by_slug(project_slug)
    if not project:
        await update.message.reply_text(
            "Project not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    sender = await get_sender_email(sender_id)
    if not sender:
        # Try partial ID match
        senders = await list_sender_emails(active_only=False)
        for s in senders:
            if s['id'].startswith(sender_id):
                sender = s
                break
    
    if not sender:
        await update.message.reply_text(
            "Sender not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    from core.db import update_project
    await update_project(project['id'], {'sender_email_id': sender['id']})
    
    await update.message.reply_text(
        f"✅ Assigned `{sender['email_address']}` to project `{project_slug}`\\.",
        parse_mode='MarkdownV2'
    )


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /editsender command - edit sender settings."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/editsender <sender_id> <field> <value>`\n\n"
            "Fields: daily_limit, display_name",
            parse_mode='MarkdownV2'
        )
        return
    
    sender_id = context.args[0]
    field = context.args[1]
    value = ' '.join(context.args[2:])
    
    # Find sender
    sender = await get_sender_email(sender_id)
    if not sender:
        senders = await list_sender_emails(active_only=False)
        for s in senders:
            if s['id'].startswith(sender_id):
                sender = s
                break
    
    if not sender:
        await update.message.reply_text("Sender not found\\.", parse_mode='MarkdownV2')
        return
    
    # Update allowed fields
    allowed_fields = {'daily_limit': int, 'display_name': str}
    
    if field not in allowed_fields:
        await update.message.reply_text(
            f"Unknown field: {field}\nAllowed: daily_limit, display_name",
            parse_mode='MarkdownV2'
        )
        return
    
    try:
        typed_value = allowed_fields[field](value)
        await update_sender_email(sender['id'], {field: typed_value})
        await update.message.reply_text(
            f"✅ Updated {field} for `{sender['email_address']}`",
            parse_mode='MarkdownV2'
        )
    except ValueError:
        await update.message.reply_text(
            f"Invalid value for {field}",
            parse_mode='MarkdownV2'
        )