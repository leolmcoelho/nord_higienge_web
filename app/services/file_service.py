"""Serviço para gerenciamento de arquivos."""
import os
from flask import send_from_directory, abort
from werkzeug.utils import secure_filename
from app.config import Config


class FileService:
    """Serviço para servir e gerenciar arquivos."""

    @staticmethod
    def serve_report(filename: str):
        """Serve relatório HTML gerado."""
        if not filename:
            abort(400)
        filepath = os.path.join(Config.REPORT_FOLDER, filename)
        if not os.path.exists(filepath):
            abort(404)
        return send_from_directory(Config.REPORT_FOLDER, filename)

    @staticmethod
    def serve_download(path: str):
        """Serve arquivo baixado."""
        if not path:
            abort(400)
        # Verificar segurança do path
        safe_path = os.path.normpath(path)
        if not safe_path.startswith(Config.DOWNLOAD_FOLDER):
            abort(403)
        if not os.path.exists(safe_path):
            abort(404)
        return send_from_directory(Config.DOWNLOAD_FOLDER, os.path.basename(safe_path))

    @staticmethod
    def get_download_tree(base_path: str = None) -> dict:
        """Retorna árvore de diretórios de downloads."""
        base_path = base_path or Config.DOWNLOAD_FOLDER
        tree = {}

        for root, dirs, files in os.walk(base_path):
            try:
                rel_path = os.path.relpath(root, base_path)
                tree[rel_path] = {
                    'dirs': sorted(dirs),
                    'files': [f for f in sorted(files) if not f.startswith('.')]
                }
            except ValueError:
                # path não está dentro de base_path
                continue

        return tree

    @staticmethod
    def save_uploaded_file(file, subfolder: str = '') -> str:
        """Salva arquivo enviado e retorna o caminho."""
        filename = secure_filename(file.filename)
        target_dir = os.path.join(Config.UPLOAD_FOLDER, subfolder)
        os.makedirs(target_dir, exist_ok=True)

        filepath = os.path.join(target_dir, filename)
        file.save(filepath)
        return filepath

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Verifica se o arquivo é permitido."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
