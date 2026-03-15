"""
MailGuard OSS - Test API Key Command
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.config import settings
from core.db import list_api_keys, list_projects
import httpx


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /testkey command - test an API key against the API."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/testkey <api_key> <test_email>`\n\n"
            "This will send a test OTP to the email\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    api_key = context.args[0]
    test_email = context.args[1]
    
    # Determine if sandbox key
    is_sandbox = api_key.startswith('mg_test_')
    
    # Get API base URL from settings
    api_base = f"http://localhost:{settings.PORT}"
    if settings.is_production:
        # In production, use the public URL
        api_base = "https://your-api.up.railway.app"  # Replace with actual URL
    
    await update.message.reply_text(
        f"⏳ Testing API key...\n\n"
        f"Key type: {'🧪 Sandbox' if is_sandbox else '🔑 Live'}\n"
        f"Email: `{test_email}`",
        parse_mode='MarkdownV2'
    )
    
    try:
        async with httpx.AsyncClient() as client:
            # Test send OTP
            response = await client.post(
                f"{api_base}/api/v1/otp/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"email": test_email, "purpose": "test"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                await update.message.reply_text(
                    f"✅ *API Key Test Successful*\n\n"
                    f"OTP sent to `{data.get('masked_email', test_email)}`\n"
                    f"Expires in: {data.get('expires_in', 600)}s\n\n"
                    f"{'Test OTP: `000000`' if is_sandbox else 'Check email for OTP code'}",
                    parse_mode='MarkdownV2'
                )
            else:
                error = response.json().get('detail', response.text)
                await update.message.reply_text(
                    f"❌ *API Key Test Failed*\n\n"
                    f"Status: {response.status_code}\n"
                    f"Error: `{error}`",
                    parse_mode='MarkdownV2'
                )
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ *API Key Test Failed*\n\n"
            f"Error: `{str(e)}`",
            parse_mode='MarkdownV2'
        )