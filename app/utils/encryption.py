"""Utilitários de encriptação para credenciais."""
import base64
import hashlib
from cryptography.fernet import Fernet


class CredentialEncryption:
    """Encriptar/decriptar credenciais usando AES."""

    @staticmethod
    def _get_key():
        """Deriva chave de encriptação da configuração."""
        import os
        key_str = os.environ.get('ENCRYPTION_KEY', 'nord-higiene-default-key-change-in-production')
        key_bytes = hashlib.sha256(key_str.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    @staticmethod
    def encrypt(text: str) -> str:
        """Encripta texto."""
        key = CredentialEncryption._get_key()
        fernet = Fernet(key)
        return fernet.encrypt(text.encode()).decode()

    @staticmethod
    def decrypt(encrypted_text: str) -> str:
        """Decripta texto."""
        key = CredentialEncryption._get_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_text.encode()).decode()
