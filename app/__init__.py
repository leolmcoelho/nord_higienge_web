"""Flask app factory."""
import json

from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from app.config import Config, DevelopmentConfig

# Inicializa extensões
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")

# Configurar encoding JSON para UTF-8
class UTF8JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, str):
            return obj.encode('utf-8')
        return super().default(obj)

# Monkey patch para configurar encoding
def monkey_patch_json():
    from flask.json.provider import DefaultJSONProvider
    original_dumps = json.dumps

    def utf8_dumps(self, obj, **kwargs):
        kwargs['ensure_ascii'] = False
        return original_dumps(obj, **kwargs)

    DefaultJSONProvider.dumps = utf8_dumps

# Aplicar o monkey patch antes de criar a app
monkey_patch_json()


def create_app(config_class=DevelopmentConfig):
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Configuração
    app.config.from_object(config_class)
    Config.init_app(app)

    # Inicializa extensões
    db.init_app(app)
    socketio.init_app(app)

    # Registra blueprints
    from app.routes.api import api_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.socket_events import register_socket_events

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    register_socket_events(socketio)

    # Cria tabelas do banco
    with app.app_context():
        # Diagnostics: registrar informações de caminho/permissões antes de criar tabelas
        try:
            import os
            from pathlib import Path
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            try:
                app.logger.info('SQLALCHEMY_DATABASE_URI=%s', db_uri)
            except Exception:
                print('SQLALCHEMY_DATABASE_URI=', db_uri)

            # derivar caminho do sqlite se aplicável
            db_path = None
            if isinstance(db_uri, str) and db_uri.startswith('sqlite'):
                # sqlite:///relative or sqlite:////absolute
                if db_uri.startswith('sqlite:////'):
                    db_path = Path(db_uri.replace('sqlite:////', '/', 1))
                else:
                    db_path = Path(db_uri.replace('sqlite:///', '', 1))

            try:
                cwd = os.getcwd()
                uid = os.getuid() if hasattr(os, 'getuid') else None
                euid = os.geteuid() if hasattr(os, 'geteuid') else None
                gid = os.getgid() if hasattr(os, 'getgid') else None
                egid = os.getegid() if hasattr(os, 'getegid') else None
                info = {
                    'cwd': cwd,
                    'uid': uid,
                    'euid': euid,
                    'gid': gid,
                    'egid': egid,
                }
                try:
                    app.logger.info('Startup env: %s', info)
                except Exception:
                    print('Startup env:', info)
            except Exception as _:
                pass

            if db_path is not None:
                try:
                    exists = db_path.exists()
                    parent = db_path.parent
                    pstat = db_path.stat() if exists else None
                    parent_stat = parent.stat()
                    details = {
                        'db_path': str(db_path),
                        'exists': exists,
                        'db_mode': oct(pstat.st_mode) if pstat is not None else None,
                        'db_uid': pstat.st_uid if pstat is not None else None,
                        'db_gid': pstat.st_gid if pstat is not None else None,
                        'parent_mode': oct(parent_stat.st_mode),
                        'parent_uid': parent_stat.st_uid,
                        'parent_gid': parent_stat.st_gid,
                    }
                    try:
                        app.logger.info('DB file details: %s', details)
                    except Exception:
                        print('DB file details:', details)
                except Exception as _:
                    try:
                        app.logger.exception('Erro ao inspecionar arquivo DB')
                    except Exception:
                        print('Erro ao inspecionar arquivo DB')

        except Exception:
            pass

        try:
            db.create_all()
        except Exception as e:
            try:
                app.logger.exception('Falha ao criar tabelas do banco: %s', e)
            except Exception:
                print('Falha ao criar tabelas do banco:', e)

        # Seed de palavras-chave padrão (apenas se não houver palavras ativas)
        try:
            from app.services.keyword_service import KeywordService
            ks = KeywordService()
            existing = ks.get_active_keywords()
            if not existing:
                default_keywords = [
                    'Palavra-chave / Express',
                    'serviços de limpeza',
                    'fornecimento de consumíveis de higiene',
                    'limpeza de instalações sanitárias',
                    'produtos de higienização',
                    'desinfeção de espaços',
                    'serviços de lavandaria',
                    'higienização de roupa hospitalar',
                    'manutenção da higiene ambiental',
                    'limpeza técnica especializada',
                    'recolha e tratamento de resíduos',
                    'papel higiénico industrial',
                    'papel higiénico folha dupla',
                    'papel jumbo',
                    'rolo industrial',
                    'toalhas de papel em rolo contínuo',
                    'toalhas de mão em folha intercalada',
                    'papel reciclado',
                    'dispensador compatível',
                    'toalhetes húmidos descartáveis',
                    'toalhetes com loção hidratante',
                    'detergentes enzimáticos',
                    'produtos de limpeza com rotulagem ecológica',
                    'sabão líquido antibacteriano',
                    'recargas para doseador',
                    'produtos biocidas homologados',
                    'desinfetantes com certificação CE',
                    'sacos de lixo hospitalar',
                    'sacos de resíduos urbanos',
                    'sacos de resíduos perigosos',
                    'sacos biodegradáveis',
                    'codificação por cores',
                    'espessura mínima (≥ 50 micras)',
                    'capacidade (30L, 50L, 100L, 120L)',
                    'fraldas para adulto tipo cueca',
                    'fraldas com barreiras antifugas',
                    'fraldas absorção noturna',
                    'produtos para incontinência',
                    'pensos para incontinência ligeira',
                    'tamanhos M/L/XL',
                    'sistema de fecho reposicionável',
                    'compatível com pele sensível',
                    'aluguer de roupa hospitalar',
                    'lavagem, secagem e desinfeção',
                    'recolha e entrega porta-a-porta',
                    'rastreabilidade têxtil',
                    'ciclo de esterilização',
                    'normas RABC',
                    'pastilhas de desinfeção',
                    'pastilhas de desinfeção com detergente',
                    'luvas de exame em nitrilo',
                    'luvas de exame em látex',
                    'luvas de vinil',
                    'luvas de polietileno',
                    'luvas cirúrgicas estéreis',
                    'luvas descartáveis com certificação CE',
                    'gel de banho',
                    'sabonete líquido',
                    'Cera Autobrilhante Acrílica',
                    'Decapante de cera',
                    'Detergente multiusos (para lavar e encerar)',
                    'Detergente multiusos desinfectante (limpeza de superfícies) perfumado',
                    'Detergente multiusos desinfectante amoniacal',
                    'Esfregão de arame redondo',
                    'Lã de Aço nº 1',
                    'Palha de Aço nº 3',
                    'Palha de Aço nº 5',
                    'Esfregão verde COM esponja',
                    'Esfregão verde SEM esponja Grande',
                    'Esfregonas',
                    'Recargas Esfregonas',
                    'Esfregona ecológica microfibras ( recarga )',
                    'Recarga de esfregona industrial para carro duplo silver',
                    'Cabos de esfregona cromado 140 cm',
                    'Espremedor de esfregona para balde',
                    'Balde c/espremedor de esfregona',
                    'Limpa móveis COM Óleo',
                    'Limpa móveis SEM Óleo',
                    'Mopas (45cm)',
                    'Mopas (45cm) Recargas',
                    'Mopas (60cm)',
                    'Mopas (60cm) Recargas',
                    'Pá do Lixo cabo alto',
                    'Panos de limpeza para o chão',
                    'Panos do pó',
                    'Pano microfibra 40x30 6 Panos',
                    'Pano de cozinha 50x70',
                    'Vassoura Macia - com cabo',
                    'Vassoura Rija - com cabo',
                    'Balde com pedal 8 lts',
                    'Balde com tampa vascolante 25 lts',
                    'Saboneteira em plastico para sabonete sólido',
                    'Blocos sanitários',
                    'Blocos sanitários - Recargas Duplas',
                    'Creme de limpeza c/ lixivia ( tipo Cif )',
                    'Gel lixivia sanitário',
                    'Limpeza, desinfeção e desincrustação de WC',
                    'Lixívia',
                    'Luvas menage ( S, M, L )',
                    'Pastilhas de cloro ( lixivia sólida )',
                    'Pastilhas para urinol',
                    'Piaçaba com suporte',
                    'Piaçaba simples',
                    'Ácido muriático',
                    'Creolina',
                    'Benzina',
                    'Desentupidor de canos',
                    'Soda cáustica',
                    'sabonetes',
                    'Ambientador aerosol',
                    'Toush Fresh Dispersor/Recarga - Ambientador',
                    'Toush Fresh Recarga - Ambientador',
                    'Detergente de loiça',
                    'Detergente Maq. Loiça - capsulas +/- 30 doses',
                    'Detergente de roupa',
                    'Sabão pequeno (+/- 100 grs )',
                    'Dispensador/Sabonete Gel',
                    'Sabão barra ( azul e branco )',
                    'Toalhitas humedecidas para limpar monitores e equipamentos informáticos',
                    'Limpa vidros',
                    'Guia metálica c/borracha - 35 cm',
                    'Punho limpa vidros',
                    'Suporte plastico peluche - 35 cm',
                    'Peluxe simples - 35 cm',
                    'Cabo telescópio 2x1,2m=2,4 mts',
                    'Cabo telescópio 2x1,5m=3 mts',
                    'Sacos do lixo 60x80 - 0,6 a 0,8 micras espessura',
                    'Sacos do lixo 80x1,20 - 0,6 a 0,8 micras espessura',
                    'Sacos do lixo 97x1,30 - 0,6 a 0,8 micras espessura',
                    'Sacos de plástico cristal 120x150 cm c/fole de 20 cm c/ espessura de 0,6 ( 80+20+20x150cm )',
                    'Sacos do lixo de 30L',
                    'Sacos do lixo de 50L',
                    'Cabo de Alumínio Anodizado 1,55 Mt p/ vassoura',
                    'Luvas de Nitrilo Universais S/Pó (Cx c/100 Unidades Forte)',
                    'Balde 12 Lt C/ Espremedor',
                    'Pá de Lixo C/Borracha e Cabo',
                    'Pano Microfibra Cores 40x40 (Pack de 6 Unidades)',
                    'Saco Lixo BD 60x100 Cm',
                    'Saco Lixo BD 52x60, 30 Litros Extra Forte Resistente (Rolos c/40 Unidades)',
                    'Saco Lixo BD 60x80, 50 Litros Extra Forte Resistente (Rolos c/36 Unidades)',
                    'Saco Lixo BD 80x90, 100 Litros Extra Forte Resistente (Rolos c/10 Unidades)',
                    'Saco Lixo BD 90x130, 200 Litros Forte (1unid = 10kg)',
                    'Vassoura Doméstica S/Cabo',
                    'Vassoura Para Exterior 3 Cordões',
                    'Guardanapos Papel 33x33 Folha dupla (Maço 100 unid.)',
                    'Guardanapos Papel Zig/Zag (Bar) (1cx = 8 000 unid)',
                    'Toalhas 30x45 Tabuleiro (1 Cx = 1 000 unid.)',
                    'Sacos de Papel S01 P/Talheres (1 Cx = 2 000 unid)',
                    'Rolos Cozinha Industriais (TNT – emb. de 2 rolos 1.6)',
                    'Esfregão Verde (em rolo de 6m)',
                    'Toalhetes Zig/Zag Suave 2 folhas 21x25 (1 Cx = 20 Maços (160f) = 3 200 folhas)',
                    'Papel Higiénico Rolos (1 emb = 12 rolos – 180 mt)',
                    'Esfregões salva unhas (1cx = 10 unid)',
                    'Esfregona Especial – Microfibras 100% (1cx = 12 unid.– 250 gr)',
                    'Esfregona industrial - Microfibras 100%',
                    'Toucas para cabelo (cozinha) (1cx = 100 unid.)',
                    'Sacos de Papel S03 P/Sandes (1 cx = 1 000 unid.)',
                    'Panos de cozinha em tecido',
                    'Copos de papel 180 ml (Pack 50 unid)',
                    'Copos de papel 90 ml (Pack 100 unid)',
                    'Recarga de mopa microfibras 100cm',
                    'Desinfestação - controlo de baratas, formigas e ratos',
                    'AQUISIÇÃO DE DETERGENTES PARA MÁQUINAS DE LAVAGEM DE DISPOSITIVOS MÉDICOS (INSTRUMENTAL CIRÚRGICO)',
                    'DETERGENTES PARA MÁQUINAS REPROCESSAMENTO DE ENDOSCÓPIOS',
                    'Detergente p/máquinas de reproc. endosc. Flexíveis compt. c/modelo EW1/1AER',
                    'Desinfetante/esterilizador p/maquinas reproc. endosc. Flexíveis compt. c/modelo EW1/1AER',
                    'Ativador p/maquinas reproc. endosc. Flexíveis compt. c/modelo EW1/1AER',
                    'AQUISIÇÃO DE MATERIAL DE INCONTINÊNCIA',
                    'Fralda Adulto S (CINTURA 50-85 CM)',
                    'papel de marquesa',
                    'batas cirúrgicas',
                    'BATAS CIRÚRGICAS E OUTRO MATERIAL',
                    'Pastilhas de Limpeza e Desinfeção',
                    'Toalhetes de Limpeza e Desinfeção',
                    'Sacos de Plástico',
                    'Produtos para tratamento de águas',
                    'Produtos para higiene de piscinas',
                    'Lixívia em pastilhas',
                    'Papel variado',
                    'Acessórios de limpeza',
                    'Contentores de resíduos vários tamanhos com pedal',
                    'Contentores de resíduos vários tamanhos sem pedal',
                    'Dispensadores de luvas',
                    'Dispensadores de aventais',
                    'Solução hidroalcoólica dermoprotetora higiene mãos gel Fr',
                    'Solução hidroalcoólica dermoprotetora higiene mãos gel Fr doseador',
                    'Solução hidroalcoólica desinfeção cirúrgica mãos gel Fr Disp Autom',
                    'Toalhetes desinfetantes e antissépticos isentos de álcool Emb',
                    'Desinfetante atmosférico spray Fr 500 ml',
                    'Sacos de congelação',
                    'Guardanapo',
                    'Material geriátrico',
                    'Camas articuladas',
                    'Canadianas',
                    'Colchões anti-escaras',
                    'Cadeiras de rodas',
                    'Almofadas',
                    'Material de limpeza',
                    'Limpa vidros',
                    'Panos de cozinha de chão',
                ]
                for kw in default_keywords:
                    try:
                        ks.add_keyword(kw)
                    except Exception:
                        try:
                            app.logger.exception('Falha ao inserir keyword: %s', kw)
                        except Exception:
                            pass
        except Exception:
            try:
                app.logger.exception('Erro ao rodar seed de palavras-chave')
            except Exception:
                pass

    return app
