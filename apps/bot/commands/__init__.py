"""
MailGuard OSS - Bot Commands
"""
from apps.bot.commands import start, addemail, senders, testsender, removesender
from apps.bot.commands import newproject, projects, genkey, keys, revokekey, testkey
from apps.bot.commands import logs, stats

__all__ = [
    'start', 'addemail', 'senders', 'testsender', 'removesender',
    'newproject', 'projects', 'genkey', 'keys', 'revokekey', 'testkey',
    'logs', 'stats'
]