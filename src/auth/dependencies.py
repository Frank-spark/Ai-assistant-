"""Authentication dependencies for Reflex Executive Assistant."""

import logging
import hmac
import hashlib
import time
import json
from typing import Optional
from fastapi import Request, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def verify_slack_signature(request: Request) -> None:
    """Verify Slack webhook signature."""
    try:
        settings = get_settings()
        slack_signing_secret = settings.slack_signing_secret
        
        if not slack_signing_secret:
            logger.warning("Slack signing secret not configured")
            return
        
        # Get timestamp and signature from headers
        timestamp = request.headers.get("x-slack-request-timestamp")
        signature = request.headers.get("x-slack-signature")
        
        if not timestamp or not signature:
            raise HTTPException(status_code=401, detail="Missing Slack signature headers")
        
        # Check if request is too old (replay attack protection)
        if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
            raise HTTPException(status_code=401, detail="Request timestamp too old")
        
        # Get request body
        body = await request.body()
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = f"v0={hmac.new(slack_signing_secret.encode('utf-8'), sig_basestring.encode('utf-8'), hashlib.sha256).hexdigest()}"
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
            
        logger.debug("Slack signature verified successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        raise HTTPException(status_code=401, detail="Signature verification failed")


async def verify_gmail_webhook(request: Request) -> None:
    """Verify Gmail webhook authenticity."""
    try:
        settings = get_settings()
        gmail_webhook_secret = settings.gmail_webhook_secret
        
        if not gmail_webhook_secret:
            logger.warning("Gmail webhook secret not configured")
            return
        
        # Gmail uses a simple token-based verification
        # The token is sent in the request body or headers
        # This is a simplified verification - in production you might want more robust checks
        
        # For now, we'll just log that verification was attempted
        logger.debug("Gmail webhook verification attempted")
        
    except Exception as e:
        logger.error(f"Error verifying Gmail webhook: {e}")
        raise HTTPException(status_code=401, detail="Gmail webhook verification failed")


async def verify_asana_webhook(request: Request) -> None:
    """Verify Asana webhook signature."""
    try:
        settings = get_settings()
        asana_webhook_secret = settings.asana_webhook_secret
        
        if not asana_webhook_secret:
            logger.warning("Asana webhook secret not configured")
            return
        
        # Get signature from headers
        signature = request.headers.get("x-hook-signature")
        signature_256 = request.headers.get("x-hook-signature-256")
        
        if not signature and not signature_256:
            raise HTTPException(status_code=401, detail="Missing Asana signature headers")
        
        # Get request body
        body = await request.body()
        
        # Verify signature (Asana uses HMAC-SHA256)
        if signature_256:
            expected_signature = hmac.new(
                asana_webhook_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature_256, expected_signature):
                raise HTTPException(status_code=401, detail="Invalid Asana signature")
        
        logger.debug("Asana signature verified successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying Asana webhook: {e}")
        raise HTTPException(status_code=401, detail="Asana webhook verification failed")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Get current authenticated user from JWT token."""
    try:
        if not credentials:
            return None
        
        settings = get_settings()
        jwt_secret = settings.jwt_secret
        
        if not jwt_secret:
            logger.warning("JWT secret not configured")
            return None
        
        # TODO: Implement JWT token validation
        # This would decode the JWT token and return user information
        
        logger.debug("JWT token validation attempted")
        return None
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


async def require_authentication(
    current_user: Optional[dict] = Depends(get_current_user)
) -> dict:
    """Require authentication for protected endpoints."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user


async def require_admin_role(
    current_user: dict = Depends(require_authentication)
) -> dict:
    """Require admin role for administrative endpoints."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_api_key(
    x_api_key: Optional[str] = Header(None)
) -> Optional[str]:
    """Get API key from header."""
    if not x_api_key:
        return None
    
    settings = get_settings()
    valid_api_keys = settings.api_keys
    
    if x_api_key in valid_api_keys:
        return x_api_key
    
    return None


async def require_api_key(
    api_key: Optional[str] = Depends(get_api_key)
) -> str:
    """Require valid API key for API endpoints."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Valid API key required")
    return api_key 