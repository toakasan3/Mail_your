"""
MailGuard OSS - Projects Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings
from core.db import list_projects, get_project, get_project_by_slug, update_project


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projects command - list all projects."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    projects = await list_projects(active_only=False)
    
    if not projects:
        await update.message.reply_text(
            "No projects configured\\. Use /newproject to create one\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    message = "📁 *Projects*\n\n"
    
    for project in projects:
        status = "✅" if project['is_active'] else "⚠️"
        sender = project.get('sender_emails')
        sender_email = sender['email_address'] if sender else "Not assigned"
        
        message += (
            f"{status} *{project['name']}* \\(`{project['slug']}`\\)\n"
            f"   Sender: {sender_email}\n"
            f"   OTP Length: {project.get('otp_length', 6)}\n"
            f"   Expiry: {project.get('otp_expiry_seconds', 600)}s\n"
            f"   Rate Limit: {project.get('rate_limit_per_hour', 10)}/hour\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')


async def get_project_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get detailed info about a specific project."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/projects <slug>`",
            parse_mode='MarkdownV2'
        )
        return
    
    slug = context.args[0]
    project = await get_project_by_slug(slug)
    
    if not project:
        await update.message.reply_text(
            "Project not found\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    sender = project.get('sender_emails')
    
    message = (
        f"📁 *{project['name']}*\n\n"
        f"Slug: `{project['slug']}`\n"
        f"Status: {'Active' if project['is_active'] else 'Inactive'}\n\n"
        f"*Settings:*\n"
        f"• OTP Length: {project.get('otp_length', 6)}\n"
        f"• OTP Expiry: {project.get('otp_expiry_seconds', 600)}s\n"
        f"• Max Attempts: {project.get('otp_max_attempts', 5)}\n"
        f"• Rate Limit: {project.get('rate_limit_per_hour', 10)}/hour\n\n"
        f"*Sender:*\n"
        f"• Email: {sender['email_address'] if sender else 'Not assigned'}\n"
        f"• Provider: {sender['provider'] if sender else 'N/A'}\n"
    )
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')