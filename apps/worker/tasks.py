"""
MailGuard OSS - Worker Tasks
ARQ async tasks for email dispatch and notifications
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from email.message import EmailMessage

import aiosmtplib
from arq import cron
from arq.connections import RedisSettings

from core.config import settings
from core.crypto import decrypt
from core.db import (
    get_sender_email, update_sender_email,
    create_email_log, list_email_logs
)


# ============================================================================
# ARQ Worker Configuration
# ============================================================================

async def startup(ctx):
    """Worker startup - initialize connections."""
    from core.redis_client import init_redis
    from core.db import init_db
    
    await init_redis(settings.REDIS_URL)
    init_db(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    print("✓ Worker started")


async def shutdown(ctx):
    """Worker shutdown - cleanup connections."""
    from core.redis_client import close_redis
    await close_redis()
    print("✓ Worker stopped")


class WorkerSettings:
    """ARQ Worker Settings."""
    functions = [send_otp_email, send_notification, cleanup_expired_otps]
    cron_jobs = [
        cron(cleanup_expired_otps, minute={0, 15, 30, 45})  # Every 15 minutes
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_tries = 3
    retry_delay = 60  # Exponential backoff base


# ============================================================================
# Email Sending Task
# ============================================================================

async def send_otp_email(
    ctx: dict,
    email: str,
    otp: str,
    project_id: str,
    sender_email_id: str,
    purpose: str,
    otp_record_id: str
) -> Dict[str, Any]:
    """
    Send OTP email via SMTP.
    
    Args:
        ctx: ARQ context
        email: Recipient email address
        otp: OTP code to send
        project_id: Project ID
        sender_email_id: Sender email configuration ID
        purpose: Purpose of OTP (registration, login, etc.)
        otp_record_id: OTP record ID for logging
        
    Returns:
        Result dict with status
    """
    from core.crypto import hmac_email
    
    email_hash = hmac_email(email)
    
    try:
        # Get sender configuration
        sender = await get_sender_email(sender_email_id)
        if not sender:
            raise ValueError(f"Sender email not found: {sender_email_id}")
        
        # Check daily limit
        if sender.get('emails_sent_today', 0) >= sender.get('daily_limit', 500):
            raise ValueError("Sender daily limit exceeded")
        
        # Decrypt SMTP password
        smtp_password = decrypt(sender['app_password_enc'])
        
        # Get project for templates
        from core.db import get_project
        project = await get_project(project_id)
        
        # Build email
        message = EmailMessage()
        message["From"] = f"{sender.get('display_name', 'MailGuard')} <{sender['email_address']}>"
        message["To"] = email
        
        # Use templates if available
        subject = project.get('otp_subject_tmpl') if project else None
        body = project.get('otp_body_tmpl') if project else None
        
        if subject:
            # Render Jinja2 template
            from jinja2 import Template
            subject = Template(subject).render(otp=otp, purpose=purpose)
        else:
            subject = f"Your verification code: {otp}"
        
        if body:
            from jinja2 import Template
            body = Template(body).render(otp=otp, purpose=purpose)
        else:
            body = f"Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
        
        message["Subject"] = subject
        
        if project and project.get('otp_format') == 'html':
            message.set_content(body, subtype='html')
        else:
            message.set_content(body)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=sender['smtp_host'],
            port=sender['smtp_port'],
            username=sender['email_address'],
            password=smtp_password,
            start_tls=True
        )
        
        # Update sender usage count
        await update_sender_email(sender['id'], {
            'emails_sent_today': sender.get('emails_sent_today', 0) + 1,
            'last_used_at': datetime.utcnow().isoformat()
        })
        
        # Log success
        await create_email_log(
            project_id=project_id,
            sender_email_id=sender_email_id,
            email_hash=email_hash,
            purpose=purpose,
            status='sent'
        )
        
        return {"status": "sent", "email": email}
    
    except Exception as e:
        # Log failure
        await create_email_log(
            project_id=project_id,
            sender_email_id=sender_email_id,
            email_hash=email_hash,
            purpose=purpose,
            status='failed',
            error_message=str(e)
        )
        
        # Re-raise for retry
        raise


# ============================================================================
# Notification Task
# ============================================================================

async def send_notification(
    ctx: dict,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send notification to Telegram admin.
    
    Args:
        ctx: ARQ context
        notification_type: Type of notification
        message: Notification message
        data: Additional data
        
    Returns:
        Result dict
    """
    try:
        # Send via Telegram bot if configured
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ADMIN_UID:
            from telegram import Bot
            from telegram.constants import ParseMode
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            # Format message
            text = f"🔔 *{notification_type}*\n\n{message}"
            if data:
                text += f"\n\n```json\n{data}\n```"
            
            await bot.send_message(
                chat_id=settings.TELEGRAM_ADMIN_UID,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        return {"status": "sent"}
    
    except Exception as e:
        print(f"Failed to send notification: {e}")
        raise


# ============================================================================
# Cleanup Task
# ============================================================================

async def cleanup_expired_otps(ctx: dict) -> Dict[str, int]:
    """
    Cleanup expired OTP records.
    Runs every 15 minutes via cron.
    
    Returns:
        Count of cleaned up records
    """
    from core.db import get_supabase
    
    try:
        client = get_supabase()
        
        # Mark expired OTPs as invalidated
        result = client.table('otp_records') \
            .update({'is_invalidated': True}) \
            .lt('expires_at', datetime.utcnow().isoformat()) \
            .eq('is_invalidated', False) \
            .execute()
        
        count = len(result.data) if result.data else 0
        
        if count > 0:
            print(f"✓ Cleaned up {count} expired OTP records")
        
        return {"cleaned": count}
    
    except Exception as e:
        print(f"Failed to cleanup expired OTPs: {e}")
        raise


# ============================================================================
# Daily Summary Task
# ============================================================================

async def send_daily_summary(ctx: dict) -> Dict[str, Any]:
    """
    Send daily summary to admin.
    """
    from datetime import timedelta
    from core.db import list_email_logs
    
    try:
        since = datetime.utcnow() - timedelta(days=1)
        logs = await list_email_logs(since=since, limit=1000)
        
        total = len(logs)
        sent = len([l for l in logs if l['status'] == 'sent'])
        failed = len([l for l in logs if l['status'] == 'failed'])
        
        message = (
            f"📊 Daily Summary\n\n"
            f"Total emails: {total}\n"
            f"✓ Sent: {sent}\n"
            f"✗ Failed: {failed}"
        )
        
        await send_notification(None, "Daily Summary", message)
        
        return {"total": total, "sent": sent, "failed": failed}
    
    except Exception as e:
        print(f"Failed to send daily summary: {e}")
        raise