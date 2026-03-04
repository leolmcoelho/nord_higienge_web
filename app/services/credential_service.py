"""Serviço para gerenciamento de credenciais."""
from app.models.credential import Credential
from app.utils.encryption import CredentialEncryption
from app import db


class CredentialService:
    """Serviço para operações com credenciais."""

    def save_credentials(self, service: str, username: str, password: str) -> None:
        """Salva ou atualiza credenciais de um serviço."""
        encrypted_username = CredentialEncryption.encrypt(username)
        encrypted_password = CredentialEncryption.encrypt(password)

        cred = Credential.query.filter_by(service=service).first()
        if cred:
            cred.username_encrypted = encrypted_username
            cred.password_encrypted = encrypted_password
        else:
            cred = Credential(
                service=service,
                username_encrypted=encrypted_username,
                password_encrypted=encrypted_password
            )
            db.session.add(cred)
        db.session.commit()

    def get_credentials(self, service: str) -> dict:
        """Retorna credenciais de um serviço (decriptadas)."""
        cred = Credential.query.filter_by(service=service).first()
        if not cred:
            return None

        return {
            'username': CredentialEncryption.decrypt(cred.username_encrypted),
            'password': CredentialEncryption.decrypt(cred.password_encrypted),
            'updated_at': cred.updated_at.isoformat() if cred.updated_at else None,
        }

    def get_all_credentials(self) -> list[dict]:
        """Retorna todas as credenciais (decriptadas)."""
        creds = Credential.query.all()
        result = []
        for cred in creds:
            result.append({
                'service': cred.service,
                'username': CredentialEncryption.decrypt(cred.username_encrypted),
                'updated_at': cred.updated_at.isoformat() if cred.updated_at else None,
            })
        return result
