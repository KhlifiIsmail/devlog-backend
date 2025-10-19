import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str
) -> bool:
    """
    Verify that the payload was sent from GitHub by validating SHA256.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: GitHub webhook secret
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing signature header")
        return False
    
    if not signature_header.startswith('sha256='):
        logger.warning(f"Invalid signature format: {signature_header}")
        return False
    
    # Get the signature from header
    github_signature = signature_header.split('sha256=')[-1]
    
    # Calculate expected signature
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = hash_object.hexdigest()
    
    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(github_signature, expected_signature)
    
    if not is_valid:
        logger.warning("GitHub signature verification failed")
    
    return is_valid


def extract_event_type(event_header: str) -> str:
    """
    Map GitHub event header to our event type choices.
    
    Args:
        event_header: X-GitHub-Event header value
    
    Returns:
        Event type string
    """
    event_mapping = {
        'push': 'push',
        'pull_request': 'pull_request',
        'ping': 'ping',
    }
    return event_mapping.get(event_header, 'other')