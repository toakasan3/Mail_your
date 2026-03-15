"""
MailGuard OSS - Database Module
Supabase client with service role key
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
import asyncio

# Global Supabase client
_supabase_client: Optional[Client] = None


def init_db(supabase_url: str, supabase_key: str) -> Client:
    """
    Initialize the Supabase client.
    
    Args:
        supabase_url: Supabase project URL
        supabase_key: Supabase service role key (NOT anon key)
        
    Returns:
        Supabase client instance
    """
    global _supabase_client
    _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def get_supabase() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Supabase client
        
    Raises:
        RuntimeError: If client not initialized
    """
    if _supabase_client is None:
        from core.config import settings
        init_db(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


# ============================================================================
# Sender Email Operations
# ============================================================================

async def create_sender_email(
    email_address: str,
    display_name: str,
    provider: str,
    smtp_host: str,
    smtp_port: int,
    app_password_enc: str,
    daily_limit: int = 500
) -> Dict[str, Any]:
    """Create a new sender email record."""
    client = get_supabase()
    result = client.table('sender_emails').insert({
        'email_address': email_address,
        'display_name': display_name,
        'provider': provider,
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'app_password_enc': app_password_enc,
        'daily_limit': daily_limit,
        'is_verified': False,
        'is_active': True
    }).execute()
    return result.data[0] if result.data else None


async def get_sender_email(sender_id: str) -> Optional[Dict[str, Any]]:
    """Get a sender email by ID."""
    client = get_supabase()
    result = client.table('sender_emails').select('*').eq('id', sender_id).execute()
    return result.data[0] if result.data else None


async def get_sender_by_email(email_address: str) -> Optional[Dict[str, Any]]:
    """Get a sender email by email address."""
    client = get_supabase()
    result = client.table('sender_emails').select('*').eq('email_address', email_address).execute()
    return result.data[0] if result.data else None


async def list_sender_emails(active_only: bool = True) -> List[Dict[str, Any]]:
    """List all sender emails."""
    client = get_supabase()
    query = client.table('sender_emails').select('*')
    if active_only:
        query = query.eq('is_active', True)
    result = query.order('created_at', desc=True).execute()
    return result.data


async def update_sender_email(sender_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a sender email record."""
    client = get_supabase()
    result = client.table('sender_emails').update(updates).eq('id', sender_id).execute()
    return result.data[0] if result.data else None


async def delete_sender_email(sender_id: str) -> bool:
    """Delete a sender email record."""
    client = get_supabase()
    result = client.table('sender_emails').delete().eq('id', sender_id).execute()
    return len(result.data) > 0


# ============================================================================
# Project Operations
# ============================================================================

async def create_project(
    name: str,
    slug: str,
    sender_email_id: Optional[str] = None,
    otp_length: int = 6,
    otp_expiry_seconds: int = 600,
    otp_max_attempts: int = 5,
    otp_subject_tmpl: Optional[str] = None,
    otp_body_tmpl: Optional[str] = None,
    otp_format: str = 'text',
    rate_limit_per_hour: int = 10
) -> Dict[str, Any]:
    """Create a new project."""
    client = get_supabase()
    result = client.table('projects').insert({
        'name': name,
        'slug': slug,
        'sender_email_id': sender_email_id,
        'otp_length': otp_length,
        'otp_expiry_seconds': otp_expiry_seconds,
        'otp_max_attempts': otp_max_attempts,
        'otp_subject_tmpl': otp_subject_tmpl,
        'otp_body_tmpl': otp_body_tmpl,
        'otp_format': otp_format,
        'rate_limit_per_hour': rate_limit_per_hour,
        'is_active': True
    }).execute()
    return result.data[0] if result.data else None


async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get a project by ID."""
    client = get_supabase()
    result = client.table('projects').select('*, sender_emails(*)').eq('id', project_id).execute()
    return result.data[0] if result.data else None


async def get_project_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get a project by slug."""
    client = get_supabase()
    result = client.table('projects').select('*, sender_emails(*)').eq('slug', slug).execute()
    return result.data[0] if result.data else None


async def list_projects(active_only: bool = True) -> List[Dict[str, Any]]:
    """List all projects."""
    client = get_supabase()
    query = client.table('projects').select('*, sender_emails(*)')
    if active_only:
        query = query.eq('is_active', True)
    result = query.order('created_at', desc=True).execute()
    return result.data


async def update_project(project_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a project."""
    client = get_supabase()
    result = client.table('projects').update(updates).eq('id', project_id).execute()
    return result.data[0] if result.data else None


# ============================================================================
# API Key Operations
# ============================================================================

async def create_api_key(
    project_id: str,
    key_hash: str,
    key_prefix: str,
    label: Optional[str] = None,
    is_sandbox: bool = False
) -> Dict[str, Any]:
    """Create a new API key."""
    client = get_supabase()
    result = client.table('api_keys').insert({
        'project_id': project_id,
        'key_hash': key_hash,
        'key_prefix': key_prefix,
        'label': label,
        'is_sandbox': is_sandbox,
        'is_active': True
    }).execute()
    return result.data[0] if result.data else None


async def get_api_key_by_hash(key_hash: str) -> Optional[Dict[str, Any]]:
    """Get an API key by its hash."""
    client = get_supabase()
    result = client.table('api_keys').select('*, projects(*)').eq('key_hash', key_hash).eq('is_active', True).execute()
    return result.data[0] if result.data else None


async def list_api_keys(project_id: str) -> List[Dict[str, Any]]:
    """List all API keys for a project."""
    client = get_supabase()
    result = client.table('api_keys').select('*').eq('project_id', project_id).order('created_at', desc=True).execute()
    return result.data


async def revoke_api_key(key_id: str) -> bool:
    """Revoke an API key."""
    client = get_supabase()
    result = client.table('api_keys').update({'is_active': False}).eq('id', key_id).execute()
    return len(result.data) > 0


async def update_api_key_last_used(key_id: str) -> None:
    """Update the last_used_at timestamp for an API key."""
    client = get_supabase()
    client.table('api_keys').update({
        'last_used_at': datetime.utcnow().isoformat()
    }).eq('id', key_id).execute()


# ============================================================================
# OTP Record Operations
# ============================================================================

async def create_otp_record(
    project_id: str,
    email_hash: str,
    otp_hash: str,
    purpose: str,
    expires_at: datetime
) -> Dict[str, Any]:
    """Create a new OTP record."""
    client = get_supabase()
    result = client.table('otp_records').insert({
        'project_id': project_id,
        'email_hash': email_hash,
        'otp_hash': otp_hash,
        'purpose': purpose,
        'expires_at': expires_at.isoformat(),
        'attempt_count': 0,
        'is_verified': False,
        'is_invalidated': False
    }).execute()
    return result.data[0] if result.data else None


async def get_active_otp(project_id: str, email_hash: str) -> Optional[Dict[str, Any]]:
    """Get the most recent active OTP for an email."""
    client = get_supabase()
    result = client.table('otp_records').select('*') \
        .eq('project_id', project_id) \
        .eq('email_hash', email_hash) \
        .eq('is_invalidated', False) \
        .gt('expires_at', datetime.utcnow().isoformat()) \
        .eq('is_verified', False) \
        .order('created_at', desc=True) \
        .limit(1) \
        .execute()
    return result.data[0] if result.data else None


async def increment_otp_attempt(otp_id: str) -> int:
    """Increment the attempt count for an OTP."""
    client = get_supabase()
    # First get current count
    result = client.table('otp_records').select('attempt_count').eq('id', otp_id).execute()
    if not result.data:
        return 0
    new_count = result.data[0]['attempt_count'] + 1
    client.table('otp_records').update({'attempt_count': new_count}).eq('id', otp_id).execute()
    return new_count


async def mark_otp_verified(otp_id: str) -> None:
    """Mark an OTP as verified."""
    client = get_supabase()
    client.table('otp_records').update({
        'is_verified': True,
        'is_invalidated': True
    }).eq('id', otp_id).execute()


async def invalidate_otp(otp_id: str) -> None:
    """Invalidate an OTP."""
    client = get_supabase()
    client.table('otp_records').update({'is_invalidated': True}).eq('id', otp_id).execute()


async def count_otps_for_email(project_id: str, email_hash: str, since: datetime) -> int:
    """Count OTPs sent to an email in a time period."""
    client = get_supabase()
    result = client.table('otp_records').select('id', count='exact') \
        .eq('project_id', project_id) \
        .eq('email_hash', email_hash) \
        .gte('created_at', since.isoformat()) \
        .execute()
    return result.count if hasattr(result, 'count') else len(result.data)


# ============================================================================
# Email Log Operations
# ============================================================================

async def create_email_log(
    project_id: str,
    sender_email_id: str,
    email_hash: str,
    purpose: str,
    status: str,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """Create an email log entry."""
    client = get_supabase()
    result = client.table('email_logs').insert({
        'project_id': project_id,
        'sender_email_id': sender_email_id,
        'email_hash': email_hash,
        'purpose': purpose,
        'status': status,
        'error_message': error_message
    }).execute()
    return result.data[0] if result.data else None


async def list_email_logs(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List email logs with optional filters."""
    client = get_supabase()
    query = client.table('email_logs').select('*, projects(name, slug), sender_emails(email_address)')
    
    if project_id:
        query = query.eq('project_id', project_id)
    if status:
        query = query.eq('status', status)
    if since:
        query = query.gte('created_at', since.isoformat())
    
    result = query.order('created_at', desc=True).limit(limit).execute()
    return result.data


# ============================================================================
# Bot Session Operations
# ============================================================================

async def save_bot_session(user_id: int, session_data: Dict[str, Any]) -> None:
    """Save or update a bot session."""
    client = get_supabase()
    # Upsert the session
    result = client.table('bot_sessions').select('*').eq('user_id', str(user_id)).execute()
    
    if result.data:
        client.table('bot_sessions').update({
            'session_data': session_data,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('user_id', str(user_id)).execute()
    else:
        client.table('bot_sessions').insert({
            'user_id': str(user_id),
            'session_data': session_data
        }).execute()


async def get_bot_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Get a bot session."""
    client = get_supabase()
    result = client.table('bot_sessions').select('*').eq('user_id', str(user_id)).execute()
    return result.data[0]['session_data'] if result.data else None


async def clear_bot_session(user_id: int) -> None:
    """Clear a bot session."""
    client = get_supabase()
    client.table('bot_sessions').delete().eq('user_id', str(user_id)).execute()


# ============================================================================
# Health Check
# ============================================================================

async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        client = get_supabase()
        result = client.table('projects').select('id').limit(1).execute()
        return True
    except Exception:
        return False