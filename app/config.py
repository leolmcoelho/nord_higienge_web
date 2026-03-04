"""Configuração da aplicação."""
import os
from pathlib import Path


class Config:
    """Configurações da aplicação."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

    # Diretório base do projeto
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR}/data/database.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Uploads
    UPLOAD_FOLDER = str(BASE_DIR / 'data' / 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

    # Downloads e Reports
    DOWNLOAD_FOLDER = str(BASE_DIR / 'data' / 'downloads')
    REPORT_FOLDER = str(BASE_DIR / 'data' / 'reports')

    # Encriptação
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'default-32-byte-key-change-me')

    # Selenium
    HEADLESS_DEFAULT = True
    SELENIUM_TIMEOUT = 180  # segundos

    @staticmethod
    def init_app(app):
        """Inicializa pastas necessárias."""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.REPORT_FOLDER, exist_ok=True)
        # Garantir diretórios principais
        data_dir = Config.BASE_DIR / 'data'
        logs_dir = Config.BASE_DIR / 'logs'
        os.makedirs(str(data_dir), exist_ok=True)
        os.makedirs(str(logs_dir), exist_ok=True)

        # Garantir que o arquivo de banco de dados exista e permissões corretas
        try:
            db_file = data_dir / 'database.db'
            if not db_file.exists():
                # cria arquivo vazio
                db_file.touch()
                try:
                    os.chmod(str(db_file), 0o666)
                except Exception:
                    pass
        except Exception as e:
            # Não falhar na inicialização se não for possível criar o arquivo
            try:
                app.logger.warning(f"Não foi possível criar o arquivo de BD: {e}")
            except Exception:
                pass

        # Normalizar SQLALCHEMY_DATABASE_URI se for sqlite com caminho relativo
        try:
            uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if isinstance(uri, str) and uri.startswith('sqlite:///'):
                tail = uri[len('sqlite:///'):]
                tail_path = Path(tail)
                if not tail_path.is_absolute():
                    abs_path = Config.BASE_DIR / tail
                    normalized = f"sqlite:///{abs_path}"
                    app.config['SQLALCHEMY_DATABASE_URI'] = normalized
                    try:
                        app.logger.info('Normalized SQLALCHEMY_DATABASE_URI to %s', normalized)
                    except Exception:
                        print('Normalized SQLALCHEMY_DATABASE_URI to', normalized)
        except Exception:
            pass


class DevelopmentConfig(Config):
    """Configuração de desenvolvimento."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuração de produção."""
    DEBUG = False
