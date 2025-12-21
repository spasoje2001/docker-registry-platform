"""
Utility functions for accounts app.
"""
import random
import string
from django.core.cache import cache


def generate_verification_code(length=6):
    """Generate random numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))


def store_email_change_request(user_id, new_email, code):
    """
    Store email change request in Redis.

    Args:
        user_id: User's ID
        new_email: New email address to change to
        code: Verification code

    Returns:
        bool: True if stored successfully
    """
    cache_key = f'email_change:{user_id}'
    data = {
        'new_email': new_email,
        'code': code,
    }
    # Expiration: 10 minutes (600 seconds)
    return cache.set(cache_key, data, timeout=600)


def get_email_change_request(user_id):
    """
    Retrieve email change request from Redis.

    Args:
        user_id: User's ID

    Returns:
        dict or None: {'new_email': str, 'code': str} if exists, None otherwise
    """
    cache_key = f'email_change:{user_id}'
    return cache.get(cache_key)


def delete_email_change_request(user_id):
    """
    Delete email change request from Redis.

    Args:
        user_id: User's ID
    """
    cache_key = f'email_change:{user_id}'
    cache.delete(cache_key)
