"""Modelo para jobs de extração."""
from datetime import datetime
from app import db


class ExtractionJob(db.Model):
    """Job de extração de editais."""
    __tablename__ = 'extraction_jobs'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    execution_time = db.Column(db.Float)  # segundos

    # Configuração (JSON)
    config_json = db.Column(db.Text, nullable=False)

    # Resultados
    links_total = db.Column(db.Integer, default=0)
    processed = db.Column(db.Integer, default=0)
    downloaded = db.Column(db.Integer, default=0)
    skipped = db.Column(db.Integer, default=0)

    # Relatório
    report_path = db.Column(db.String(512))

    # Erros
    error_message = db.Column(db.Text)
    error_traceback = db.Column(db.Text)

    # Relacionamentos
    items = db.relationship('ExtractedItem', backref='job', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def config(self):
        """Retorna configuração como dict."""
        import json
        return json.loads(self.config_json) if self.config_json else {}

    @config.setter
    def config(self, value):
        """Define configuração a partir de dict."""
        import json
        self.config_json = json.dumps(value)

    def to_dict(self):
        """Converte para dict serializável."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'execution_time': self.execution_time,
            'links_total': self.links_total,
            'processed': self.processed,
            'downloaded': self.downloaded,
            'skipped': self.skipped,
            'report_path': self.report_path,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
        }
