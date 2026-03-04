import datetime
import time
from typing import Callable, Optional

from selenium.common.exceptions import WebDriverException

from .acingov import AcingovClient
from .dre import DREClient
from .driver import create_driver
from .logger import logger
from .report import generate_report
from .vortal import VortalClient
from .words import get_word_list

StatusHook = Optional[Callable[[str], None]]


def _update_statistics(summary, link, downloaded):
    """Atualiza as estatísticas do processamento de um link."""
    local = link.get("local", "Desconhecido")

    # Atualizar estatísticas gerais
    summary["processed"] += 1
    if downloaded:
        summary["downloaded"] += 1
    else:
        summary["skipped"] += 1

    # Estatísticas por entidade
    if local not in summary["entity_stats"]:
        summary["entity_stats"][local] = {"total": 0, "downloaded": 0}
    summary["entity_stats"][local]["total"] += 1
    if downloaded:
        summary["entity_stats"][local]["downloaded"] += 1

    # Estatísticas de palavras-chave
    for keyword in link.get("found_keywords", []):
        summary["keyword_stats"][keyword] = summary["keyword_stats"].get(keyword, 0) + 1


def _add_to_date_info(date_info, link, downloaded):
    """Adiciona uma oportunidade à lista de informações da data."""
    date_info["opportunities"].append({"local": link.get("local", "Desconhecido"), "title": link.get("title", ""), "downloaded": downloaded, "keywords": link.get("found_keywords", []), "portal_url": link.get("portal_url", "")})


def run_pipeline(
    keywords_file: str | None = None,
    sheet_name: str | int | None = 0,
    vortal_user: str = "",
    vortal_password: str = "",
    acingov_user: str = "",
    acingov_password: str = "",
    limit: int | None = None,
    headless: bool = False,
    use_word_boundaries: bool = True,
    status_hook: StatusHook = None,
    report_format: str = "html",
) -> dict:
    """Executa o fluxo completo DRE -> Vortal com opções configuráveis."""

    def notify(message: str):
        if status_hook:
            try:
                status_hook(message)
            except Exception:
                logger.debug("Status hook falhou", exc_info=True)

    if not vortal_user or not vortal_password:
        raise ValueError("Credenciais da Vortal são obrigatórias para executar o fluxo.")

    # Credenciais do Acingov são opcionais (só se houver links do Acingov)

    keywords = get_word_list(file_path=keywords_file, sheet_name=sheet_name)
    if not keywords:
        raise ValueError("Nenhuma palavra-chave carregada. Verifique o arquivo/aba informados.")

    summary = {"links_total": 0, "processed": 0, "downloaded": 0, "skipped": 0, "dates_processed": [], "entity_stats": {}, "keyword_stats": {}, "execution_time": 0}

    start_time = datetime.datetime.now()

    try:
        # for i in range(1, 4):  # Últimos 8 dias
        driver = None
        dre_max_retries = 3
        dre_retry_delay = 5

        # === FASE 1: Buscar editais no DRE (com retry) ===
        links = None
        date = datetime.date.today().strftime("%Y-%m-%d")

        for dre_attempt in range(dre_max_retries):
            try:
                if not driver:
                    driver = create_driver(headless=headless)

                logger.info(f"📋 Buscando anúncios no DRE para {date} (tentativa {dre_attempt + 1}/{dre_max_retries})")

                dre = DREClient(driver=driver)
                notify("Buscando anúncios no DRE...")
                links = dre.run(keywords=keywords, use_word_boundaries=use_word_boundaries, date=date)

                logger.info(f"✅ DRE processado com sucesso: {len(links)} links encontrados")
                break  # Sucesso - sai do loop de retry do DRE

            except Exception as e:
                logger.error(f"❌ Erro ao processar DRE (tentativa {dre_attempt + 1}/{dre_max_retries}): {e}", exc_info=True)

                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = None

                if dre_attempt < dre_max_retries - 1:
                    logger.info(f"⏳ Aguardando {dre_retry_delay}s antes de tentar o DRE novamente...")
                    time.sleep(dre_retry_delay)
                    dre_retry_delay *= 2
                else:
                    logger.error(f"❌ Todas as {dre_max_retries} tentativas do DRE falharam")
                    raise

        # with open('tmp/oportunidades/oportunidade_2026-02-18.json', 'r') as f:

        #     links = json.load(f)
        # Se não conseguiu buscar do DRE, não continua
        if links is None:
            raise RuntimeError("Falha ao obter links do DRE após todas as tentativas")

        # === FASE 2: Processar links nos portais (sem retry do DRE) ===
        date_info = {"date": date, "links_count": len(links), "opportunities": []}

        summary["links_total"] += len(links)
        notify(f"{len(links)} anúncios encontrados. Categorizando por portal...")

        if not links:
            logger.info(f"Nenhum anúncio encontrado para a data {date}.")
            summary["dates_processed"].append(date_info)
        else:
            # Categorizar links por portal
            vortal_links = []
            acingov_links = []
            unknown_links = []

            for link in links:
                portal_url = link.get("portal_url", "").lower()
                if "vortal" in portal_url:
                    vortal_links.append(link)
                elif "acingov" in portal_url:
                    acingov_links.append(link)
                else:
                    unknown_links.append(link)
            logger.info(f"📊 Vortal: {len(vortal_links)}, Acingov: {len(acingov_links)}, Desconhecidos: {len(unknown_links)}")

            # Processar links do Vortal (erros individuais não param o fluxo)
            if vortal_links:
                try:
                    notify(f"Processando {len(vortal_links)} links no Vortal...")

                    # aumenta timeout do driver para operações longas
                    try:
                        driver.command_executor._conn.timeout = 300
                    except Exception:
                        pass
                    try:
                        driver.set_page_load_timeout(180)
                    except Exception:
                        pass

                    vortal_client = VortalClient(driver=driver)
                    vortal_client.DATE = date

                    # retry no login caso haja timeouts / perda de sessão
                    vortal_login_ok = False
                    for _login_attempt in range(2):
                        try:
                            vortal_client.login(vortal_user, vortal_password)
                            vortal_login_ok = True
                            break
                        except Exception as e:
                            msg = str(e)
                            recoverable_login = "Read timed out" in msg or "Connection refused" in msg or "Connection reset by peer" in msg or "Failed to establish a new connection" in msg or isinstance(e, WebDriverException)

                            if _login_attempt == 0 and recoverable_login:
                                logger.warning("⚠️ Falha no login (timeout/connection) — recriando driver e tentando novamente...")
                                try:
                                    try:
                                        driver.quit()
                                    except Exception:
                                        pass

                                    driver = create_driver(headless=headless)
                                    try:
                                        driver.command_executor._conn.timeout = 300
                                    except Exception:
                                        pass
                                    try:
                                        driver.set_page_load_timeout(180)
                                    except Exception:
                                        pass

                                    vortal_client = VortalClient(driver=driver)
                                    vortal_client.DATE = date
                                    continue
                                except Exception as re:
                                    logger.error(f"❌ Falha ao recriar driver para login: {re}", exc_info=True)
                                    break
                            else:
                                raise

                    if not vortal_login_ok:
                        raise RuntimeError("Login no Vortal falhou")

                    for link in vortal_links:
                        title = link.get("title", "sem título")
                        notify(f"Processando no Vortal: {title}")

                        processed = False
                        # Tenta processar o link e reconectar o WebDriver se a sessão for perdida
                        for attempt_link in range(2):
                            try:
                                downloaded = vortal_client.search_oportunitys(title)
                                _update_statistics(summary, link, downloaded)
                                _add_to_date_info(date_info, link, downloaded)
                                processed = True
                                break
                            except Exception as e:
                                msg = str(e)
                                logger.error(f"❌ Erro ao processar link no Vortal '{title}' (attempt {attempt_link + 1}): {e}", exc_info=True)

                                recoverable = "Read timed out" in msg or "Connection refused" in msg or "Connection reset by peer" in msg or "Failed to establish a new connection" in msg or "Max retries exceeded" in msg or "session not created" in msg or isinstance(e, WebDriverException)

                                if attempt_link == 0 and recoverable:
                                    logger.warning("⚠️ Sessão WebDriver perdida — recriando driver e relogin (retry)...")
                                    try:
                                        try:
                                            driver.quit()
                                        except Exception:
                                            pass

                                        driver = create_driver(headless=headless)
                                        vortal_client = VortalClient(driver=driver)
                                        vortal_client.DATE = date
                                        vortal_client.login(vortal_user, vortal_password)

                                        # pequena pausa para estabilizar a sessão
                                        time.sleep(1)
                                        continue
                                    except Exception as re:
                                        logger.error(f"❌ Falha ao recriar driver: {re}", exc_info=True)
                                        break
                                else:
                                    break

                        if not processed:
                            _update_statistics(summary, link, False)
                            _add_to_date_info(date_info, link, False)
                except Exception as e:
                    logger.error(f"❌ Erro crítico no cliente Vortal: {e}", exc_info=True)
                    for link in vortal_links:
                        _update_statistics(summary, link, False)
                        _add_to_date_info(date_info, link, False)
            # print(f"Links do Vortal processados: {summary['downloaded']} de {len(vortal_links)}")
            # Processar links do Acingov (erros individuais não param o fluxo)
            print("Links do Acingov para processar:", len(acingov_links))
            if acingov_links:
                if not acingov_user or not acingov_password:
                    logger.warning("Links do Acingov encontrados, mas credenciais não fornecidas. Pulando...")
                    for link in acingov_links:
                        _update_statistics(summary, link, False)
                        _add_to_date_info(date_info, link, False)
                else:
                    try:
                        notify(f"Processando {len(acingov_links)} links no Acingov...")
                        # aumenta timeout do driver (operações longas)
                        try:
                            driver.command_executor._conn.timeout = 300
                        except Exception:
                            pass
                        try:
                            driver.set_page_load_timeout(180)
                        except Exception:
                            pass

                        acingov_client = AcingovClient(driver=driver)
                        acingov_client.DATE = date

                        # retry no login do Acingov (tratamento de timeouts de conexão)
                        acingov_login_ok = False
                        for _login_attempt in range(2):
                            try:
                                acingov_client.login(acingov_user, acingov_password)
                                acingov_login_ok = True
                                break
                            except Exception as e:
                                msg = str(e)
                                recoverable_login = "Read timed out" in msg or "Connection refused" in msg or "Connection reset by peer" in msg or "Failed to establish a new connection" in msg or isinstance(e, WebDriverException)

                                if _login_attempt == 0 and recoverable_login:
                                    logger.warning("⚠️ Falha no login Acingov (timeout/connection) — recriando driver e tentando novamente...")
                                    try:
                                        try:
                                            driver.quit()
                                        except Exception:
                                            pass

                                        driver = create_driver(headless=headless)
                                        try:
                                            driver.command_executor._conn.timeout = 300
                                        except Exception:
                                            pass
                                        try:
                                            driver.set_page_load_timeout(180)
                                        except Exception:
                                            pass

                                        acingov_client = AcingovClient(driver=driver)
                                        acingov_client.DATE = date
                                        continue
                                    except Exception as re:
                                        logger.error(f"❌ Falha ao recriar driver para login Acingov: {re}", exc_info=True)
                                        break
                                else:
                                    raise

                        if not acingov_login_ok:
                            raise RuntimeError("Login no Acingov falhou")

                        # acingov_client.fechar_modal()

                        for link in acingov_links:
                            title = link.get("title", "sem título")
                            notify(f"Processando no Acingov: {title}")

                            processed = False
                            for attempt_link in range(2):
                                try:
                                    downloaded = acingov_client.run(title)
                                    _update_statistics(summary, link, downloaded)
                                    _add_to_date_info(date_info, link, downloaded)
                                    processed = True
                                    break
                                except Exception as e:
                                    msg = str(e)
                                    logger.error(f"❌ Erro ao processar link no Acingov '{title}' (attempt {attempt_link + 1}): {e}", exc_info=True)

                                    recoverable = "Read timed out" in msg or "Connection refused" in msg or "Connection reset by peer" in msg or "Failed to establish a new connection" in msg or "Max retries exceeded" in msg or "session not created" in msg or isinstance(e, WebDriverException)

                                    if attempt_link == 0 and recoverable:
                                        logger.warning("⚠️ Sessão WebDriver perdida — recriando driver e relogin (retry)...")
                                        try:
                                            try:
                                                driver.quit()
                                            except Exception:
                                                pass

                                            driver = create_driver(headless=headless)
                                            acingov_client = AcingovClient(driver=driver)
                                            acingov_client.DATE = date
                                            acingov_client.login(acingov_user, acingov_password)
                                            acingov_client.fechar_modal()

                                            time.sleep(1)
                                            continue
                                        except Exception as re:
                                            logger.error(f"❌ Falha ao recriar driver: {re}", exc_info=True)
                                            break
                                    else:
                                        break

                            if not processed:
                                _update_statistics(summary, link, False)
                                _add_to_date_info(date_info, link, False)
                    except Exception as e:
                        logger.error(f"❌ Erro crítico no cliente Acingov: {e}", exc_info=True)
                        for link in acingov_links:
                            _update_statistics(summary, link, False)
                            _add_to_date_info(date_info, link, False)

            # Log dos links desconhecidos
            if unknown_links:
                for link in unknown_links:
                    logger.warning(f"Portal não identificado para URL: {link.get('portal_url', '')}. Pulando...")
                    _update_statistics(summary, link, False)
                    _add_to_date_info(date_info, link, False)

            summary["dates_processed"].append(date_info)

        # Encerrar driver
        if driver:
            try:
                driver.quit()
            except Exception:
                logger.warning("Falha ao encerrar driver.", exc_info=True)

        # Calcular tempo de execução
        end_time = datetime.datetime.now()
        summary["execution_time"] = (end_time - start_time).total_seconds()

        # Gerar relatório no formato escolhido
        report_path = generate_report(summary, format=report_format)
        summary["report_path"] = report_path

        notify(f"Processo concluído. Relatório: {report_path}")
        return summary

    except Exception as e:
        logger.error(f"Erro crítico no pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import os

    vortal_user = os.getenv("VORTAL_USER", "josealves@nordhigiene.pt")
    vortal_password = os.getenv("VORTAL_PASSWORD", "Nord#2026***1")
    acingov_user = os.getenv("ACINGOV_USER", "josealves@nordhigiene.pt")
    acingov_password = os.getenv("ACINGOV_PASSWORD", "M18122007a")
    run_pipeline(
        keywords_file=None,
        sheet_name=0,
        vortal_user=vortal_user,
        vortal_password=vortal_password,
        acingov_user=acingov_user,
        acingov_password=acingov_password,
        headless=False,
    )
