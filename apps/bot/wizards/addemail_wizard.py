"""
MailGuard OSS - Add Email Wizard
Multi-step conversation for adding a sender email
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import re

from core.config import settings
from core.crypto import encrypt
from core.db import create_sender_email, get_sender_by_email

# States
EMAIL, PASSWORD, PROVIDER, CONFIRM = range(4)

# Common SMTP providers
PROVIDERS = {
    'gmail': {'host': 'smtp.gmail.com', 'port': 587},
    'outlook': {'host': 'smtp.office365.com', 'port': 587},
    'yahoo': {'host': 'smtp.mail.yahoo.com', 'port': 587},
    'zoho': {'host': 'smtp.zoho.com', 'port': 587},
    'custom': {'host': None, 'port': 587}
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add email wizard."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📧 *Add Sender Email*\n\n"
        "Please enter the email address you want to use for sending OTPs\\.\n\n"
        "Use /cancel to abort\\.",
        parse_mode='MarkdownV2'
    )
    
    return EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate email address."""
    email = update.message.text.strip().lower()
    
    # Validate email format
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        await update.message.reply_text(
            "Invalid email format\\. Please enter a valid email address\\.",
            parse_mode='MarkdownV2'
        )
        return EMAIL
    
    # Check if already exists
    existing = await get_sender_by_email(email)
    if existing:
        await update.message.reply_text(
            "This email is already configured\\. Use /senders to see existing senders\\.",
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    # Store email in context
    context.user_data['sender_email'] = email
    
    await update.message.reply_text(
        f"Email: `{email}`\n\n"
        f"Now please enter the App Password for this email\\.\n\n"
        f"⚠️ For Gmail, use an App Password from your Google Account security settings\\.\n"
        f"For Outlook, use an App Password from Microsoft account security\\.\n\n"
        f"_The password will be encrypted and stored securely\\._",
        parse_mode='MarkdownV2'
    )
    
    return PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and encrypt the app password."""
    password = update.message.text.strip()
    
    # Store encrypted password
    encrypted_password = encrypt(password)
    context.user_data['app_password_enc'] = encrypted_password
    
    # Delete the message containing the password for security
    try:
        await update.message.delete()
    except:
        pass
    
    await update.message.reply_text(
        "✅ Password encrypted and stored\\.\n\n"
        "Select the email provider:\n\n"
        "1\\. Gmail\n"
        "2\\. Outlook\n"
        "3\\. Yahoo\n"
        "4\\. Zoho\n"
        "5\\. Custom\n\n"
        "Reply with the number or name\\.",
        parse_mode='MarkdownV2'
    )
    
    return PROVIDER


async def receive_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive provider selection and collect SMTP details if custom."""
    text = update.message.text.strip().lower()
    
    provider_map = {
        '1': 'gmail', 'gmail': 'gmail',
        '2': 'outlook', 'outlook': 'outlook', 'microsoft': 'outlook',
        '3': 'yahoo', 'yahoo': 'yahoo',
        '4': 'zoho', 'zoho': 'zoho',
        '5': 'custom', 'custom': 'custom'
    }
    
    provider = provider_map.get(text)
    
    if not provider:
        await update.message.reply_text(
            "Invalid selection\\. Please reply with 1\\-5 or the provider name\\.",
            parse_mode='MarkdownV2'
        )
        return PROVIDER
    
    context.user_data['provider'] = provider
    
    if provider == 'custom':
        await update.message.reply_text(
            "Enter the SMTP host \\(e\\.g\\. mail\\.yourdomain\\.com\\):",
            parse_mode='MarkdownV2'
        )
        context.user_data['awaiting_smtp_host'] = True
        return PROVIDER  # Will need to handle this in next message
    
    # Use predefined SMTP settings
    smtp_config = PROVIDERS[provider]
    context.user_data['smtp_host'] = smtp_config['host']
    context.user_data['smtp_port'] = smtp_config['port']
    
    # Show confirmation
    email = context.user_data['sender_email']
    
    await update.message.reply_text(
        f"📧 *Confirm Sender Email*\n\n"
        f"Email: `{email}`\n"
        f"Provider: {provider.title()}\n"
        f"SMTP: `{smtp_config['host']}:{smtp_config['port']}`\n\n"
        f"Reply 'yes' to confirm and save, or 'no' to cancel\\.",
        parse_mode='MarkdownV2'
    )
    
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and save the sender email."""
    text = update.message.text.strip().lower()
    
    if text not in ['yes', 'y']:
        await update.message.reply_text(
            "Cancelled\\. Use /addemail to start over\\.",
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    email = context.user_data['sender_email']
    provider = context.user_data['provider']
    app_password_enc = context.user_data['app_password_enc']
    smtp_host = context.user_data.get('smtp_host', PROVIDERS.get(provider, {}).get('host'))
    smtp_port = context.user_data.get('smtp_port', 587)
    
    # Create sender email record
    try:
        sender = await create_sender_email(
            email_address=email,
            display_name=email.split('@')[0],
            provider=provider,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            app_password_enc=app_password_enc
        )
        
        await update.message.reply_text(
            f"✅ *Sender Email Added*\n\n"
            f"Email: `{email}`\n"
            f"Provider: {provider.title()}\n"
            f"ID: `{sender['id'][:8]}...`\n\n"
            f"Use /testsender to verify the SMTP connection\\.",
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to save sender email: `{str(e)}`",
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