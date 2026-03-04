"""Tarefas Celery para execução do pipeline de automação."""
import logging
import os
import traceback
from datetime import datetime

from app import socketio
from app.services.credential_service import CredentialService
from app.services.job_service import JobService
from app.tasks.celery_app import celery


def emit_progress(job_uuid: str, message: str):
    """Emite evento de progresso via Socket.IO."""
    socketio.emit('job_progress', {
        'job_uuid': job_uuid,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }, room=job_uuid)


def emit_error(job_uuid: str, error: str, traceback_str: str = None):
    """Emite evento de erro via Socket.IO."""
    socketio.emit('job_failed', {
        'job_uuid': job_uuid,
        'error': error,
        'traceback': traceback_str or ''
    }, room=job_uuid)


def emit_completion(job_uuid: str, summary: dict):
    """Emite evento de conclusão via Socket.IO."""
    socketio.emit('job_completed', {
        'job_uuid': job_uuid,
        'summary': summary
    }, room=job_uuid)


@celery.task(bind=True, name='tasks.run_extraction_pipeline')
def run_extraction_pipeline(self, job_uuid: str, config: dict):
    """
    Tarefa Celery que executa o pipeline de extração.

    Esta tarefa é executada assincronamente pelo Celery worker e
    comunica o progresso via Socket.IO.
    """
    # Garante que qualquer acesso ao Flask/SQLAlchemy ocorra dentro do
    # application context da aplicação Flask. Mantemos o contexto durante
    # toda a execução para que callbacks que atualizam o DB funcionem.
    from app import create_app

    app = create_app()

    try:
        with app.app_context():
            # Instanciar serviços que dependem do contexto (ex: DB)
            job_service = JobService()
            cred_service = CredentialService()

            # configurar logger por job (arquivo em logs/job_<uuid>.log)
            # usar raiz do projeto em vez de CWD (workers podem ter CWD diferente)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            logs_dir = os.path.join(project_root, 'logs')
            try:
                os.makedirs(logs_dir, exist_ok=True)
            except Exception:
                pass
            job_log_path = os.path.join(logs_dir, f'job_{job_uuid}.log')
            # garantir arquivo criado (FileHandler geralmente cria, mas escrevemos um byte para forçar permissões)
            try:
                open(job_log_path, 'a', encoding='utf-8').close()
            except Exception:
                # fallback para /tmp se não for possível criar em repo
                try:
                    tmp_logs = os.path.join('/tmp', 'nord_logs')
                    os.makedirs(tmp_logs, exist_ok=True)
                    job_log_path = os.path.join(tmp_logs, f'job_{job_uuid}.log')
                    open(job_log_path, 'a', encoding='utf-8').close()
                except Exception:
                    job_log_path = None

            job_logger = logging.getLogger(f'job_{job_uuid}')
            job_logger.setLevel(logging.INFO)
            if job_log_path and not any(getattr(h, 'baseFilename', None) == job_log_path for h in job_logger.handlers):
                try:
                    fh = logging.FileHandler(job_log_path, encoding='utf-8')
                    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
                    job_logger.addHandler(fh)
                except Exception:
                    job_log_path = None
            # sempre adicionar StreamHandler para ver no output do worker
            if not any(isinstance(h, logging.StreamHandler) for h in job_logger.handlers):
                sh = logging.StreamHandler()
                sh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
                job_logger.addHandler(sh)

            # debug info: informar onde será escrito o log
            try:
                cwd = os.getcwd()
            except Exception:
                cwd = 'unknown'
            info_path = job_log_path or 'none'
            emit_progress(job_uuid, f'LOG_CWD: {cwd}')
            emit_progress(job_uuid, f'LOG_PATH: {info_path}')
            try:
                job_logger.info(f'Job logger configured. CWD={cwd} PATH={info_path}')
            except Exception:
                pass

            # Atualizar status para running (o método já define started_at)
            job_service.update_job_status(job_uuid, 'running')

            emit_progress(job_uuid, 'Iniciando pipeline de extração...')

            # Carregar credenciais do banco
            emit_progress(job_uuid, 'Carregando credenciais...')
            vortal_creds = cred_service.get_credentials('vortal')
            acingov_creds = cred_service.get_credentials('acingov')

            # Descriptografar senhas
            vortal_user = vortal_creds['username'] if vortal_creds else None
            vortal_pass = vortal_creds['password'] if vortal_creds else None
            acingov_user = acingov_creds['username'] if acingov_creds else None
            acingov_pass = acingov_creds['password'] if acingov_creds else None

            # Importar o módulo de automação (feito aqui para evitar circular import)
            import sys
            sys.path.insert(0, '/mnt/dados/projetos/nord_higiene_web/automation')

            # Se não foi fornecido um arquivo de keywords, gerar um temporário
            # a partir das keywords ativas no banco para permitir execução E2E.
            if not config.get('keywords_file'):
                try:
                    import pandas as _pd

                    from app.services.keyword_service import KeywordService

                    ks = KeywordService()
                    words = ks.get_word_list()
                    if words:
                        tmp_dir = os.path.join('/tmp', 'nord_keywords')
                        os.makedirs(tmp_dir, exist_ok=True)
                        tmp_path = os.path.join(tmp_dir, f'keywords_{job_uuid}.xlsx')
                        df = _pd.DataFrame({'Palavra-chave / Expressão': words})
                        df.to_excel(tmp_path, index=False)
                        config['keywords_file'] = tmp_path
                except Exception:
                    # se falhar, seguimos e deixamos o automation levantar o erro
                    pass

            from automation.automation import run_pipeline

            # Executar pipeline com callback de progresso
            emit_progress(job_uuid, 'Executando busca no DRE...')

            def status_hook(message: str):
                """Callback para atualizar progresso."""
                emit_progress(job_uuid, message)
                # Atualizar mensagem no banco
                try:
                    job_service.update_job_message(job_uuid, message)
                except Exception:
                    job_logger.exception('Falha ao atualizar job message')
                # Persistir log em tabela e arquivo
                try:
                    job = job_service.get_job(job_uuid)
                    if job:
                        job_service.add_log(job.id, 'INFO', message)
                except Exception:
                    job_logger.exception('Falha ao gravar log no DB')
                job_logger.info(message)

            # Executar o pipeline
            summary = run_pipeline(
                keywords_file=config.get('keywords_file'),
                sheet_name=config.get('sheet_name'),
                vortal_user=vortal_user,
                vortal_password=vortal_pass,
                acingov_user=acingov_user,
                acingov_password=acingov_pass,
                limit=config.get('limit'),
                headless=config.get('headless', True),
                use_word_boundaries=config.get('use_word_boundaries', True),
                status_hook=status_hook,
                report_format='html'
            )

            # Salvar resultados no banco
            emit_progress(job_uuid, 'Salvando resultados no banco...')
            job_logger.info('Salvando resultados no banco')
            job_service.save_job_results(job_uuid, summary)

            # Atualizar status para completed (o método já define completed_at)
            job_service.update_job_status(job_uuid, 'completed')

            # Emitir evento de conclusão
            emit_completion(job_uuid, summary)
            job_logger.info('Job completed')
            try:
                job = job_service.get_job(job_uuid)
                if job:
                    job_service.add_log(job.id, 'INFO', 'Job completed', extra=summary)
            except Exception:
                job_logger.exception('Falha ao gravar log de completion')

            # remover handlers
            for h in list(job_logger.handlers):
                try:
                    h.close()
                    job_logger.removeHandler(h)
                except Exception:
                    pass

            return summary
    except Exception as e:
        # Capturar erro
        error_msg = str(e)
        error_traceback = traceback.format_exc()

        # Atualizar job com erro (garantir contexto se ainda não houver)
        try:
            from app import create_app as _create_app
            _app = _create_app()
            with _app.app_context():
                job_service.update_job_error(job_uuid, error_msg, error_traceback)
                try:
                    job = job_service.get_job(job_uuid)
                    if job:
                        job_service.add_log(job.id, 'ERROR', error_msg, extra={'traceback': error_traceback})
                except Exception:
                    pass
        except Exception:
            # Se falhar, apenas logamos e continuamos para emitir o evento
            try:
                logging.exception('Falha ao atualizar job com erro')
            except Exception:
                pass

        # Emitir evento de erro
        emit_error(job_uuid, error_msg, error_traceback)

        # Relançar para Celery
        raise


@celery.task(name='tasks.cancel_extraction_job')
def cancel_extraction_job(job_uuid: str):
    """Cancela um job em execução."""
    from app import celery as celery_app

    # Operações que acessam o DB precisam de application context
    from app import create_app

    app = create_app()
    with app.app_context():
        job_service = JobService()
        job = job_service.get_job(job_uuid)

        if job and job.task_id:
            # Revogar a task Celery
            celery_app.control.revoke(job.task_id, terminate=True)
            job_service.update_job_status(job_uuid, 'cancelled')
            return {'status': 'cancelled', 'job_uuid': job_uuid}

        return {'error': 'Job not found', 'job_uuid': job_uuid}
