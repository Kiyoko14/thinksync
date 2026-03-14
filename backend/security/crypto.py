"""
Cryptography utilities for sensitive data protection.

Provides encryption/decryption for sensitive data like SSH keys and passwords,
plus masking utilities for logging and API responses.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


# In production, this should come from a secure environment variable
# or key management service (AWS KMS, HashiCorp Vault, etc.)
def _get_encryption_key() -> bytes:
    """
    Get or generate the encryption key.
    
    In production, this should use a proper key management system.
    For now, we derive from ENCRYPTION_KEY env var or generate one.
    """
    key_env = os.getenv("ENCRYPTION_KEY")
    if key_env:
        # Use provided key
        try:
            return base64.urlsafe_b64decode(key_env)
        except Exception:
            pass
    
    # For development/testing: derive from a salt
    # In production, use proper KMS
    salt = os.getenv("ENCRYPTION_SALT", "thinksync-default-salt-change-in-prod").encode()
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    password = os.getenv("ENCRYPTION_PASSWORD", "change-this-in-production").encode()
    return base64.urlsafe_b64encode(kdf.derive(password))


_CIPHER = None


def _get_cipher() -> Fernet:
    """Get or create the Fernet cipher instance."""
    global _CIPHER
    if _CIPHER is None:
        _CIPHER = Fernet(_get_encryption_key())
    return _CIPHER


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data like SSH keys or passwords.
    
    Args:
        data: The plaintext data to encrypt
        
    Returns:
        Base64-encoded encrypted data
        
    Note:
        In production, consider using envelope encryption with a
        Key Management Service (AWS KMS, GCP KMS, Azure Key Vault)
    """
    if not data:
        return ""
    
    try:
        cipher = _get_cipher()
        encrypted = cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        # Log the error but don't expose details
        print(f"Encryption error: {type(e).__name__}")
        raise ValueError("Failed to encrypt sensitive data")


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
        
    Returns:
        Decrypted plaintext
        
    Raises:
        ValueError: If decryption fails
    """
    if not encrypted_data:
        return ""
    
    try:
        cipher = _get_cipher()
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = cipher.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        print(f"Decryption error: {type(e).__name__}")
        raise ValueError("Failed to decrypt sensitive data")


def mask_sensitive_value(value: Optional[str], visible_chars: int = 4) -> str:
    """
    Mask a sensitive value for logging or API responses.
    
    Args:
        value: The value to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked string like "***key1234" or "***"
        
    Examples:
        >>> mask_sensitive_value("my-secret-api-key-12345", 5)
        "***12345"
        >>> mask_sensitive_value("short")
        "***"
        >>> mask_sensitive_value(None)
        "***"
    """
    if not value:
        return "***"
    
    if len(value) <= visible_chars:
        return "***"
    
    return "***" + value[-visible_chars:]


def mask_ssh_key(key: Optional[str]) -> str:
    """
    Mask an SSH private key for logging.
    
    Args:
        key: The SSH private key
        
    Returns:
        Masked representation showing only key type
    """
    if not key:
        return "***"
    
    # Try to extract key type from header
    if "BEGIN RSA PRIVATE KEY" in key:
        return "***RSA_KEY***"
    elif "BEGIN OPENSSH PRIVATE KEY" in key:
        return "***OPENSSH_KEY***"
    elif "BEGIN EC PRIVATE KEY" in key:
        return "***EC_KEY***"
    elif "BEGIN DSA PRIVATE KEY" in key:
        return "***DSA_KEY***"
    else:
        return "***PRIVATE_KEY***"


def mask_connection_string(conn_str: Optional[str]) -> str:
    """
    Mask password in database connection strings.
    
    Args:
        conn_str: Connection string like "postgres://user:pass@host:5432/db"
        
    Returns:
        Masked connection string like "postgres://user:***@host:5432/db"
    """
    if not conn_str:
        return "***"
    
    import re
    # Match password in various connection string formats
    patterns = [
        (r"://([^:]+):([^@]+)@", r"://\1:***@"),  # postgres://user:pass@host
        (r"password=([^;&]+)", r"password=***"),   # password=secret
        (r"pwd=([^;&]+)", r"pwd=***"),             # pwd=secret
    ]
    
    masked = conn_str
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
    
    return masked


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        URL-safe base64-encoded token
    """
    return base64.urlsafe_b64encode(os.urandom(length)).decode()[:length]
