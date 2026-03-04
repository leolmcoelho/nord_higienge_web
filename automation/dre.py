import datetime
import json
import os
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from driver import create_driver
from logger import logger
from words import get_word_list, normalize_word


class DREClient:
    url = "https://diariodarepublica.pt/dr/home"
    DATE = datetime.date.today().strftime("%Y-%m-%d")

    def __init__(self, driver: webdriver.Chrome = None, headless: bool = False, extra_args=None):
        """Cliente para interação com o portal DRE.

        Args:
            driver (webdriver.Chrome | None): Instância já criada (injeta teste ou reuso). Se None, cria interna.
            headless (bool): Se True, inicia browser em modo headless.
            extra_args (Iterable[str] | None): Argumentos extras ao Chrome.
        """
        self.driver = driver or create_driver(headless=headless, extra_args=extra_args)

    # def __del__(self):
    #     # Fechar o navegador quando o objeto for destruído
    #     try:
    #         self.driver.quit()
    #     except Exception:
    #         pass

    def click(self, xpath, timeout: int = 40) -> bool:
        self.wait = WebDriverWait(self.driver, timeout)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
        return True

    def element(self, xpath, timeout: int = 40):
        self.wait = WebDriverWait(self.driver, timeout)
        return self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
   
    def elements(self, xpath, timeout: int = 40):
        self.wait = WebDriverWait(self.driver, timeout)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        return self.driver.find_elements(By.XPATH, xpath)

    

    def click_btn_scroll(self, retries: int = 3) -> bool:
        """Tenta clicar no botão de scroll com retry. Retorna True se conseguiu, False caso contrário."""
        for attempt in range(retries):
            try:
                self.click("//*[@id[starts-with(., 'b') and contains(., '-BotoesZoom')]]/div/div/button[3]", timeout=10)
                logger.debug(f"✅ Botão de scroll clicado com sucesso (tentativa {attempt + 1})")
                return True
            except Exception as e:
                logger.debug(f"⚠️ Tentativa {attempt + 1}/{retries} falhou ao clicar no botão de scroll: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
        logger.warning("⚠️ Botão de scroll não encontrado após várias tentativas. Continuando sem scroll.")
        return False

    def scroll_to_bottom(self):
        self.driver.execute_async_script("""
        const done = arguments[0];  // callback para o Selenium

        function getScrollableElements() {
            const elems = [document.documentElement, document.body, ...document.querySelectorAll('*')];
            return elems.filter(el => el.scrollHeight > el.clientHeight + 20);
        }

        const elems = getScrollableElements();
        let scrollElem = elems.find(el => el.scrollTop + el.clientHeight < el.scrollHeight) || window;

        let lastHeight = 0;
        let sameCount = 0;

        const interval = setInterval(() => {
            if (scrollElem === window) {
                window.scrollBy(0, 500);
                var newHeight = document.body.scrollHeight;
            } else {
                scrollElem.scrollBy(0, 500);
                var newHeight = scrollElem.scrollHeight;
            }

            // se o tamanho não muda, tentamos mais algumas vezes
            if (newHeight === lastHeight) {
                sameCount++;
            } else {
                sameCount = 0;
                lastHeight = newHeight;
            }

            // chegou ao final ou não muda há muito tempo
            if (sameCount >= 6) {
                clearInterval(interval);
                if (scrollElem === window)
                    window.scrollTo(0, document.body.scrollHeight);
                else
                    scrollElem.scrollTo(0, scrollElem.scrollHeight);

                console.log('✅ Rolagem completa!');
                setTimeout(done, 500);
            }
        }, 300);
    """)

    def click_previous_month(self):
        """Clica no botão de voltar mês no calendário."""
        try:
            # Tenta diferentes xpaths para o botão de voltar mês
            xpaths = ["//a[@title='Mês Anterior']"]

            for xpath in xpaths:
                try:
                    logger.info(f"Tentando clicar em voltar mês com xpath: {xpath}")
                    self.click(xpath, timeout=5)
                    logger.info("✅ Clicou com sucesso no botão de voltar mês")
                    time.sleep(0.5)
                    return True
                except Exception as e:
                    logger.error(f"Xpath {xpath} não funcionou: {e}")
                    continue

            logger.error("❌ Nenhum xpath funcionou para voltar mês")
            raise ValueError("Não foi possível clicar no botão de voltar mês.")
        except Exception as e:
            logger.error(f"Erro ao tentar voltar mês: {e}")
            raise e

    def get_2_serie(self, retries: int = 3, delay: float = 1.0) -> bool:
        """Acessa a "2.ª Série" com retry.

        Args:
            retries: número máximo de tentativas (padrão 3).
            delay: tempo inicial de espera entre tentativas em segundos; aplica backoff exponencial.

        Returns:
            True se conseguiu clicar na 2.ª série.

        Lança ValueError se todas as tentativas falharem.
        """
        attempt = 0
        xpath = "//a[.//span[normalize-space()='2.ª Série']]"

        while attempt < retries:
            try:
                attempt += 1
                logger.debug(f"Tentativa {attempt}/{retries} para acessar 2.ª Série")

                # Aguardar que o elemento da 2ª série esteja presente e clicável
                WebDriverWait(self.driver, 40).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self.click(xpath, timeout=40)
                logger.info("✅ Acessou a 2ª série com sucesso")
                return True

            except Exception as e:
                wait_time = delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Falha ao acessar 2.ª série (tentativa {attempt}/{retries}): {e}. "
                    f"Re-tentando em {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

        # depois das tentativas
        logger.error("Todas as tentativas para acessar a 2.ª série falharam.")
        raise ValueError("Erro ao acessar a 2.ª série do DRE.")

    def click_anuncios_publicados(self):
        try:
            self.click("//a[contains(@class, 'conteudoSerieII') and contains(., 'Contratos Públicos')]", timeout=40)
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Não foi possível clicar em 'Contratos Públicos': {e}")
            raise ValueError("Erro ao clicar em 'Contratos Públicos' do DRE.")

    def click_200(self):
        max_attempts = 5
        time.sleep(2)  # Pequena pausa antes de tentar acessar o select
        self.driver.refresh()  # Tentar refresh para resolver possíveis problemas de carregamento
                
        for attempt in range(max_attempts):
            try:
                logger.info(f"Tentativa {attempt + 1} de {max_attempts} para selecionar itens por página")
                self.set_contratos_publicos_select()
                # Aguardar que o select esteja presente e visível
                element = WebDriverWait(self.driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH, "(//select[contains(@class, 'dropdown-display')])[2]"))
                )
                
                # Aguardar um pouco mais para garantir que as opções estejam carregadas
                time.sleep(2)
                
                select_element = Select(element)
                
                # Tentar selecionar 200 diretamente
                try:
                    qtd = '50'
                    select_element.select_by_visible_text(qtd)
                    logger.info(f"✅ Selecionado {qtd} itens por página com sucesso")
                    return
                except Exception:
                    pass
                
                # # Se não conseguiu, tentar por value
                # try:
                #     select_element.select_by_value("50")
                #     logger.info("✅ Selecionado '200' itens por página (por value)")
                #     return
                # except Exception:
                #     pass
                
                # Se ainda não conseguiu, tentar a maior opção disponível
                try:
                    options = [opt.text.strip() for opt in select_element.options if opt.text.strip()]
                    numeric_options = [int(opt) for opt in options if opt.isdigit()]
                    if numeric_options:
                        max_option = str(max(numeric_options))
                        select_element.select_by_visible_text(max_option)
                        logger.info(f"✅ Selecionado '{max_option}' itens por página (maior disponível)")
                        return
                    else:
                        logger.warning("Nenhuma opção numérica encontrada no select")
                except Exception as e:
                    logger.error(f"Erro ao tentar selecionar opção no select: {e}")
                    
                # Se chegou aqui, nenhuma tentativa funcionou nesta iteração
                if attempt < max_attempts - 1:
                    logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente em 3 segundos...")
                    time.sleep(3)
                else:
                    logger.error(f"Todas as {max_attempts} tentativas falharam")
                    
            except Exception as e:
                self.driver.refresh()
                if attempt < max_attempts - 1:
                    logger.warning(f"Erro na tentativa {attempt + 1}: {e}. Tentando novamente em 3 segundos...")
                    time.sleep(3)
                else:
                    logger.error(f"Erro final após {max_attempts} tentativas: {e}")
                    raise e

    def set_date(self, date_str: str):
        self.DATE = date_str
        # Verifica se a data solicitada é de um mês anterior ao atual
        current_month = datetime.date.today().strftime("%Y-%m")
        requested_month = date_str[:7]

        if requested_month < current_month:
            time.sleep(2)
            self.click_previous_month()

        # Verificar se existe link para a data antes de tentar clicar
        date_xpath = f"//a[contains(@title, '{date_str}')]"
        
        try:
            WebDriverWait(self.driver, 40).until(
                EC.element_to_be_clickable((By.XPATH, date_xpath))
            )
            self.click(date_xpath, timeout=40)
        except Exception:
            logger.warning(f"⚠️ Nenhum anúncio publicado na data {date_str}. Pulando esta data.")

    def set_contratos_publicos_select(self, retries: int = 3) -> bool:
        """Seleciona a opção "L - Contratos públicos" no dropdown.

        - Abre o dropdown antes de tentar selecionar (melhora confiabilidade).
        - Faz retry em falhas e não lança — retorna False se não conseguir.
        """
        xpath = '//*[@id="Dropdown"]'
        attempt = 0

        while attempt < retries:
            attempt += 1
            try:
                logger.debug(f"Tentativa {attempt}/{retries} para selecionar 'L - Contratos públicos'")

                # Aguardar e obter o elemento do dropdown
                el = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )

                # Garantir que o dropdown está aberto (clicar nele)
                try:
                    el.click()
                    logger.debug("Dropdown clicado para abrir opções")
                except Exception:
                    logger.debug("Falha ao clicar no dropdown diretamente, tentando wrapper click")
                    try:
                        self.click(xpath)
                    except Exception:
                        logger.debug("Clique via wrapper também falhou — prosseguindo para tentativa de leitura das opções")

                time.sleep(0.6)  # tempo para as opções serem renderizadas

                select = Select(el)

                # Esperar que a opção desejada apareça nas opções
                try:
                    WebDriverWait(self.driver, 3).until(
                        lambda d: any(o.text.strip() == "L - Contratos públicos" for o in select.options)
                    )
                except Exception:
                    logger.debug(f"Opção 'L - Contratos públicos' não visível na tentativa {attempt}")

                # Tentar selecionar por texto e por value como fallback
                try:
                    select.select_by_visible_text("L - Contratos públicos")
                    logger.info("✅ Selecionado 'L - Contratos públicos' com sucesso")
                    return True
                except Exception:
                    try:
                        select.select_by_value("L - Contratos públicos")
                        logger.info("✅ Selecionado 'L - Contratos públicos' por value")
                        return True
                    except Exception as e:
                        logger.debug(f"Seleção falhou nesta tentativa: {e}")

            except Exception as e:
                logger.warning(f"Erro ao acessar/abrir dropdown (tentativa {attempt}/{retries}): {e}")

            # backoff simples
            time.sleep(1 + attempt)

        logger.warning("Não foi possível selecionar 'L - Contratos públicos' após várias tentativas")
        return False

    def get_ads_link(self, date: str | None = None) -> str | None:
        try:
            # Navegar para a página e aguardar carregamento completo
            self.driver.get(self.url)
            
            # Aguardar que a página carregue completamente
            WebDriverWait(self.driver, 40).until(
                EC.presence_of_element_located((By.XPATH, "//*[starts-with(@id, 'Series')]"))
            )
            time.sleep(1)  # Pequena pausa adicional

            self.get_2_serie()

            time.sleep(1)

            if date:
                self.set_date(date)
            
            time.sleep(1)
            self.click_anuncios_publicados()
            
            # Verificar se voltou para home e tentar novamente se necessário (até 3 tentativas).
            # Usa espera por elemento da listagem (`#ListaDiplomasDiario`) ou checa mudança de URL para validar sucesso,
            # assim evitamos decisões baseadas em leituras imediatas de `current_url` que podem estar desatualizadas.
            attempts = 0
            max_attempts = 3
            success = False

            while attempts < max_attempts and not success:
                attempts += 1
                logger.debug(f"Verificando navegação após clicar em 'anúncios publicados' (tentativa {attempts}/{max_attempts}). URL atual: {self.driver.current_url}")

                try:
                    # Primeiro, aguardar rapidamente pela presença do elemento que indica que a listagem carregou
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "ListaDiplomasDiario"))
                    )
                    success = True
                    logger.info("Página de anúncios carregada (elemento #ListaDiplomasDiario encontrado)")
                    break
                except Exception:
                    # Se o elemento não apareceu, verificar se a URL efetivamente mudou
                    current = self.driver.current_url
                    if "/dr/home" not in current:
                        # Consideramos que a navegação ocorreu mesmo sem o elemento estar presente ainda
                        success = True
                        logger.info(f"URL mudou para '{current}' — prosseguindo (elemento ainda não encontrado)")
                        break

                    # ainda estamos em /dr/home -> tentar reclicar
                    logger.warning(f"Retornou para /dr/home (tentativa {attempts}/{max_attempts}), re-clicando em 'anúncios publicados'...")
                    try:
                        self.click_anuncios_publicados()
                    except Exception as e:
                        logger.warning(f"Falha ao clicar em 'anúncios publicados' na tentativa {attempts}: {e}")
                    time.sleep(1)

            if not success:
                logger.error("Após várias tentativas a página de anúncios não carregou corretamente; prosseguindo, mas a listagem pode estar incorreta.")

            i = 1
            content_file = []
                 # Tentar selecionar mais itens por página (opcional)
            self.set_contratos_publicos_select()
            try:
                self.click_200()
            except Exception as e:
                logger.warning(f"Não foi possível alterar itens por página, continuando: {e}")
            # iterar por todas as páginas/scrolls, extrair itens únicos e montar HTML agregado
            collected_items_html = []
            seen_links = set()
            max_iterations = 200
            iteration = 0

            def _extract_items_from_source(html_source):
                soup = BeautifulSoup(html_source, "html.parser")
                return soup.select('#ListaDiplomasDiario > div > div:nth-of-type(3) > div') or []

            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"Iteração de coleta {iteration}: {len(seen_links)} itens já coletados")

                # rolar para carregar o conteúdo atual
                try:
                    self.scroll_to_bottom()
                except Exception:
                    logger.debug("scroll_to_bottom falhou nesta iteração")

                time.sleep(0.8)

                # extrair itens da página atual
                items = _extract_items_from_source(self.driver.page_source)
                new_found = 0
                for it in items:
                    a = it.select_one('a')
                    if not a:
                        continue
                    href = a.get('href')
                    if not href or href in seen_links:
                        continue
                    seen_links.add(href)
                    collected_items_html.append(str(it))
                    new_found += 1

                # tentar avançar página (se botão existir)
                try:
                    self.click_proxima_pagina()
                    time.sleep(0.8)
                except Exception:
                    # se não houver botão ou falhar, parar quando não houver itens novos
                    if new_found == 0:
                        logger.info("Nenhum item novo e próxima página indisponível — encerrando coleta")
                        break
                    # caso tenha encontrado itens novos, tentar mais uma iteração de scroll
                    logger.debug("Próxima página indisponível — tentando mais scroll para garantir carregamento")
                    try:
                        self.scroll_to_bottom()
                        time.sleep(0.6)
                    except Exception:
                        pass

                if new_found == 0 and iteration > 1:
                    logger.info(f"Nenhum item novo na iteração {iteration}; encerrando")
                    break

            logger.info(f"Coleta concluída — total único de itens: {len(seen_links)}")

            # montar um HTML compatível com o seletor usado em `filter_ads`
            fake_container = (
                '<div id="ListaDiplomasDiario"><div><div></div><div>' +
                ''.join(collected_items_html) +
                '</div></div></div>'
            )

            # persistir para inspeção e debug
            with open("dre_page_all.html", "w", encoding="utf-8") as file:
                file.write(fake_container)

            return fake_container

        except Exception:
            logger.error("Erro ao acessar a página", exc_info=True)
            return None

    # def use_only_white_list(self, data):
        
         
    def click_proxima_pagina(self):
        self.click("//button[@aria-label='Ir para a página seguinte']", timeout=5)

    def filter_ads(self, file=None, keywords=None, use_word_boundaries: bool = False):
        """Filtra itens e mantém apenas os que contêm palavras-chave no HTML detalhado.

        Args:
            file: HTML da listagem (se None, será carregado via navegador).
            keywords: lista de palavras/expressões; se None, carrega de `words.get_word_list()`.
            use_word_boundaries: se True, exige correspondência por palavra inteira.

        Returns:
            list[dict]: itens filtrados contendo `local`, `link`, `title`, `found_keywords` e `portal_url`.
        """
        file = file or self.get_ads_link()
        if not file:
            logger.warning("HTML da listagem não carregado (None). Retornando lista vazia")
            return []

        soup = BeautifulSoup(file, "html.parser")

        if keywords is None:
            try:
                keywords = get_word_list()
            except Exception:
                logger.error("Falha ao carregar lista de palavras-chave. Retornando lista vazia", exc_info=True)
                keywords = []
        logger.info(f"Total de palavras-chave para busca: {len(keywords)}")
        # //*[@id="ListaDiplomasDiario"]/div/div[2]/div
        itens = soup.select(
            '#ListaDiplomasDiario > div > div:nth-child(2) > div'
        )
        logger.info(f"Total de itens encontrados: {len(itens)}")


        editais = []
        i = 0
        for j, item in enumerate(itens):
            # <div data-container="" style="background-color: rgb(255, 255, 255); border-color: rgb(242, 242, 242); border-radius: 0px 0px 4px 4px; border-style: solid; border-width: 0px; margin-right: 0px; padding: 15px; width: 100%; position: absolute; top: -10000px;"><div class="ZoomText int-links" data-container=""><a class="conteudoSerieII LinkDiploma" data-link="" href="/dr/detalhe/anuncio-procedimento/29108-2025-945116954" rel="" style="margin-left: 0px; font-weight: bold;"><span data-expression="" style="margin-left: 0px;">Anúncio de procedimento n.º 29108/2025</span></a></div><div class="ZoomText int-links" data-container="" style="padding: 1px 0px 0px;"><span data-expression="" style="color: rgb(153, 153, 153); font-weight: bold;">Unidade Local de Saúde da Guarda, E. P. E.</span></div><div class="ZoomTextSumario int-links" data-container="" id="b8-l4-421_224-HTML_Text3" style="text-align: justify; color: rgb(22, 22, 22); font-size: 14px; font-weight: normal;"><div class="ZoomTextSumario int-links" data-container=""><div class="OSBlockWidget" data-block="HTMLInject.InjectHTML" id="b8-l4-421_224-$b7"><div data-container="" id="b8-l4-421_224-b7-InjectHTMLWrapper">Identificação microbiana e antibiograma automatizada pelo período de 36 meses para o Serviço de Patologia Clínica da ULS Guarda</div></div></div></div><div class="ZoomText int-links" data-container="" id="b8-l4-421_224-ShowResumoEn" style="margin-top: 3px; padding: 0px;"></div></div>
            # print(item.get_text(strip=True))
            # Extrair link
            link = item.select_one("a")["href"]
            
            # Extrair local (emitente)
            local = item.select_one("button span.cursor_class").get_text(strip=True) if item.select_one("button span.cursor_class") else ""
            
            # Verificar se é alteração
            is_alteracao = bool(item.select_one("div.OSInline span"))
            
            # Extrair título
            title_elem = item.select_one("div.ZoomTextSumario")
            if title_elem:
                title = title_elem.get_text(strip=True)
                # Limpar o título se necessário
                title = title.replace("P250A/2025 -", "").strip() if title.startswith("P250A/2025 -") else title
            else:
                title = ""
            
            # print(f"Analisando edital: {title}")
            edital = {"local": local, "link": f"https://dre.pt{link}", "title": title, "is_alteracao": is_alteracao}
            # Abrir a página detalhada, rolar e verificar palavras-chave
            self.driver.get(edital["link"])
            try:
                self.click_btn_scroll()
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível clicar no botão de scroll: {e}. Continuando sem scroll.")
            page_html = self.driver.page_source

            found = self.find_keywords_in_html(page_html, keywords, use_word_boundaries=use_word_boundaries)
            if found:
                try:
                    portal_url = self.get_portal(page_html)
                except Exception:
                    portal_url = None
                edital["found_keywords"] = found
                edital["portal_url"] = portal_url
                editais.append(edital)
                i += 1

            logger.info(f"Processado {j + 1} de {len(itens)} editais")
            # input(f"Encontrado edital relevante em {local}. Pressione Enter para continuar...")
        logger.info(f"Total de editais elegiveis: {i}")
        os.makedirs("tmp/oportunidades", exist_ok=True)
        if self.DATE:
            with open(f"tmp/oportunidades/oportunidade_{self.DATE}.json", "w", encoding="utf-8") as f:
                json.dump(editais, f, ensure_ascii=False, indent=4)
        return editais

    def get_portal(self, html):
        soup = BeautifulSoup(html, "html.parser")

        # Busca qualquer texto que contenha "URL para Apresentação:"
        texto = soup.get_text()

        # Usa regex para extrair o link que vem logo após
        match = re.search(r"URL\s+para\s+Apresenta[çc][ãa]o:\s*(https?://\S+)", texto)
        if match:
            return match.group(1)

        raise ValueError("Link de apresentação não encontrado no HTML.")

    def find_keywords_in_html(self, html: str, keywords: list[str], use_word_boundaries: bool = False) -> list[str]:
        """Retorna as palavras da lista que aparecem no HTML (texto visível).

        - Normaliza tanto o texto do HTML quanto as palavras (lowercase, sem acentos, espaços comprimidos).
        - Por padrão usa busca por substring; com `use_word_boundaries=True` faz correspondência por palavra inteira.

        Args:
            html (str): Conteúdo HTML completo.
            keywords (list[str]): Lista de palavras/expressões a verificar.
            use_word_boundaries (bool): Se True, usa correspondência por palavra inteira.

        Returns:
            list[str]: Lista (sem duplicadas) de palavras da lista que foram encontradas.
        """

        # with open(f"tmp/{datetime.datetime.now().strftime('%H-%M-%S')}.html", "w", encoding="utf-8") as f:
        #     f.write(html)
        if not html or not keywords:
            return []

        # extrai texto visível e normaliza
        text_raw = BeautifulSoup(html, "html.parser").get_text(" ")
        norm_text = normalize_word(text_raw)

        # normaliza keywords, mantendo mapeamento para a forma original
        seen = set()
        norm_to_original = {}
        normalized_keywords = []
        for kw in keywords:
            n = normalize_word(str(kw))
            if not n:
                continue
            if n in seen:
                continue
            seen.add(n)
            norm_to_original[n] = kw
            normalized_keywords.append(n)

        found = []
        if use_word_boundaries:
            for n in normalized_keywords:
                pattern = rf"\b{re.escape(n)}\b"
                if re.search(pattern, norm_text):
                    found.append(norm_to_original[n])
        else:
            for n in normalized_keywords:
                if n in norm_text:
                    found.append(norm_to_original[n])

        return found

    def has_keywords(self, html: str, keywords: list[str], use_word_boundaries: bool = False) -> bool:
        """Atalho booleano: True se alguma palavra for encontrada no HTML."""
        return bool(self.find_keywords_in_html(html, keywords, use_word_boundaries=use_word_boundaries))

    def run(self, keywords=None, use_word_boundaries=True, date=None):
        """Função principal para execução direta do cliente DRE."""
        if not keywords:
            keywords = get_word_list()
        # print(keywords)
        links = self.get_ads_link(date=date)
        return self.filter_ads(file=links, keywords=keywords, use_word_boundaries=use_word_boundaries)


if __name__ == "__main__":
    try:
        client = DREClient()
        date = "2026-02-05"  # Exemplo de data; pode ser alterada conforme necessário
        date = None
        link = client.get_ads_link(date=date)
        # link = None
        # with open('dre_page_all.html', encoding="utf-8") as f:
        #     link = f.read()
        client.filter_ads(file=link)
        if link:
            logger.info("Link encontrado")
        else:
            logger.warning("Link não encontrado")

    except Exception as e:
        logger.error(f"Erro ao executar o cliente DRE: {e}", exc_info=True)
    input("Pressione Enter para sair...")
