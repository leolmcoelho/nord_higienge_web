"""Script para executar o servidor Flask de desenvolvimento."""
import os

from dotenv import load_dotenv

from app import create_app, socketio

# Carrega variáveis de ambiente
load_dotenv()

# Cria a aplicação
app = create_app()


if __name__ == '__main__':
    # Executa o servidor Flask com Socket.IO
    # For development: disable reloader and debug to avoid worker/process
    # restarts that break long-running WebDriver sessions.
    socketio.run(
        app,
        host=os.environ.get('FLASK_HOST', '0.0.0.0'),
        port=int(os.environ.get('FLASK_PORT', 5000)),
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )
