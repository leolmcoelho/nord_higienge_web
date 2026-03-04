"""Configuração do Celery."""
from celery import Celery

from app.config import Config

# Instância do Celery
celery = Celery(
    'nord_higiene_web',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND
)

# Configurações do Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Lisbon',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 2,  # 2 horas max
    task_soft_time_limit=3600 * 1.5,  # 1.5 horas soft
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Processar um job por vez
)

# Auto-discover tasks
celery.autodiscover_tasks(['app.tasks'])

# Garantir que os módulos de tasks sejam importados ao iniciar o Celery
# (ajuda quando o worker não descobre tasks automaticamente em alguns ambientes)
try:
    import app.tasks.pipeline  # noqa: F401
except Exception:
    pass
