"""Modelo para palavras-chave."""
from datetime import datetime
from app import db


class Keyword(db.Model):
    """Palavra-chave para busca de editais."""
    __tablename__ = 'keywords'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(256), unique=True, nullable=False)
    normalized_word = db.Column(db.String(256), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    source_file = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Converte para dict serializável."""
        return {
            'id': self.id,
            'word': self.word,
            'normalized_word': self.normalized_word,
            'is_active': self.is_active,
            'source_file': self.source_file,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
