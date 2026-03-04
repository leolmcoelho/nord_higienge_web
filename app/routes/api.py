"""Rotas da API REST."""
import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file, abort
from app.tasks.pipeline import run_extraction_pipeline
from app.services.job_service import JobService
from app.services.credential_service import CredentialService
from app.services.keyword_service import KeywordService
from app.services.file_service import FileService


api_bp = Blueprint('api', __name__, url_prefix='/api')


# Job Management
@api_bp.route('/jobs', methods=['POST'])
def create_job():
    """Cria um novo job de extração."""
    config = request.json

    # Valida campos obrigatórios
    if not config.get('vortal_user') or not config.get('vortal_password'):
        return jsonify({'error': 'Vortal credentials required'}), 400

    # Salva credenciais
    cred_service = CredentialService()
    cred_service.save_credentials('vortal',
                              config['vortal_user'],
                              config['vortal_password'])
    if config.get('acingov_user') and config.get('acingov_password'):
        cred_service.save_credentials('acingov',
                                  config['acingov_user'],
                                  config['acingov_password'])

    # Cria registro do job
    job_service = JobService()
    job_id = job_service.create_job(config)

    # Obtém o job criado para pegar o UUID
    job = job_service.get_job_by_id(job_id)
    job_uuid = job.uuid if job else str(uuid.uuid4())

    # Inicia task Celery
    task = run_extraction_pipeline.apply_async(args=[job_uuid, config])

    return jsonify({
        'job_id': job_id,
        'job_uuid': job_uuid,
        'task_id': task.id,
        'status': 'pending'
    }), 201


@api_bp.route('/jobs/<job_uuid>', methods=['GET'])
def get_job(job_uuid):
    """Retorna status e detalhes do job."""
    job_service = JobService()
    job = job_service.get_job(job_uuid)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())


@api_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """Lista todos os jobs com filtros opcionais."""
    job_service = JobService()
    status_filter = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    jobs = job_service.list_jobs(status=status_filter, limit=limit, offset=offset)
    return jsonify([job.to_dict() for job in jobs])


@api_bp.route('/jobs/<job_uuid>/cancel', methods=['POST'])
def cancel_job(job_uuid):
    """Cancela um job em execução."""
    from app.tasks.celery_app import celery
    job_service = JobService()
    job = job_service.get_job(job_uuid)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job.status not in ['pending', 'running']:
        return jsonify({'error': 'Job cannot be cancelled'}), 400

    # Revoga task Celery
    celery.control.revoke(job.config.get('task_id', ''), terminate=True)

    job_service.update_job_status(job_uuid, 'cancelled')
    return jsonify({'status': 'cancelled'})


@api_bp.route('/jobs/stats', methods=['GET'])
def get_jobs_stats():
    """Retorna estatísticas dos jobs."""
    job_service = JobService()
    stats = job_service.get_dashboard_stats()
    return jsonify(stats)


@api_bp.route('/jobs/<job_uuid>/logs', methods=['GET'])
def get_job_logs(job_uuid):
    """Retorna logs de um job."""
    job_service = JobService()
    limit = request.args.get('limit', 100, type=int)
    logs = job_service.get_job_logs_by_uuid(job_uuid, limit=limit)
    return jsonify([log.to_dict() for log in logs])


# Items
@api_bp.route('/items', methods=['GET'])
def list_items():
    """Lista itens extraídos com filtros."""
    job_service = JobService()
    downloaded = request.args.get('downloaded', type=bool)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    limit = request.args.get('limit', 100, type=int)

    items = job_service.list_items(
        downloaded=downloaded,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )
    return jsonify([item.to_dict() for item in items])


@api_bp.route('/jobs/<job_uuid>/items', methods=['GET'])
def get_job_items(job_uuid):
    """Retorna itens de um job específico."""
    job_service = JobService()
    items = job_service.get_job_items(job_uuid)
    return jsonify([item.to_dict() for item in items])


# Credentials
@api_bp.route('/credentials', methods=['GET'])
def get_credentials():
    """Retorna credenciais armazenadas (mascaradas)."""
    cred_service = CredentialService()
    creds = cred_service.get_all_credentials()
    # Não retorna senhas
    return jsonify(creds)


@api_bp.route('/credentials', methods=['POST'])
def update_credentials():
    """Atualiza credenciais armazenadas."""
    data = request.json
    cred_service = CredentialService()

    if 'vortal' in data:
        cred_service.save_credentials('vortal',
                                  data['vortal'].get('username', ''),
                                  data['vortal'].get('password', ''))
    if 'acingov' in data:
        cred_service.save_credentials('acingov',
                                  data['acingov'].get('username', ''),
                                  data['acingov'].get('password', ''))

    return jsonify({'status': 'updated'})


# Keywords
@api_bp.route('/keywords', methods=['GET'])
def get_keywords():
    """Retorna palavras-chave ativas."""
    keyword_service = KeywordService()
    keywords = keyword_service.get_active_keywords()
    return jsonify([kw.word for kw in keywords])


@api_bp.route('/keywords', methods=['POST'])
def add_keyword():
    """Adiciona uma palavra-chave."""
    data = request.json
    keyword_service = KeywordService()
    keyword = keyword_service.add_keyword(
        word=data.get('word', ''),
        source_file=data.get('source_file')
    )
    return jsonify(keyword.to_dict())


@api_bp.route('/keywords/upload', methods=['POST'])
def upload_keywords():
    """Faz upload de arquivo de palavras-chave."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    file_service = FileService()
    if not file_service.is_allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Salva arquivo
    filepath = file_service.save_uploaded_file(file)

    # Carrega palavras-chave
    keyword_service = KeywordService()
    count = keyword_service.load_keywords_from_file(
        filepath,
        sheet_name=request.form.get('sheet_name', 0)
    )

    return jsonify({
        'status': 'uploaded',
        'filename': file.filename,
        'count': count
    })


@api_bp.route('/reports/<path:filename>', methods=['GET'])
def get_report(filename):
    """Serve um arquivo de relatório gerado."""
    base_dir = os.path.join(current_app.root_path, '..', 'relatorio')
    base_dir = os.path.realpath(base_dir)
    full_path = os.path.realpath(os.path.join(base_dir, filename))
    # Protege contra path traversal
    if not full_path.startswith(base_dir):
        abort(403)
    if not os.path.isfile(full_path):
        abort(404)
    return send_file(full_path, mimetype='text/html')
