"""
Test GitHub webhook signature verification.
"""
import pytest
import hmac
import hashlib
import json
from core.webhooks.utils import verify_github_signature


def test_valid_signature(sample_push_payload, webhook_secret):
    """Test that a valid signature is accepted."""
    payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    # Generate valid signature
    signature = 'sha256=' + hmac.new(
        webhook_secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    assert verify_github_signature(payload_bytes, signature, webhook_secret) is True


def test_invalid_signature(sample_push_payload, webhook_secret):
    """Test that an invalid signature is rejected."""
    payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    # Use wrong signature
    signature = 'sha256=invalid_signature_here'
    
    assert verify_github_signature(payload_bytes, signature, webhook_secret) is False


def test_missing_signature(sample_push_payload, webhook_secret):
    """Test that missing signature is rejected."""
    payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    assert verify_github_signature(payload_bytes, '', webhook_secret) is False


def test_wrong_format_signature(sample_push_payload, webhook_secret):
    """Test that wrong format signature is rejected."""
    payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    # Missing 'sha256=' prefix
    signature = 'just_a_hash_value'
    
    assert verify_github_signature(payload_bytes, signature, webhook_secret) is False


def test_tampered_payload(sample_push_payload, webhook_secret):
    """Test that tampered payload fails verification."""
    payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    # Generate signature for original payload
    signature = 'sha256=' + hmac.new(
        webhook_secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Tamper with payload
    sample_push_payload['commits'][0]['message'] = "TAMPERED MESSAGE"
    tampered_bytes = json.dumps(sample_push_payload).encode('utf-8')
    
    # Signature should not match tampered payload
    assert verify_github_signature(tampered_bytes, signature, webhook_secret) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])