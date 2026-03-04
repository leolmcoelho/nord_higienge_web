"""Script para executar o Celery worker."""
from dotenv import load_dotenv
from app import create_app
from app.tasks.celery_app import celery

# Carrega variáveis de ambiente
load_dotenv()

# Cria o contexto da aplicação Flask
app = create_app()
app.app_context().push()

# Configura o Celery com a aplicação Flask
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Lisbon',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 2,  # 2 horas max
    task_soft_time_limit=3600 * 1.5,  # 1.5 horas soft
)


if __name__ == '__main__':
    celery.start()
