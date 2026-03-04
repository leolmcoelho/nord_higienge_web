# Nord Higiene Web - Sistema de Extração de Editais

Sistema web para automação de extração de editais de portais governamentais portugueses (DRE, Vortal, Acingov).

## Tecnologias

- **Flask** - Framework web
- **Celery** - Fila de tarefas assíncronas
- **Redis** - Message broker para Celery
- **SQLite** - Banco de dados
- **Flask-SocketIO** - Atualizações em tempo real
- **Selenium** - Automação de navegador

## Estrutura do Projeto

```
nord_higiene_web/
├── app/                      # Aplicação Flask
│   ├── models/               # Modelos do banco de dados
│   ├── routes/               # Rotas (API, Dashboard, etc.)
│   ├── tasks/                # Tarefas Celery
│   ├── services/             # Lógica de negócio
│   ├── templates/            # Templates HTML
│   ├── static/              # Arquivos estáticos (CSS, JS, imgs)
│   └── utils/               # Utilitários (encriptação, etc.)
├── automation/              # Módulos de automação existentes
├── data/                    # Dados da aplicação
│   ├── database.db          # Banco SQLite
│   ├── uploads/            # Arquivos enviados
│   ├── downloads/          # Arquivos baixados
│   └── reports/           # Relatórios gerados
├── logs/                   # Logs da aplicação
├── run_flask.py           # Servidor Flask
├── run_celery.py          # Worker Celery
├── run_redis.sh           # Inicialização Redis
└── requirements_web.txt   # Dependências
```

## Pré-requisitos

- Python 3.10+
- Redis server
- Google Chrome (para Selenium)
- pip (gerenciador de pacotes Python)

## Instalação

### 1. Clonar o projeto

```bash
cd /mnt/dados/projetos
git clone <repo-url> nord_higiene_web
cd nord_higiene_web
```

### 2. Instalar dependências Python

```bash
# Criar ambiente virtual (opcional mas recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements_web.txt
```

### 3. Instalar e iniciar Redis

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
./run_redis.sh
```

**macOS:**
```bash
brew install redis
redis-server
```

**Windows:**
- Baixar e instalar Redis para Windows
- Iniciar o servidor Redis

### 4. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar o arquivo .env com suas configurações
nano .env  # ou use seu editor preferido
```

Variáveis importantes:
- `SECRET_KEY` - Chave secreta para Flask (altere em produção!)
- `ENCRYPTION_KEY` - Chave para encriptação de senhas
- `REDIS_URL` - URL do servidor Redis (padrão: redis://localhost:6379/0)

### 5. Instalar Google Chrome (se necessário)

**Ubuntu/Debian:**
```bash
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable
```

**macOS:**
```bash
brew install --cask google-chrome
```

**Windows:**
- Baixar Google Chrome em https://www.google.com/chrome/

## Como Executar

### Desenvolvimento

**Terminal 1 - Redis:**
```bash
./run_redis.sh
```

**Terminal 2 - Celery Worker:**
```bash
source .venv/bin/activate
python run_celery.py
```

**Terminal 3 - Flask App:**
```bash
source .venv/bin/activate
python run_flask.py
```

A aplicação estará disponível em: http://localhost:5000

### Produção (usando systemd)

**1. Criar arquivo de serviço do Flask:**
```bash
sudo nano /etc/systemd/system/nord-higiene-flask.service
```

Conteúdo:
```ini
[Unit]
Description=Nord Higiene Flask App
After=network.target redis.service

[Service]
User=leonardo
WorkingDirectory=/mnt/dados/projetos/nord_higiene_web
Environment="PATH=/mnt/dados/projetos/nord_higiene_web/.venv/bin"
ExecStart=/mnt/dados/projetos/nord_higiene_web/.venv/bin/python run_flask.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Criar arquivo de serviço do Celery:**
```bash
sudo nano /etc/systemd/system/nord-higiene-celery.service
```

Conteúdo:
```ini
[Unit]
Description=Nord Higiene Celery Worker
After=network.target redis.service

[Service]
User=leonardo
WorkingDirectory=/mnt/dados/projetos/nord_higiene_web
Environment="PATH=/mnt/dados/projetos/nord_higiene_web/.venv/bin"
ExecStart=/mnt/dados/projetos/nord_higiene_web/.venv/bin/celery -A app.tasks.celery_app:celery worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

**3. Ativar e iniciar os serviços:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable nord-higiene-flask.service
sudo systemctl enable nord-higiene-celery.service
sudo systemctl start nord-higiene-flask.service
sudo systemctl start nord-higiene-celery.service
```

**4. Verificar status:**
```bash
sudo systemctl status nord-higiene-flask.service
sudo systemctl status nord-higiene-celery.service
```

## Uso da Aplicação

### 1. Configurar Credenciais

Acesse `/config` e configure as credenciais:
- Vortal (obrigatório)
- Acingov (opcional)

### 2. Configurar Palavras-chave

Carregue um arquivo Excel com as palavras-chave para busca de editais.

### 3. Iniciar Extração

No dashboard, clique em "Nova Extração" e configure:
- Data inicial
- Data final
- Limites de processamento
- Modo headless

### 4. Acompanhar Progresso

Acesse `/jobs` para acompanhar o progresso em tempo real.

### 5. Visualizar Relatórios

Acesse `/reports` para ver relatórios de extrações concluídas.

### 6. Baixar Documentos

Acesse `/items` para ver e baixar documentos extraídos.

## Troubleshooting

### Redis não inicia

**Erro:** `Could not connect to Redis at 127.0.0.1:6379`

**Solução:**
```bash
# Verificar se Redis está rodando
redis-cli ping
# Deve retornar: PONG

# Se não estiver rodando:
sudo systemctl start redis-server
# ou
redis-server
```

### Celery worker não conecta

**Erro:** `Error connecting to Redis`

**Solução:**
- Verifique se Redis está rodando
- Verifique a variável `REDIS_URL` no `.env`

### Selenium/Chrome falha

**Erro:** `WebDriverException`

**Solução:**
```bash
# Verificar Chrome instalado
google-chrome --version

# Verificar chromedriver
chromedriver --version

# Se necessário, atualizar o chromedriver
pip install --upgrade webdriver-manager
```

### Banco de dados não cria tabelas

**Solução:**
```bash
# Remover banco de dados e reiniciar
rm data/database.db
python run_flask.py  # As tabelas serão recriadas automaticamente
```

### Permissões negadas em downloads

**Solução:**
```bash
# Garantir permissões de escrita
chmod -R 755 data/
```

## Desenvolvimento

### Adicionar nova rota

1. Crie arquivo em `app/routes/`
2. Registre o blueprint em `app/__init__.py`
3. Crie template em `app/templates/`

### Adicionar novo modelo

1. Crie arquivo em `app/models/`
2. Herde de `db.Model`
3. Adicione campos e métodos
4. Rode o app para criar tabela automaticamente

### Adicionar nova tarefa Celery

1. Crie função decorada com `@celery.task` em `app/tasks/pipeline.py`
2. Chame usando `task.delay()` da API
3. Emita eventos via Socket.IO para atualizações

## Segurança

- Senhas são encriptadas com AES antes de serem salvas
- Use HTTPS em produção
- Altere `SECRET_KEY` em produção
- Use uma `ENCRYPTION_KEY` forte
- Configure rate limiting para APIs públicas
- Valide todos os inputs do usuário

## Suporte

Para problemas ou dúvidas, verifique:
1. Logs em `logs/`
2. Status dos serviços (`systemctl status`)
3. Logs do Celery worker
4. Logs do Flask app
