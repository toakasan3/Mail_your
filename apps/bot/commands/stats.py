"""
MailGuard OSS - Stats Command
"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

from core.config import settings
from core.db import list_email_logs, list_projects, list_sender_emails, list_api_keys


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - view statistics."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    # Get current stats
    projects = await list_projects()
    senders = await list_sender_emails()
    
    # Get logs for different time periods
    now = datetime.utcnow()
    
    today_logs = await list_email_logs(since=now - timedelta(hours=24), limit=1000)
    week_logs = await list_email_logs(since=now - timedelta(days=7), limit=5000)
    
    # Calculate stats
    def count_stats(logs):
        sent = len([l for l in logs if l['status'] == 'sent'])
        failed = len([l for l in logs if l['status'] == 'failed'])
        return sent, failed
    
    today_sent, today_failed = count_stats(today_logs)
    week_sent, week_failed = count_stats(week_logs)
    
    # Count API keys
    total_keys = 0
    active_keys = 0
    for project in projects:
        keys = await list_api_keys(project['id'])
        total_keys += len(keys)
        active_keys += len([k for k in keys if k['is_active']])
    
    message = (
        "📊 *MailGuard Statistics*\n\n"
        
        f"*Overview*\n"
        f"📁 Projects: {len(projects)}\n"
        f"📧 Senders: {len([s for s in senders if s['is_active']])}\n"
        f"🔑 API Keys: {active_keys}/{total_keys} active\n\n"
        
        f"*Today \(24h\)*\n"
        f"✅ Sent: {today_sent}\n"
        f"❌ Failed: {today_failed}\n"
        f"📈 Success Rate: {(today_sent / max(today_sent + today_failed, 1) * 100):.1f}%\n\n"
        
        f"*This Week*\n"
        f"✅ Sent: {week_sent}\n"
        f"❌ Failed: {week_failed}\n"
        f"📈 Success Rate: {(week_sent / max(week_sent + week_failed, 1) * 100):.1f}%\n\n"
        
        f"*Sender Usage*\n"
    )
    
    for sender in senders[:5]:  # Top 5 senders
        usage = sender.get('emails_sent_today', 0)
        limit = sender.get('daily_limit', 500)
        pct = (usage / limit * 100) if limit > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        message += f"`{sender['email_address'][:20]}` {bar} {usage}/{limit}\n"
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')