"""
MailGuard OSS - Worker Application
"""
from apps.worker.tasks import WorkerSettings, send_otp_email, send_notification

__all__ = ['WorkerSettings', 'send_otp_email', 'send_notification']