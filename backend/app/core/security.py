"""
Provides the cryptographic engine, utilizing AES-256-GCM algorithms to encrypt/decrypt vaulted API credentials.
Manages the authentication headers and authorization dependencies required to protect the administrative UI endpoints.
"""

import os
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecretVault:
    """
    Provides hardware-accelerated AES-256-GCM authenticated encryption
    for storing sensitive multi-tenant third-party tokens.
    """
    
    @staticmethod
    def _get_master_key() -> bytes:
        """
        Retrieves and validates the master encryption key from environment variables.
        The key must be a 32-byte base64 or hex-encoded string in production, 
        or a raw 32-byte string.
        """
        key_str = os.getenv("ENCRYPTION_MASTER_KEY", "fallback_secret_key_must_be_32_bytes!!")
        key_bytes = key_str.encode("utf-8")
        if len(key_bytes) != 32:
            raise ValueError("ENCRYPTION_MASTER_KEY must be exactly 32 bytes long")
        return key_bytes

    @classmethod
    def encrypt_token(cls, plain_text_token: str) -> Tuple[bytes, bytes]:
        """
        Encrypts a plain text string using AES-256-GCM.
        Returns a tuple containing the ciphertext and the unique initialization vector (IV).
        """
        aesgcm = AESGCM(cls._get_master_key())
        nonce = os.urandom(12)  # Standard 12-byte nonce for GCM mode
        ciphertext = aesgcm.encrypt(nonce, plain_text_token.encode("utf-8"), None)
        return ciphertext, nonce

    @classmethod
    def decrypt_token(cls, ciphertext: bytes, nonce: bytes) -> str:
        """
        Decrypts AES-256-GCM ciphertext.
        Verifies authentication tags automatically during the operation.
        """
        aesgcm = AESGCM(cls._get_master_key())
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")