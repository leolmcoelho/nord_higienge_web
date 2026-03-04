"""Rotas do Dashboard."""
import os
from flask import Blueprint, render_template
from app.services.job_service import JobService
from app.services.keyword_service import KeywordService


dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Página inicial do dashboard."""
    job_service = JobService()
    recent_jobs = job_service.list_jobs(limit=5)
    stats = job_service.get_dashboard_stats()

    # Credenciais padrão do ambiente
    default_credentials = {
        'vortal_user': os.environ.get('VORTAL_USER', ''),
        'vortal_password': os.environ.get('VORTAL_PASSWORD', ''),
        'acingov_user': os.environ.get('ACINGOV_USER', ''),
        'acingov_password': os.environ.get('ACINGOV_PASSWORD', ''),
    }

    return render_template('dashboard.html',
                       recent_jobs=recent_jobs,
                       stats=stats,
                       **default_credentials)


@dashboard_bp.route('/jobs')
def jobs_page():
    """Página de lista de jobs."""
    job_service = JobService()
    jobs = job_service.list_jobs(limit=50)
    return render_template('jobs.html', jobs=jobs)


@dashboard_bp.route('/reports')
def reports_page():
    """Página de relatórios."""
    job_service = JobService()
    completed_jobs = job_service.list_jobs(status='completed', limit=100)
    return render_template('reports.html', jobs=completed_jobs)


@dashboard_bp.route('/items')
def items_page():
    """Página de itens extraídos."""
    job_service = JobService()
    items = job_service.list_items(limit=100)
    return render_template('items.html', items=items)


@dashboard_bp.route('/config')
def config_page():
    """Página de configuração."""
    keyword_service = KeywordService()
    keywords = keyword_service.get_active_keywords()

    # Credenciais padrão do ambiente
    default_credentials = {
        'vortal_user': os.environ.get('VORTAL_USER', ''),
        'acingov_user': os.environ.get('ACINGOV_USER', ''),
    }

    return render_template('config.html',
                       keywords=keywords,
                       **default_credentials)
