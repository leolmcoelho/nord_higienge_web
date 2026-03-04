"""Modelo para logs de jobs."""
from datetime import datetime
from app import db


class JobLog(db.Model):
    """Log de execução de job."""
    __tablename__ = 'job_logs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    level = db.Column(db.String(10), nullable=False, index=True)  # INFO, WARNING, ERROR, DEBUG
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Dados adicionais (opcional, JSON)
    extra_json = db.Column(db.Text)

    # Relacionamento
    job = db.relationship('ExtractionJob', backref=db.backref('logs', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def extra(self):
        """Retorna dados extras como dict."""
        import json
        return json.loads(self.extra_json) if self.extra_json else {}

    @extra.setter
    def extra(self, value):
        """Define dados extras a partir de dict."""
        import json
        self.extra_json = json.dumps(value) if value else None

    def to_dict(self):
        """Converte para dict serializável."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'extra': self.extra,
        }
