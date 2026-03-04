"""Serviço para gerenciamento de jobs de extração."""
import json
import uuid
from datetime import datetime
from app.models.job import ExtractionJob
from app.models.item import ExtractedItem
from app.models.job_log import JobLog
from app import db


class JobService:
    """Serviço para operações CRUD de jobs."""

    def create_job(self, config: dict) -> int:
        """Cria um novo job de extração."""
        job = ExtractionJob(
            uuid=str(uuid.uuid4()),
            config=config,
            status='pending',
        )
        db.session.add(job)
        db.session.commit()
        return job.id

    def get_job(self, job_uuid: str) -> ExtractionJob:
        """Retorna um job pelo UUID."""
        return ExtractionJob.query.filter_by(uuid=job_uuid).first()

    def get_job_by_id(self, job_id: int) -> ExtractionJob:
        """Retorna um job pelo ID."""
        return ExtractionJob.query.get(job_id)

    def list_jobs(self, status: str = None, limit: int = 50, offset: int = 0) -> list[ExtractionJob]:
        """Lista jobs com filtros opcionais."""
        query = ExtractionJob.query
        if status:
            query = query.filter_by(status=status)
        return query.order_by(ExtractionJob.created_at.desc()).offset(offset).limit(limit).all()

    def update_job_status(self, job_uuid: str, status: str) -> None:
        """Atualiza status do job."""
        job = self.get_job(job_uuid)
        if job:
            job.status = status
            if status == 'running' and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in ['completed', 'failed', 'cancelled']:
                job.completed_at = datetime.utcnow()
                if job.started_at:
                    job.execution_time = (job.completed_at - job.started_at).total_seconds()
            db.session.commit()

    def update_job_message(self, job_uuid: str, message: str) -> None:
        """Atualiza última mensagem do job (log simples)."""
        # Em uma implementação completa, isso poderia salvar em uma tabela de logs
        pass

    def update_job_error(self, job_uuid: str, error_message: str, error_traceback: str) -> None:
        """Atualiza erro do job."""
        job = self.get_job(job_uuid)
        if job:
            job.status = 'failed'
            job.error_message = error_message
            job.error_traceback = error_traceback
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.execution_time = (job.completed_at - job.started_at).total_seconds()
            db.session.commit()

    def save_job_results(self, job_uuid: str, summary: dict) -> None:
        """Salva resultados do job."""
        job = self.get_job(job_uuid)
        if job:
            job.links_total = summary.get('links_total', 0)
            job.processed = summary.get('processed', 0)
            job.downloaded = summary.get('downloaded', 0)
            job.skipped = summary.get('skipped', 0)
            job.report_path = summary.get('report_path')

            # Salvar itens extraídos
            dates_processed = summary.get('dates_processed', [])
            for date_info in dates_processed:
                processing_date = date_info.get('date')
                opportunities = date_info.get('opportunities', [])
                for opp in opportunities:
                    item = ExtractedItem(
                        job_id=job.id,
                        title=opp.get('title', ''),
                        local=opp.get('local', ''),
                        dre_link=opp.get('dre_link', ''),
                        portal_url=opp.get('portal_url', ''),
                        portal_type=self._infer_portal_type(opp.get('portal_url', '')),
                        downloaded=opp.get('downloaded', False),
                        skipped=not opp.get('downloaded', False),
                        keywords_list=opp.get('keywords', []),
                        processing_date=datetime.strptime(processing_date, '%Y-%m-%d').date() if processing_date else datetime.utcnow().date(),
                    )
                    db.session.add(item)

            db.session.commit()

    def get_dashboard_stats(self) -> dict:
        """Retorna estatísticas para o dashboard."""
        total_jobs = ExtractionJob.query.count()
        active_jobs = ExtractionJob.query.filter(ExtractionJob.status == 'running').count()
        today = datetime.utcnow().date()
        downloads_today = ExtractedItem.query.filter(
            ExtractedItem.downloaded == True,
            ExtractedItem.processing_date >= today
        ).count()

        completed_jobs = ExtractionJob.query.filter(ExtractionJob.status == 'completed').count()
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        return {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'downloads_today': downloads_today,
            'success_rate': round(success_rate, 1),
        }

    def list_items(self, downloaded: bool = None, date_from: str = None, date_to: str = None, limit: int = 100) -> list[ExtractedItem]:
        """Lista itens extraídos com filtros."""
        query = ExtractedItem.query
        if downloaded is not None:
            query = query.filter_by(downloaded=downloaded)
        if date_from:
            try:
                query = query.filter(ExtractedItem.processing_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
            except ValueError:
                pass
        if date_to:
            try:
                query = query.filter(ExtractedItem.processing_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
            except ValueError:
                pass
        return query.order_by(ExtractedItem.processing_date.desc()).limit(limit).all()

    def add_log(self, job_id: int, level: str, message: str, extra: dict = None) -> None:
        """Adiciona um log ao job."""
        log = JobLog(
            job_id=job_id,
            level=level,
            message=message,
            extra=extra
        )
        db.session.add(log)
        db.session.commit()

    def get_job_logs(self, job_id: int, limit: int = 100) -> list[JobLog]:
        """Retorna logs de um job."""
        return JobLog.query.filter_by(job_id=job_id).order_by(JobLog.timestamp.desc()).limit(limit).all()

    def get_job_logs_by_uuid(self, job_uuid: str, limit: int = 100) -> list[JobLog]:
        """Retorna logs de um job pelo UUID."""
        job = self.get_job(job_uuid)
        if not job:
            return []
        return self.get_job_logs(job.id, limit)

    def get_job_items(self, job_uuid: str) -> list[ExtractedItem]:
        """Retorna itens de um job específico."""
        job = self.get_job(job_uuid)
        if not job:
            return []
        return ExtractedItem.query.filter_by(job_id=job.id).all()

    @staticmethod
    def _infer_portal_type(portal_url: str) -> str:
        """Infere o tipo do portal a partir da URL."""
        portal_url = portal_url.lower()
        if 'vortal' in portal_url:
            return 'vortal'
        elif 'acingov' in portal_url:
            return 'acingov'
        return 'unknown'
