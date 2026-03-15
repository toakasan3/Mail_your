"""
MailGuard OSS - Logs Command
"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

from core.config import settings
from core.db import list_email_logs, list_projects


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logs command - view email logs."""
    user_id = update.effective_user.id
    
    if settings.TELEGRAM_ADMIN_UID and user_id != settings.TELEGRAM_ADMIN_UID:
        return
    
    # Parse arguments
    project_slug = None
    status_filter = None
    since = datetime.utcnow() - timedelta(hours=24)  # Default: last 24 hours
    limit = 20
    
    for arg in context.args or []:
        if arg == '--failed':
            status_filter = 'failed'
        elif arg == '--today':
            since = datetime.utcnow() - timedelta(hours=24)
        elif arg == '--week':
            since = datetime.utcnow() - timedelta(days=7)
        elif not arg.startswith('--'):
            project_slug = arg
    
    # Get logs
    project_id = None
    if project_slug:
        from core.db import get_project_by_slug
        project = await get_project_by_slug(project_slug)
        if project:
            project_id = project['id']
    
    logs = await list_email_logs(
        project_id=project_id,
        status=status_filter,
        since=since,
        limit=limit
    )
    
    if not logs:
        await update.message.reply_text(
            "No logs found for the specified filters\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    message = "📋 *Email Logs*\n\n"
    
    for log in logs[:15]:  # Limit to 15 for readability
        status_icon = "✅" if log['status'] == 'sent' else "❌"
        project_name = log.get('projects', {}).get('name', 'Unknown')
        timestamp = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).strftime('%m/%d %H:%M')
        
        message += (
            f"{status_icon} `{timestamp}` "
            f"[{project_name}] "
            f"{log.get('purpose', 'N/A')}"
        )
        
        if log['status'] == 'failed' and log.get('error_message'):
            error_short = log['error_message'][:50]
            message += f"\n   Error: `{error_short}`"
        
        message += "\n"
    
    total = len(logs)
    if total > 15:
        message += f"\n_...and {total - 15} more_"
    
    # Add summary
    sent_count = len([l for l in logs if l['status'] == 'sent'])
    failed_count = len([l for l in logs if l['status'] == 'failed'])
    
    message += f"\n📊 Summary: {sent_count} sent, {failed_count} failed"
    
    await update.message.reply_text(message, parse_mode='MarkdownV2')