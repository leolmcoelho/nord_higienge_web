"""Modelo para itens extraídos."""
import json
from datetime import datetime
from app import db


class ExtractedItem(db.Model):
    """Item extraído de um edital."""
    __tablename__ = 'extracted_items'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)

    # Metadados do item
    title = db.Column(db.String(512), nullable=False)
    local = db.Column(db.String(256))  # Nome da entidade
    dre_link = db.Column(db.String(512))  # Link original DRE
    portal_url = db.Column(db.String(512))  # URL Vortal/Acingov
    portal_type = db.Column(db.String(20))  # 'vortal' ou 'acingov'

    # Status de processamento
    downloaded = db.Column(db.Boolean, default=False, nullable=False, index=True)
    skipped = db.Column(db.Boolean, default=False, nullable=False)

    # Palavras-chave (JSON array)
    found_keywords = db.Column(db.Text)

    # Data de processamento
    processing_date = db.Column(db.Date, nullable=False, index=True)

    @property
    def keywords_list(self):
        """Retorna keywords como lista."""
        return json.loads(self.found_keywords) if self.found_keywords else []

    @keywords_list.setter
    def keywords_list(self, value):
        """Define keywords a partir de lista."""
        self.found_keywords = json.dumps(value) if value else '[]'

    def to_dict(self):
        """Converte para dict serializável."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title,
            'local': self.local,
            'dre_link': self.dre_link,
            'portal_url': self.portal_url,
            'portal_type': self.portal_type,
            'downloaded': self.downloaded,
            'skipped': self.skipped,
            'found_keywords': self.keywords_list,
            'processing_date': self.processing_date.isoformat() if self.processing_date else None,
        }
