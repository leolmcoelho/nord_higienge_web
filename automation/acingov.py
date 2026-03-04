import datetime
import re
import time
import traceback
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .download_manager import DownloadManager
from .driver import create_driver
from .logger import logger


class AcingovClient:
    url = "https://www.acingov.pt/acingovprod/2/index.php/"
    DATE = datetime.datetime.now().strftime("%Y-%m-%d")

    def __init__(self, driver: webdriver.Chrome = None, download_base=None, headless=False, extra_args=None):
        """Inicializa o cliente Acingov.

        Args:
            driver (webdriver.Chrome | None): Driver já criado externamente (opcional).
            download_base (str | None): Pasta base onde serão criadas subpastas de download.
            headless (bool): Se True, inicializa em modo headless.
            extra_args (Iterable[str] | None): Argumentos adicionais para o Chrome se o driver for criado aqui.
        """
        # Cria ou utiliza driver injetado
        self.driver = driver or create_driver(headless=headless, extra_args=extra_args)
        
        # Inicializa o gerenciador de downloads
        self.download_manager = DownloadManager(self.driver, download_base=download_base)

    # def __del__(self):
    #     # Fechar o navegador quando o objeto for destruído
    #     try:
    #         self.driver.quit()
    #     except Exception:
    #         pass
    

    def element(self, xpath, timeout=10):
        self.wait = WebDriverWait(self.driver, timeout)
        element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        return element
    

    def elements(self, xpath):
        self.wait = WebDriverWait(self.driver, 10)
        elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
        return elements

    def write(self, xpath, text, clear_first=True):
        element = self.element(xpath)
        if clear_first:
            element.clear()
        element.send_keys(text)


    def click_element(self, xpath, wait=None):
        if wait is None:
            wait = WebDriverWait(self.driver, 10)
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        element.click()

    def login(self, username, password):
       
        self.driver.get(self.url)
        self.write('//*[@id="user"]', username)
        password_path = ' //*[@id="pass"]'
        self.write(password_path, password)
        self.element(password_path).send_keys(Keys.ENTER)


        time.sleep(1)  # Espera a página carregar após login
        self.fechar_modal()  # Fecha modal de anúncios se aparecer
        
    def fechar_modal(self):
        """Fecha modal de anúncios se aparecer."""
        try:
            el = self.element('//*[@id="ad-dialog"]/div/div[1]/div[1]/span', timeout=5)
            if el:
                el.click()
                logger.debug("✅ Modal de anúncio fechado")
        except Exception:
            # Modal pode não aparecer, ignorar
            pass
    
    def fechar_popup_fornecedor(self):
        """Fecha pop-ups de fornecedor que podem aparecer e bloquear cliques."""
        try:
            # Tenta fechar múltiplos possíveis pop-ups
            popup_selectors = [
                '//*[@id="template"]/div[16]/div[1]/button',  # Pop-up de download
                '//*[@id="pop-up-fornecedor-2"]//button[contains(@class, "close")]',
                '//*[@id="pop-up-fornecedor-2"]//span[contains(@class, "close")]',
                '//*[@id="pop-up-fornecedor-2"]//*[contains(@class, "fechar")]',
                '//button[contains(text(), "Fechar")]',
                '//button[contains(text(), "×")]',
            ]
            
            for selector in popup_selectors:
                try:
                    el = self.element(selector, timeout=0.5)
                    if el:
                        el.click()
                        logger.debug("✅ Pop-up de fornecedor fechado")
                        time.sleep(0.5)
                        return True
                except Exception:
                    continue
            
            # Se não encontrar botão de fechar, tenta clicar fora do pop-up
            try:
                # Clica no overlay de fundo se existir
                overlay = self.driver.find_element(By.CSS_SELECTOR, '.modal-backdrop, .overlay')
                if overlay:
                    overlay.click()
                    logger.debug("✅ Pop-up fechado via overlay")
                    time.sleep(0.5)
                    return True
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"ℹ️ Nenhum pop-up de fornecedor detectado")
        
        return False

    def get_entity_nif(self) -> str | None:
        """Extrai o NIF da entidade contratante da página usando múltiplas estratégias.
        
        Returns:
            NIF com 9 dígitos ou None se não encontrado
        """
        # Debug: salva HTML para análise se necessário
        # with open(f"debug_acingov_{datetime.datetime.now().strftime('%H%M%S')}.html", "w", encoding="utf-8") as f:
        #     f.write(self.driver.page_source)
        
        # Estratégia 1: Buscar em elementos visíveis específicos
        selectors_to_try = [
            (By.XPATH, "//*[contains(text(), 'NIF')]"),
            (By.XPATH, "//*[contains(text(), 'nif')]"),
            (By.XPATH, "//*[@class='entidade']"),
            (By.XPATH, "//*[@id='entidade']"),
            (By.CSS_SELECTOR, ".dados-entidade"),
        ]
        
        for by, selector in selectors_to_try:
            try:
                elements = self.driver.find_elements(by, selector)
                for elem in elements:
                    text = elem.text or elem.get_attribute("textContent") or ""
                    match = re.search(r'\b([0-9]{9})\b', text)
                    if match:
                        nif = match.group(1)
                        logger.info(f"🆔 NIF encontrado via seletor: {nif}")
                        return nif
            except Exception:
                continue
        
        # Estratégia 2: Buscar no page_source completo
        try:
            page_text = self.driver.page_source
            # Tenta padrão "NIF: 123456789" ou "NIF 123456789"
            match = re.search(r'NIF[:\s]*([0-9]{9})', page_text, re.IGNORECASE)
            if match:
                nif = match.group(1)
                logger.info(f"🆔 NIF encontrado no page_source: {nif}")
                return nif
            
            # Tenta buscar qualquer sequência de 9 dígitos (pode ser menos preciso)
            matches = re.findall(r'\b([0-9]{9})\b', page_text)
            if matches:
                # Pega o primeiro que não seja repetição (tipo 000000000, 111111111)
                for potential_nif in matches:
                    if len(set(potential_nif)) > 1:  # tem pelo menos 2 dígitos diferentes
                        logger.info(f"🆔 NIF encontrado (heurística): {potential_nif}")
                        return potential_nif
                        
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair NIF do page_source: {e}")
        
        logger.warning("⚠️ NIF não encontrado na página do Acingov")
        return None

    def wait_for_overlay_to_disappear(self, timeout: int = 30) -> bool:
        """Aguarda o overlay de loading (blockUI) desaparecer.
        
        Args:
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            True se o overlay desapareceu, False se não havia overlay
        """
        try:
            # Aguarda o overlay aparecer (se houver)
            overlay = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".blockUI.blockOverlay, .blockOverlay"))
            )
            logger.debug("⏳ Overlay de loading detectado, aguardando...")
            
            # Aguarda o overlay desaparecer
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI.blockOverlay, .blockOverlay"))
            )
            logger.debug("✅ Overlay de loading desapareceu")
            return True
        except Exception:
            # Não havia overlay ou já desapareceu
            return False

    def find_procediment(self, procediment_name):
                
        wait = WebDriverWait(self.driver, 10)

        # Fecha pop-ups que podem estar bloqueando
        self.fechar_popup_fornecedor()
        
        # 1. Espera o dropdown estar clicável
        dropdown = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'search-filters-box-js')]")
            )
        )

        # 2. Clica no dropdown (com retry se houver interceptação)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                dropdown.click()
                break
            except Exception as e:
                if "element click intercepted" in str(e) and attempt < max_attempts - 1:
                    logger.debug(f"⏳ Click interceptado, tentando fechar pop-ups novamente...")
                    self.fechar_popup_fornecedor()
                    time.sleep(1)
                else:
                    raise
        
        # 3. Aguardar e clicar na primeira opção do filtro
        filter_option = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//li[contains(@class, 'filter-option-js')][1]")
            )
        )
        filter_option.click()
        
        # 4. Aguardar o input aparecer e ficar disponível
        input_field = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input.input-filter-js")
            )
        )
        
        # 5. Digita o texto desejado no input
        input_field.clear()
        input_field.send_keys(procediment_name)
        
        # 6. Confirma a busca
        input_field.send_keys(Keys.ENTER)
        
        # 7. Aguarda o overlay de loading desaparecer e resultados carregarem
        self.wait_for_overlay_to_disappear(timeout=30)
        time.sleep(2)  # Pequena pausa adicional para estabilizar

        
    def search_oportunitys(self, title, download: bool = True, max_retries: int = 3) -> bool:
        """Busca e processa uma oportunidade no Acingov com retry.
        
        Args:
            title: Título da oportunidade a buscar
            download: Se True, tenta baixar documentos
            max_retries: Número máximo de tentativas
            
        Returns:
            bool: True se houve processamento bem-sucedido, False caso contrário
        """
        for attempt in range(max_retries):
            try:
                # Fecha qualquer pop-up que possa estar aberto
                self.fechar_popup_fornecedor()
                
                self.find_procediment(title)
                logger.info(f"🔍 Procedimento '{title}' encontrado no Acingov")
                
                if download:
                    # Tenta clicar na oportunidade e baixar
                    try:
                        if self.click_oportunity():
                            return self.download_documents()
                        else:
                            logger.warning(f"⚠️ Não foi possível acessar detalhes da oportunidade: {title}")
                            return False
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar download: {e}", exc_info=True)
                        return False
                # Refresh para limpar possíveis estados de erro
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou para '{title}': {e}")
                    # Fecha pop-ups antes de tentar novamente
                    self.fechar_popup_fornecedor()
                    self.driver.refresh()
                    time.sleep(3)
                else:
                    logger.error(f"❌ Erro ao pesquisar '{title}' no Acingov após {max_retries} tentativas: {e}")
                    return False
        
        return False
        


    def click_oportunity(self, max_retries: int = 3) -> bool:
        """Clica na primeira oportunidade dos resultados com retry.
        
        Args:
            max_retries: Número máximo de tentativas
            
        Returns:
            True se conseguiu clicar, False caso contrário
        """
        xpath = '//*[@id="tabs-1"]/div/div[2]/div[2]/div[2]/div/a'
        
        for attempt in range(max_retries):
            try:
                # Fecha pop-ups que podem estar bloqueando
                self.fechar_popup_fornecedor()
                
                # Aguarda overlay desaparecer antes de tentar clicar
                self.wait_for_overlay_to_disappear()
                
                # Aguarda o elemento estar presente e visível
                wait = WebDriverWait(self.driver, 15)
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                
                # Scroll até o elemento
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                
                # Tenta clicar
                try:
                    wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                except Exception:
                    # Fallback: click via JavaScript
                    self.driver.execute_script("arguments[0].click();", element)
                
                logger.info("✅ Oportunidade clicada com sucesso.")
                
                # Aguarda a página de detalhes carregar
                self.wait_for_overlay_to_disappear()
                time.sleep(1)
                
                # Debug: verifica URL atual
                current_url = self.driver.current_url
                logger.debug(f"📍 URL atual após clicar: {current_url}")
                
                return True
                
            except Exception as e:
                traceback.print_exc()
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou ao clicar na oportunidade: {e}")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Erro ao clicar na oportunidade após {max_retries} tentativas: {e}")
                    return False
        
        return False

    def download_documents(self, xpath_download_button: str = '//*[@id="dialog-msg-confirmacao"]/div/div[2]/div[3]/a', max_retries: int = 3) -> bool:
        """Baixa documentos da oportunidade usando o DownloadManager.
        
        Args:
            xpath_download_button: XPath do botão de download (pode variar)
            max_retries: Número máximo de tentativas
            
        Returns:
            True se download bem-sucedido, False caso contrário
        """
        # Obtém NIF ANTES de iniciar download para economizar tempo
        identifier = None
        try:
            nif = self.get_entity_nif()
            # Verifica se o NIF é válido e não é o valor problemático
            if nif and nif != "951755169":
                identifier = f"NIF_{nif}"
                logger.info(f"📁 Usando identificador: {identifier}")
            else:
                # Gera nome aleatório quando NIF não encontrado ou é inválido
                random_id = uuid.uuid4().hex[:8]
                identifier = f"ENTITY_{random_id}"
                if nif == "951755169":
                    logger.warning(f"⚠️ NIF incorreto detectado ({nif}) - usando nome aleatório: {identifier}")
                else:
                    logger.warning(f"⚠️ NIF não encontrado - usando nome aleatório: {identifier}")
        except Exception as e:
            # Em caso de erro, também gera nome aleatório
            random_id = uuid.uuid4().hex[:8]
            identifier = f"ENTITY_{random_id}"
            logger.warning(f"⚠️ Erro ao extrair NIF: {e} - usando nome aleatório: {identifier}")
        
        # Clica no botão de download
        for attempt in range(max_retries):
            try:
                # Aguarda overlay desaparecer
                self.wait_for_overlay_to_disappear()
                
                # Aguarda e clica no botão de download
                wait = WebDriverWait(self.driver, 15)
                download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_download_button)))
                download_btn.click()
                logger.info("📥 Botão de download clicado...")
                
                # Tenta fechar o pop-up que aparece após o download (múltiplas tentativas)
                popup_closed = False
                for popup_attempt in range(5):
                    time.sleep(0.5)
                    try:
                        close_popup = self.driver.find_element(By.XPATH, '//*[@id="template"]/div[16]/div[1]/button')
                        if close_popup.is_displayed():
                            close_popup.click()
                            logger.info("✅ Pop-up de download fechado")
                            popup_closed = True
                            break
                    except Exception:
                        if popup_attempt == 0:
                            logger.debug(f"⏳ Aguardando pop-up aparecer (tentativa {popup_attempt + 1}/5)...")
                
                if not popup_closed:
                    logger.warning("⚠️ Pop-up de download não foi fechado - pode afetar o download")
                
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou ao clicar no download: {e}")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Não foi possível clicar no botão de download: {e}", exc_info=True)
                    return False

        # Usa o DownloadManager para gerenciar todo o fluxo (com retry em caso de timeout)
        download_retries = 2
        for download_attempt in range(download_retries):
            try:
                # Aumenta timeout progressivamente em cada retry
                current_timeout = 150 + (download_attempt * 30)  # 150s, 180s
                
                target = self.download_manager.download_and_organize(
                    download_timeout=current_timeout,
                    identifier=identifier,
                    category=f'{self.DATE}/acingov/',
                    extract_zips=True,
                    cleanup=True
                )
                logger.info(f"✅ Arquivos movidos para: {target}")
                return True
            except RuntimeError as e:
                if "Timeout" in str(e) and download_attempt < download_retries - 1:
                    logger.warning(f"⚠️ Timeout no download (tentativa {download_attempt + 1}/{download_retries})")
                    logger.info("🔄 Verificando se o botão de download ainda está disponível...")
                    
                    # Aguarda um pouco antes de tentar novamente
                    time.sleep(5)
                    
                    # Verifica se ainda está na página de detalhes
                    try:
                        wait = WebDriverWait(self.driver, 5)
                        download_btn = wait.until(EC.presence_of_element_located((By.XPATH, xpath_download_button)))
                        
                        # Se o botão ainda existe, tenta clicar novamente
                        if download_btn.is_displayed() and download_btn.is_enabled():
                            download_btn.click()
                            logger.info("📥 Re-iniciando download...")
                            time.sleep(2)
                            
                            # Tenta fechar pop-up novamente
                            for popup_attempt in range(3):
                                try:
                                    close_popup = self.driver.find_element(By.XPATH, '//*[@id="template"]/div[16]/div[1]/button')
                                    if close_popup.is_displayed():
                                        close_popup.click()
                                        logger.info("✅ Pop-up fechado após retry")
                                        break
                                    time.sleep(0.5)
                                except Exception:
                                    time.sleep(0.5)
                        else:
                            logger.warning("⚠️ Botão de download não está acessível - pulando retry")
                            return False
                            
                    except Exception as retry_error:
                        logger.warning(f"⚠️ Não foi possível re-iniciar download: {retry_error}")
                        # Continua para próxima tentativa do download_and_organize
                else:
                    logger.error(f"❌ Erro ao processar downloads após {download_retries} tentativas: {e}", exc_info=True)
                    return False
            except Exception as e:
                logger.error(f"❌ Erro ao processar downloads: {e}", exc_info=True)
                return False
        
        return False


    def run(self, title: str):
        """Ativa a busca e retorna True se processado com sucesso.

        Antes: este método não retornava nada — callers (automation) esperavam
        um booleano indicando sucesso do download. Agora retornamos o valor
        de `search_oportunitys` para corrigir contagem de downloads no relatório.
        """
        result = self.search_oportunitys(title, download=True)
        try:
            self.driver.refresh()
        except Exception:
            # refresh é opcional — ignora falhas locais
            pass
        return True
    
if __name__ == "__main__":

    try:
        from logger import logger
        user = "josealves@nordhigiene.pt"
        password = "M18122007a"
        # try:
        client = AcingovClient()
        client.DATE = '2026-02-12'
        client.login(user, password)
        # client.fechar_modal()

        client.search_oportunitys("Prestação de serviços de limpeza em instalações administrativas e oficinais, veículos ferroviários e remoção de graffitis.")
        # client.search_oportunitys("Aquisição de rolos de sacos de plástico pretos para resíduos I e II")
     
    except Exception as e:
        logger.error(f"Erro ao executar o cliente Vortal: {e}", exc_info=True)
    input("Pressione Enter para sair...")
