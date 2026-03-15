"""
MailGuard OSS - Test Sender Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings
from core.db import list_sender_emails, get_sender_email
from core.crypto import decrypt


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /testsender command - test SMTP connection for a sender."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if not context.args:
        # List available senders
        senders = await list_sender_emails()
        if not senders:
            await update.message.reply_text(
                "No sender emails configured\\.",
                parse_mode='MarkdownV2'
            )
            return
        
        message = "📧 *Available Senders*\n\n"
        for s in senders:
            message += f"• `{s['email_address']}` \\(ID: `{s['id'][:8]}...`\\)\n"
        
        message += "\nUse `/testsender <id>` to test a sender\\."
        await update.message.reply_text(message, parse_mode='MarkdownV2')
        return
    
    sender_id = context.args[0]
    
    # Find sender
    sender = await get_sender_email(sender_id)
    if not sender:
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
    
    await update.message.reply_text(
        f"⏳ Testing connection to `{sender['smtp_host']}`...",
        parse_mode='MarkdownV2'
    )
    
    # Test SMTP connection
    try:
        import aiosmtplib
        
        smtp_password = decrypt(sender['app_password_enc'])
        
        await aiosmtplib.send(
            sender['email_address'],
            sender['email_address'],  # Send test to self
            hostname=sender['smtp_host'],
            port=sender['smtp_port'],
            username=sender['email_address'],
            password=smtp_password,
            start_tls=True,
            timeout=10
        )
        
        await update.message.reply_text(
            f"✅ *SMTP Test Successful*\n\n"
            f"Connected to `{sender['smtp_host']}:{sender['smtp_port']}`\n"
            f"Authentication successful\\.",
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *SMTP Test Failed*\n\n"
            f"Error: `{str(e)[:100]}`\n\n"
            f"Check your SMTP settings and app password\\.",
            parse_mode='MarkdownV2'
        )