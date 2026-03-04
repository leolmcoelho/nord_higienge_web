"""Módulo para geração de relatórios em diferentes formatos."""

import datetime
import os
from typing import Literal

from logger import logger


def generate_report(
    summary: dict,
    output_dir: str = "relatorio",
    format: Literal["html", "md"] = "html"
) -> str:
    """Gera um relatório formatado com as estatísticas da execução.
    
    Args:
        summary: Dicionário com estatísticas da execução
        output_dir: Pasta onde o relatório será salvo
        format: Formato do relatório ("html" ou "md")
        
    Returns:
        Caminho do arquivo gerado
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if format.lower() == "html":
        return _generate_html_report(summary, output_dir)
    elif format.lower() == "md":
        return _generate_markdown_report(summary, output_dir)
    else:
        raise ValueError(f"Formato inválido: {format}. Use 'html' ou 'md'.")


def _generate_markdown_report(summary: dict, output_dir: str) -> str:
    """Gera relatório em Markdown."""
    timestamp = datetime.datetime.now()
    filename = f"relatorio_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.md"
    filepath = os.path.join(output_dir, filename)
    
    # Calcular totais
    total_links = summary.get('links_total', 0)
    total_processed = summary.get('processed', 0)
    total_downloaded = summary.get('downloaded', 0)
    total_skipped = summary.get('skipped', 0)
    dates_processed = summary.get('dates_processed', [])
    execution_time = summary.get('execution_time', 0)
    
    # Criar conteúdo do relatório
    content = f"""# 📊 Relatório de Processamento - Nord Higiene

**Data/Hora:** {timestamp.strftime('%d/%m/%Y às %H:%M:%S')}  
**Tempo de Execução:** {execution_time:.2f} segundos ({execution_time/60:.1f} minutos)

---

## 📈 Resumo Geral

| Métrica | Valor |
|---------|-------|
| 🔍 Oportunidades Encontradas (DRE) | **{total_links}** |
| ✅ Processadas no Vortal | **{total_processed}** |
| 📥 Downloads Realizados | **{total_downloaded}** |
| ⏭️ Puladas (fora da whitelist) | **{total_skipped}** |
| 📅 Datas Processadas | **{len(dates_processed)}** |

---

## 📅 Processamento por Data

"""
    
    # Detalhes por data
    for date_info in dates_processed:
        date = date_info.get('date', 'N/A')
        links_count = date_info.get('links_count', 0)
        opportunities = date_info.get('opportunities', [])
        
        content += f"""### 📆 {date}

**Oportunidades encontradas:** {links_count}

"""
        
        if opportunities:
            content += "| # | Entidade | Título | Status |\n"
            content += "|---|----------|--------|--------|\n"
            
            for idx, opp in enumerate(opportunities, 1):
                local = opp.get('local', 'N/A')
                title = opp.get('title', 'N/A')[:60] + ('...' if len(opp.get('title', '')) > 60 else '')
                status = '✅ Baixado' if opp.get('downloaded') else '⏭️ Pulado'
                content += f"| {idx} | {local} | {title} | {status} |\n"
            
            content += "\n"
        else:
            content += "_Nenhuma oportunidade relevante encontrada._\n\n"
    
    # Estatísticas por entidade
    content += """---

## 🏢 Estatísticas por Entidade

"""
    
    entity_stats = summary.get('entity_stats', {})
    if entity_stats:
        content += "| Entidade | Oportunidades | Downloads |\n"
        content += "|----------|---------------|----------|\n"
        
        for entity, stats in sorted(entity_stats.items(), key=lambda x: x[1]['total'], reverse=True):
            total = stats.get('total', 0)
            downloaded = stats.get('downloaded', 0)
            content += f"| {entity} | {total} | {downloaded} |\n"
    else:
        content += "_Nenhuma entidade processada._\n"
    
    # Palavras-chave mais encontradas
    content += """\n---

## 🔑 Palavras-chave Mais Encontradas

"""
    
    keyword_stats = summary.get('keyword_stats', {})
    if keyword_stats:
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        content += "| Palavra-chave | Ocorrências |\n"
        content += "|---------------|-------------|\n"
        
        for keyword, count in sorted_keywords:
            content += f"| {keyword} | {count} |\n"
    else:
        content += "_Nenhuma palavra-chave rastreada._\n"
    
    # Rodapé
    content += f"""\n---

## ℹ️ Informações Adicionais

- **Sistema:** Nord Higiene - Automação DRE + Vortal
- **Gerado em:** {timestamp.strftime('%d/%m/%Y às %H:%M:%S')}
- **Arquivo:** `{filename}`

---

_Relatório gerado automaticamente pelo sistema de automação Nord Higiene._
"""
    
    # Salvar arquivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"📄 Relatório Markdown gerado: {filepath}")
    return filepath


def _generate_whatsapp_message(summary: dict, output_dir: str, timestamp: datetime.datetime) -> str:
    """Gera arquivo de texto com mensagem formatada para WhatsApp."""
    filename = f"whatsapp_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    filepath = os.path.join(output_dir, filename)
    
    # Calcular totais
    total_links = summary.get('links_total', 0)
    total_processed = summary.get('processed', 0)
    total_downloaded = summary.get('downloaded', 0)
    total_skipped = summary.get('skipped', 0)
    dates_processed = summary.get('dates_processed', [])
    execution_time = summary.get('execution_time', 0)
    
    # Criar mensagem formatada
    message = f"""📊 *RELATÓRIO NORD HIGIENE*
Data: {timestamp.strftime('%d/%m/%Y às %H:%M')}
⏱️ Tempo: {execution_time/60:.1f} minutos

━━━━━━━━━━━━━━━━━━━━━

📈 *RESUMO GERAL*

🔍 Oportunidades Encontradas: *{total_links}*
✅ Processadas no Vortal: *{total_processed}*
📥 Downloads Realizados: *{total_downloaded}*
⏭️ Puladas: *{total_skipped}*
📅 Datas Processadas: *{len(dates_processed)}*

━━━━━━━━━━━━━━━━━━━━━

📅 *DETALHES POR DATA*

"""
    
    # Adicionar detalhes por data
    for date_info in dates_processed:
        date = date_info.get('date', 'N/A')
        links_count = date_info.get('links_count', 0)
        opportunities = date_info.get('opportunities', [])
        
        # Converter data para formato brasileiro
        try:
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            date_br = date_obj.strftime('%d/%m/%Y')
        except:
            date_br = date
        
        message += f"*{date_br}* - {links_count} oportunidade{'s' if links_count != 1 else ''}\n"
        
        if opportunities:
            for opp in opportunities:
                local = opp.get('local', 'N/A')
                title = opp.get('title', 'N/A')
                downloaded = opp.get('downloaded', False)
                status = '✅' if downloaded else '⏭️'
                
                # Truncar nome da entidade se muito longo
                if len(local) > 30:
                    local = local[:27] + '...'
                
                # Truncar título se muito longo
                if len(title) > 40:
                    title = title[:37] + '...'
                
                message += f"{status} {local}\n   → {title}\n\n"
        else:
            message += "_Nenhuma oportunidade encontrada_\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━\n\n🏢 *TOP ENTIDADES*\n\n"
    
    # Top entidades
    entity_stats = summary.get('entity_stats', {})
    if entity_stats:
        sorted_entities = sorted(entity_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
        for idx, (entity, stats) in enumerate(sorted_entities, 1):
            total = stats.get('total', 0)
            downloaded = stats.get('downloaded', 0)
            
            # Truncar nome da entidade
            if len(entity) > 25:
                entity = entity[:22] + '...'
            
            message += f"{idx}. {entity} - {total} ({downloaded} download{'s' if downloaded != 1 else ''})\n"
    else:
        message += "_Nenhuma entidade processada_\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━━\n\n🔑 *PALAVRAS-CHAVE MAIS ENCONTRADAS*\n\n"
    
    # Top palavras-chave
    keyword_stats = summary.get('keyword_stats', {})
    if keyword_stats:
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        for idx, (keyword, count) in enumerate(sorted_keywords, 1):
            message += f"{idx}. {keyword} ({count}x)\n"
    else:
        message += "_Nenhuma palavra-chave encontrada_\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━━\n\n_Relatório gerado automaticamente_\n_Sistema Nord Higiene - DRE + Vortal_"
    
    # Salvar arquivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(message)
    
    logger.info(f"💬 Mensagem WhatsApp gerada: {filepath}")
    return filepath


def _generate_html_report(summary: dict, output_dir: str) -> str:
    """Gera relatório em HTML."""
    timestamp = datetime.datetime.now()
    filename = f"relatorio_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.html"
    filepath = os.path.join(output_dir, filename)
    
    # Calcular totais
    total_links = summary.get('links_total', 0)
    total_processed = summary.get('processed', 0)
    total_downloaded = summary.get('downloaded', 0)
    total_skipped = summary.get('skipped', 0)
    dates_processed = summary.get('dates_processed', [])
    execution_time = summary.get('execution_time', 0)
    
    # Gerar tabelas de datas
    dates_html = ""
    for date_info in dates_processed:
        date = date_info.get('date', 'N/A')
        links_count = date_info.get('links_count', 0)
        opportunities = date_info.get('opportunities', [])
        
        dates_html += f"""
        <div class="date-section">
            <h3>📆 {date}</h3>
            <p><strong>Oportunidades encontradas:</strong> {links_count}</p>
        """
        
        if opportunities:
            dates_html += """
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Entidade</th>
                        <th>Título</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for idx, opp in enumerate(opportunities, 1):
                local = opp.get('local', 'N/A')
                title = opp.get('title', 'N/A')[:80] + ('...' if len(opp.get('title', '')) > 80 else '')
                downloaded = opp.get('downloaded')
                status = '✅ Baixado' if downloaded else '⏭️ Pulado'
                status_class = 'success' if downloaded else 'skipped'
                
                dates_html += f"""
                    <tr>
                        <td>{idx}</td>
                        <td>{local}</td>
                        <td>{title}</td>
                        <td class="{status_class}">{status}</td>
                    </tr>
                """
            
            dates_html += """
                </tbody>
            </table>
            """
        else:
            dates_html += '<p class="no-data"><em>Nenhuma oportunidade relevante encontrada.</em></p>'
        
        dates_html += "</div>"
    
    # Estatísticas por entidade
    entity_html = ""
    entity_stats = summary.get('entity_stats', {})
    if entity_stats:
        entity_html = """
        <table>
            <thead>
                <tr>
                    <th>Entidade</th>
                    <th>Oportunidades</th>
                    <th>Downloads</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for entity, stats in sorted(entity_stats.items(), key=lambda x: x[1]['total'], reverse=True):
            total = stats.get('total', 0)
            downloaded = stats.get('downloaded', 0)
            entity_html += f"""
                <tr>
                    <td>{entity}</td>
                    <td>{total}</td>
                    <td>{downloaded}</td>
                </tr>
            """
        
        entity_html += """
            </tbody>
        </table>
        """
    else:
        entity_html = '<p class="no-data"><em>Nenhuma entidade processada.</em></p>'
    
    # Palavras-chave
    keywords_html = ""
    keyword_stats = summary.get('keyword_stats', {})
    if keyword_stats:
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        keywords_html = """
        <table>
            <thead>
                <tr>
                    <th>Palavra-chave</th>
                    <th>Ocorrências</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for keyword, count in sorted_keywords:
            keywords_html += f"""
                <tr>
                    <td>{keyword}</td>
                    <td>{count}</td>
                </tr>
            """
        
        keywords_html += """
            </tbody>
        </table>
        """
    else:
        keywords_html = '<p class="no-data"><em>Nenhuma palavra-chave rastreada.</em></p>'
    
    # Template HTML completo
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório - Nord Higiene</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
            background: radial-gradient(ellipse at top left, rgba(90, 209, 255, 0.15), transparent 35%),
                        radial-gradient(ellipse at bottom right, rgba(197, 243, 107, 0.1), transparent 45%),
                        #071633;
            padding: 20px;
            color: #ecf6f7;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #081827;
            border: 1px solid #0f2a3a;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(120deg, #23d7b6, #4ce0c8);
            color: #0c0f14;
            padding: 40px;
            text-align: center;
            position: relative;
        }}
        
        header::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1), transparent 60%);
            pointer-events: none;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
            position: relative;
            z-index: 1;
        }}
        
        header h2 {{
            position: relative;
            z-index: 1;
        }}
        
        .meta {{
            font-size: 0.95em;
            opacity: 0.85;
            position: relative;
            z-index: 1;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .summary {{
            background: #0d1420;
            border: 1px solid #0f2a3a;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        
        .summary h2 {{
            color: #23d7b6;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: #11141b;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #23d7b6;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        .stat-card .label {{
            color: #9fb0bf;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .stat-card .value {{
            color: #ecf6f7;
            font-size: 2em;
            font-weight: bold;
        }}
        
        section {{
            margin-bottom: 40px;
        }}
        
        h2 {{
            color: #23d7b6;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #0f2a3a;
            font-size: 1.8em;
        }}
        
        h3 {{
            color: #4ce0c8;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: #0d1420;
            border: 1px solid #0f2a3a;
            border-radius: 10px;
            overflow: hidden;
        }}
        
        thead {{
            background: linear-gradient(120deg, #23d7b6, #4ce0c8);
            color: #0c0f14;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 700;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #0f2a3a;
            color: #ecf6f7;
        }}
        
        tbody tr:hover {{
            background: #11141b;
        }}
        
        .success {{
            color: #7ef0c9;
            font-weight: bold;
        }}
        
        .skipped {{
            color: #ffc107;
            font-weight: bold;
        }}
        
        .date-section {{
            background: #0d1420;
            border: 1px solid #0f2a3a;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .no-data {{
            color: #9fb0bf;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }}
        
        footer {{
            background: #0d1420;
            border-top: 1px solid #0f2a3a;
            padding: 30px;
            text-align: center;
            color: #9fb0bf;
        }}
        
        footer p {{
            margin: 5px 0;
        }}
        
        .footer-note {{
            margin-top: 15px;
            font-size: 0.9em;
            color: #6b7d8f;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Relatório de Processamento</h1>
            <h2>Nord Higiene</h2>
            <div class="meta">
                <p><strong>Data/Hora:</strong> {timestamp.strftime('%d/%m/%Y às %H:%M:%S')}</p>
                <p><strong>Tempo de Execução:</strong> {execution_time:.2f}s ({execution_time/60:.1f} min)</p>
            </div>
        </header>
        
        <div class="content">
            <div class="summary">
                <h2>📈 Resumo Geral</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">🔍 Oportunidades Encontradas</div>
                        <div class="value">{total_links}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">✅ Processadas no Vortal</div>
                        <div class="value">{total_processed}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">📥 Downloads Realizados</div>
                        <div class="value">{total_downloaded}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">⏭️ Puladas</div>
                        <div class="value">{total_skipped}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">📅 Datas Processadas</div>
                        <div class="value">{len(dates_processed)}</div>
                    </div>
                </div>
            </div>
            
            <section>
                <h2>📅 Processamento por Data</h2>
                {dates_html}
            </section>
            
            <section>
                <h2>🏢 Estatísticas por Entidade</h2>
                {entity_html}
            </section>
            
            <section>
                <h2>🔑 Palavras-chave Mais Encontradas</h2>
                {keywords_html}
            </section>
        </div>
        
        <footer>
            <p><strong>Sistema:</strong> Nord Higiene - Automação DRE + Vortal</p>
            <p><strong>Arquivo:</strong> {filename}</p>
            <p class="footer-note">Relatório gerado automaticamente pelo sistema de automação Nord Higiene.</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # Salvar arquivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Gerar também arquivo de WhatsApp
    whatsapp_path = _generate_whatsapp_message(summary, output_dir, timestamp)
    
    logger.info(f"📄 Relatório HTML gerado: {filepath}")
    logger.info(f"💬 Mensagem WhatsApp gerada: {whatsapp_path}")
    return filepath


if __name__ == "__main__":
    # Dados de exemplo para visualização
    sample_summary = {
        "links_total": 15,
        "processed": 12,
        "downloaded": 8,
        "skipped": 4,
        "execution_time": 245.67,
        "dates_processed": [
            {
                "date": "2026-01-26",
                "links_count": 7,
                "opportunities": [
                    {
                        "local": "Unidade Local de Saúde do Oeste, E.P.E.",
                        "title": "Aquisição de material de consumo clínico para o serviço de urgência",
                        "downloaded": True,
                        "keywords": ["material", "consumo", "clínico"]
                    },
                    {
                        "local": "Município de Torres Vedras",
                        "title": "Fornecimento de produtos de limpeza e higienização",
                        "downloaded": True,
                        "keywords": ["limpeza", "higienização", "produtos"]
                    },
                    {
                        "local": "Câmara Municipal de Caldas da Rainha",
                        "title": "Aquisição de equipamentos de proteção individual (EPI)",
                        "downloaded": False,
                        "keywords": ["epi", "proteção"]
                    },
                    {
                        "local": "Unidade Local de Saúde da Guarda, E.P.E.",
                        "title": "Serviços de higiene e limpeza hospitalar pelo período de 24 meses",
                        "downloaded": True,
                        "keywords": ["higiene", "limpeza", "hospitalar"]
                    }
                ]
            },
            {
                "date": "2026-01-25",
                "links_count": 5,
                "opportunities": [
                    {
                        "local": "Unidade Local de Saúde de Coimbra",
                        "title": "Fornecimento de material descartável para blocos operatórios",
                        "downloaded": True,
                        "keywords": ["material", "descartável", "bloco operatório"]
                    },
                    {
                        "local": "Município de Leiria",
                        "title": "Aquisição de rolos de sacos de plástico pretos para resíduos I e II",
                        "downloaded": True,
                        "keywords": ["sacos", "resíduos", "plástico"]
                    },
                    {
                        "local": "Instituto Politécnico de Santarém",
                        "title": "Serviços de manutenção e limpeza de instalações",
                        "downloaded": False,
                        "keywords": ["manutenção", "limpeza"]
                    }
                ]
            },
            {
                "date": "2026-01-24",
                "links_count": 3,
                "opportunities": [
                    {
                        "local": "Unidade Local de Saúde de Lisboa Central",
                        "title": "Aquisição de detergentes e desinfetantes hospitalares",
                        "downloaded": True,
                        "keywords": ["detergentes", "desinfetantes", "hospitalar"]
                    },
                    {
                        "local": "Município do Porto",
                        "title": "Fornecimento de papel higiénico e toalhas para edifícios públicos",
                        "downloaded": False,
                        "keywords": ["papel", "higiénico", "toalhas"]
                    },
                    {
                        "local": "Escolas de Ensino Básico de Braga",
                        "title": "Material de limpeza e higiene para estabelecimentos escolares",
                        "downloaded": True,
                        "keywords": ["limpeza", "higiene", "escolar"]
                    }
                ]
            }
        ],
        "entity_stats": {
            "Unidade Local de Saúde do Oeste, E.P.E.": {"total": 3, "downloaded": 2},
            "Município de Torres Vedras": {"total": 2, "downloaded": 2},
            "Unidade Local de Saúde da Guarda, E.P.E.": {"total": 2, "downloaded": 1},
            "Unidade Local de Saúde de Coimbra": {"total": 2, "downloaded": 2},
            "Município de Leiria": {"total": 1, "downloaded": 1},
            "Câmara Municipal de Caldas da Rainha": {"total": 1, "downloaded": 0},
            "Escolas de Ensino Básico de Braga": {"total": 1, "downloaded": 1},
            "Município do Porto": {"total": 1, "downloaded": 0}
        },
        "keyword_stats": {
            "limpeza": 8,
            "higiene": 6,
            "material": 5,
            "hospitalar": 4,
            "produtos": 3,
            "desinfetantes": 3,
            "consumo": 2,
            "proteção": 2,
            "sacos": 2,
            "resíduos": 2
        }
    }
    
    # Gerar relatórios de exemplo
    print("Gerando relatório HTML de exemplo...")
    html_path = generate_report(sample_summary, format="html")
    print(f"✅ HTML gerado: {html_path}")
    
    print("\nGerando relatório Markdown de exemplo...")
    md_path = generate_report(sample_summary, format="md")
    print(f"✅ Markdown gerado: {md_path}")
    
    print("\n🎉 Relatórios de exemplo criados com sucesso!")
    print(f"Abra o arquivo HTML no navegador: {html_path}")

