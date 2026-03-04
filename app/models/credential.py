"""Modelo para credenciais."""
from datetime import datetime
from app import db


class Credential(db.Model):
    """Credenciais de login para portais."""
    __tablename__ = 'credentials'

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(50), unique=True, nullable=False)  # 'vortal' ou 'acingov'
    username_encrypted = db.Column(db.String(512), nullable=False)
    password_encrypted = db.Column(db.String(512), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, mask_password=True):
        """Converte para dict serializável."""
        result = {
            'id': self.id,
            'service': self.service,
            'username': self.username_encrypted,  # Será descriptografado no service
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if mask_password:
            result['password'] = '***'
        return result
