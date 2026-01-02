"""Verification code storage and validation service."""
import random
import time
from typing import Optional, Dict, Tuple

# 内存存储验证码：{email: (code, expire_time)}
_verification_codes: Dict[str, Tuple[str, float]] = {}


def generate_verification_code(length: int = 6) -> str:
    """Generate a random verification code."""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def store_verification_code(email: str, code: str, expire_seconds: int = 600) -> None:
    """
    Store verification code with expiration time.
    
    Args:
        email: Email address
        code: Verification code
        expire_seconds: Expiration time in seconds (default 10 minutes)
    """
    expire_time = time.time() + expire_seconds
    _verification_codes[email] = (code, expire_time)


def verify_code(email: str, code: str) -> bool:
    """
    Verify if the code is correct and not expired.
    
    Args:
        email: Email address
        code: Verification code to verify
        
    Returns:
        True if code is valid, False otherwise
    """
    if email not in _verification_codes:
        return False
    
    stored_code, expire_time = _verification_codes[email]
    
    # 检查是否过期
    if time.time() > expire_time:
        # 删除过期验证码
        del _verification_codes[email]
        return False
    
    # 验证码匹配
    if stored_code == code:
        # 验证成功后删除验证码（一次性使用）
        del _verification_codes[email]
        return True
    
    return False


def get_code(email: str) -> Optional[str]:
    """
    Get stored verification code for email (for testing/debugging).
    
    Args:
        email: Email address
        
    Returns:
        Verification code if exists and not expired, None otherwise
    """
    if email not in _verification_codes:
        return None
    
    stored_code, expire_time = _verification_codes[email]
    
    if time.time() > expire_time:
        del _verification_codes[email]
        return None
    
    return stored_code


def cleanup_expired_codes() -> None:
    """Clean up expired verification codes."""
    current_time = time.time()
    expired_emails = [
        email for email, (_, expire_time) in _verification_codes.items()
        if current_time > expire_time
    ]
    for email in expired_emails:
        del _verification_codes[email]


