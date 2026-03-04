import datetime
import re
import time
import unicodedata

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from download_manager import DownloadManager
from driver import create_driver
from lists import white_list
from logger import logger


class VortalClient:
    url = "https://community.vortal.biz/"
    DATE = datetime.datetime.now().strftime("%Y-%m-%d")

    def __init__(self, driver: webdriver.Chrome = None, download_base=None, headless=False, extra_args=None):
        """Inicializa o cliente Vortal.

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


    def login(self, username, password):
        self.driver.get('https://community.vortal.biz/sts/Login')
        self.write('//*[@id="username"]/div[2]/div/div/span/input', username)
        password_path = '//*[@id="password"]/div[2]/div/div/span/span[1]/input'
        self.write(password_path, password)
        self.element(password_path).send_keys(Keys.ENTER)
        # Aguardar que o login seja concluído e a navegação apareça
        self.element('//*[@id="vortalNavigation"]/div/ul[2]/li[3]/div/a/span[2]', timeout=30)

    
    def close_onboarding_popup(self):
       
        close_button_xpath = '//*[@id="helppier-column-align-right"]/div/div/div'
        self.click(close_button_xpath, timeout=30)
         # Se o popup não estiver presente, ignorar o erro

    
    def write(self, xpath, message):
        self.wait = WebDriverWait(self.driver, 10)
        input_field = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        input_field.clear()
        input_field.send_keys(message)
        return True

    def click(self, xpath, timeout=10):
        self.wait = WebDriverWait(self.driver, timeout)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
        return True

    def click_js(self, xpath):
        element = self.element(xpath)
        self.driver.execute_script("arguments[0].click();", element)
        return True
    
    def enter(self, xpath):
        self.wait = WebDriverWait(self.driver, 10)
        element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        element.send_keys(Keys.ENTER)
        return True

    def get_oportunitys_page(self):
        self.driver.get('https://community.vortal.biz/opportunitiesmanagement/publics/myCountry')
        time.sleep(5)
        logger.debug("Página de oportunidades carregada")
        return self.driver.page_source

    def safe_click(self, xpath: str, timeout: int = 15, retries: int = 3) -> bool:
        """Clica com resiliência: scroll até o elemento, tenta click normal e, em caso de interceptação, usa JS.

        Remove cartões de anúncio que possam interceptar cliques ('.vortal_ads_card').
        """
        last_err = None
        for _ in range(retries):
            try:
                el = self.element(xpath, timeout=timeout)
                # Trazer ao viewport
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el
                )
                # Tentar clicar normalmente
                WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                return True
            except ElementClickInterceptedException as e:
                last_err = e
                # Tentar remover/ocultar overlays de anúncios
                try:
                    self.driver.execute_script(
                        "document.querySelectorAll('.vortal_ads_card').forEach(e=>e.style.display='none');"
                    )
                except Exception:
                    pass
                # Fallback JS click
                try:
                    el = self.element(xpath, timeout=3)
                    self.driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception as e2:
                    last_err = e2
                    time.sleep(0.5)
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        if last_err:
            raise last_err
        return False
    
    def download_documents(self):
        """Baixa documentos da oportunidade usando o DownloadManager."""
        # Clica no botão de download em lote (ZIP)
        try:
            self.safe_click('//*[@id="AvailableDocuments"]/div/div[1]/button', timeout=30)
            logger.info("📥 Download em lote iniciado (ZIP)...")
        except Exception as e:
            logger.error(f"❌ Não foi possível clicar no botão de download em lote: {e}", exc_info=True)
            return

        # Obtém o NIF da página para nomear a pasta final
        identifier = None
        try:
            nif = self.get_nif()
            if nif:
                identifier = f"NIF_{nif}"
        except Exception:
            identifier = None

        # Usa o DownloadManager para gerenciar todo o fluxo de download
        try:
            target = self.download_manager.download_and_organize(
                download_timeout=120,
                identifier=identifier,
                category=f'{self.DATE}/vortal/',
                extract_zips=True,
                cleanup=True
            )
            logger.info(f"✅ Arquivos movidos para: {target}")
        except Exception as e:
            logger.error(f"❌ Erro ao processar downloads: {e}", exc_info=True)

    def get_nif(self) -> str | None:
        """Extrai o NIF da página de detalhes da oportunidade.

        Tenta via seletor de classe e, em fallback, via XPath do bloco de autoridade gestora.

        Returns:
            str | None: NIF com 9 dígitos, se encontrado.
        """
        # Tentativa 1: seletor de classe específico com o texto "NIF: <número>"
        try:
            el = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 
                    ".contract-notice-view-details-business-card-company-nif"))
            )
            text = (el.text or el.get_attribute("textContent") or "").strip()
            m = re.search(r"(\d{9})", text)
            if m:
                return m.group(1)
        except Exception:
            pass

        # Tentativa 2: XPath fornecido do container
        try:
            el = self.element('//*[@id="ManagingAuthority"]/div/div/div[1]', timeout=5)
            text = (el.text or el.get_attribute("textContent") or "").strip()
            m = re.search(r"(\d{9})", text)
            if m:
                return m.group(1)
        except Exception:
            pass

        logger.warning("NIF não encontrado na página.")
        return None

    def get_local(self) -> str | None:
        """Extrai o nome da autoridade gestora da página de detalhes da oportunidade.

        Returns:
            str | None: Nome da entidade, se encontrado.
        """
        try:
            # Tenta múltiplos seletores para maior robustez
            selectors = [
                (By.CSS_SELECTOR, ".contract-notice-view-details-business-card-info button span"),
                (By.CSS_SELECTOR, ".contract-notice-view-details-business-card-info button"),
                (By.XPATH, '//*[@id="ManagingAuthority"]//button[@type="button"]'),
                (By.XPATH, '//*[@id="ManagingAuthority"]/div/div/div[1]'),
            ]
            
            text = None
            for by, selector in selectors:
                try:
                    el = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    text = (el.text or el.get_attribute("textContent") or "").strip()
                    if text:
                        break
                except Exception:
                    continue
            
            if not text:
                logger.warning("Nome da autoridade gestora não encontrado na página.")
                return None
            
            # Limpa e extrai apenas o nome da entidade
            return self._extract_entity_name(text)
        
        except Exception as e:
            logger.warning(f"Erro ao extrair nome da autoridade gestora: {e}")
            return None
    
    def _extract_entity_name(self, raw_text: str) -> str:
        """Extrai e limpa o nome da entidade usando técnicas de processamento de texto.
        
        Remove informações como NIF, localização, e mantém apenas o nome da entidade.
        
        Args:
            raw_text (str): Texto bruto extraído do elemento HTML
            
        Returns:
            str: Nome limpo da entidade
        """
        # Remove quebras de linha e espaços múltiplos
        text = re.sub(r'\s+', ' ', raw_text).strip()
        
        # Remove padrões conhecidos que não fazem parte do nome:
        # - NIF seguido de número
        text = re.sub(r'NIF\s*:?\s*\d+', '', text, flags=re.IGNORECASE)
        
        # - Localização (PORTUGAL, cidade ou qualquer padrão "PAÍS, Cidade")
        text = re.sub(r',?\s*PORTUGAL\s*,?\s*[\w\s]+$', '', text, flags=re.IGNORECASE)
        text = re.sub(r',?\s*[A-Z]{2,}\s*,\s*[\w\s]+$', '', text)  # Padrão genérico "PAÍS, Cidade"
        
        # - Remove vírgulas no final
        text = re.sub(r',\s*$', '', text)
        
        # Remove espaços extras resultantes da limpeza
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto removendo acentos, pontuação e convertendo para minúsculas.
        
        Args:
            text (str): Texto a ser normalizado
            
        Returns:
            str: Texto normalizado
        """
        if not text:
            return ""
        
        # Remove acentos/diacríticos
        nfkd = unicodedata.normalize('NFKD', text)
        text_without_accents = ''.join([c for c in nfkd if not unicodedata.combining(c)])
        
        # Converte para minúsculas
        text_lower = text_without_accents.lower()
        
        # Remove pontuação e caracteres especiais (mantém apenas letras, números e espaços)
        text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
        
        # Normaliza espaços múltiplos
        text_normalized = re.sub(r'\s+', ' ', text_clean).strip()
        
        return text_normalized
    
  
    def click_documents(self, retries: int = 3) -> bool:
        """Tenta clicar na aba de documentos com retry. Retorna True se conseguiu, False caso contrário."""
        for attempt in range(retries):
            try:
                self.scroll_vn_container_to_bottom()
                self.element('//*[@id="Documents"]/div[1]', timeout=10)
                
                self.driver.execute_script('document.querySelector("#Documents > div.ant-collapse-header").click()')
                logger.info("✅ Aba de documentos clicada.")
                return True
            except Exception as e:
                logger.debug(f"⚠️ Tentativa {attempt + 1}/{retries} falhou ao clicar em documentos: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        logger.warning("⚠️ Aba de documentos não encontrada após várias tentativas.")
        return False
        
    def scroll_vn_container_to_bottom(self):
        """Rola o container principal até o final de forma síncrona e resiliente.

        Evita uso de script assíncrono (que vinha gerando 'no value field') e
        tenta múltiplas iterações de scroll até estabilizar a altura.
        """
        try:
            self.driver.execute_script(
                """
                (function(){
                    const container = document.querySelector('#vn__main_container_inner');
                    if(!container){return 'container-not-found';}
                    let attempts = 0;
                    let last = -1;
                    // Limite de segurança para evitar loop infinito
                    while(attempts < 40){
                        const h = container.scrollHeight;
                        if(h === last){attempts++;} else {attempts = 0; last = h;}
                        container.scrollTop = h;
                    }
                    container.scrollTop = container.scrollHeight;
                    return 'ok';
                })();
                """
            )
        except Exception as e:
            logger.warning(f"Falha ao rolar container principal: {e}. Tentando scroll da janela.")
            try:
                self.driver.execute_script(
                    """
                    let i=0; const max=30;
                    function s(){window.scrollBy(0,600); i++; if(i<max) requestAnimationFrame(s);} s();
                    """
                )
            except Exception:
                logger.error("Fallback de scroll da janela também falhou.")



    

    def search_oportunitys(self, title, max_retries: int = 3) -> bool:
        """Busca e processa uma oportunidade no Vortal com retry.
        
        Args:
            title: Título da oportunidade a buscar
            max_retries: Número máximo de tentativas
            
        Returns:
            bool: True se houve download, False caso contrário
        """
        for attempt in range(max_retries):
            try:
                self.get_oportunitys_page()
                search_path = '//*[@id="vn__main_container_inner"]/div[1]/div[2]/main/section/section/main/main/div[2]/div/div/div/div[1]/span/span/span[1]/input'
                self.write(search_path, title)
                self.enter(search_path)
                
                # Aguardar que os resultados da busca sejam carregados
                try:
                    self.wait = WebDriverWait(self.driver, 15)
                    self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="vn__main_container_inner"]/div[1]/div[2]/main/section/section/main/main/div[4]/div/div/div/div/div/div/table/tbody/tr')))
                    self.click('//*[@id="vn__main_container_inner"]/div[1]/div[2]/main/section/section/main/main/div[4]/div/div/div/div/div/div/table/tbody/tr')
                    
                    if not self.click_documents():
                        logger.warning(f"Não foi possível acessar documentos para '{title}'. Pulando.")
                        return False
                    
                    local = self.get_local()
                    if local:
                        logger.info(f"Entidade '{local}' aprovada para download.")
                        self.download_documents()
                        return True
                    else:
                        logger.info(f"Local '{local}' não encontrado ou não aprovado para '{title}'. Pulando download.")
                        return False
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou para '{title}': {e}")
                        time.sleep(3)
                    else:
                        logger.error(f"Nenhum resultado encontrado para o título após {max_retries} tentativas: {title}", exc_info=True)
                        return False
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Erro geral na tentativa {attempt + 1}/{max_retries} para '{title}': {e}")
                    time.sleep(3)
                else:
                    logger.error(f"❌ Erro ao processar '{title}' após {max_retries} tentativas", exc_info=True)
                    return False
        
        return False
    

if __name__ == "__main__":
    try:
        client = VortalClient()
        client.login("josealves@nordhigiene.pt", "Nord#2026***1")
        client.search_oportunitys("Aquisição de rolos de sacos de plástico pretos para resíduos I e II")
     
    except Exception as e:
        logger.error(f"Erro ao executar o cliente Vortal: {e}", exc_info=True)
    input("Pressione Enter para sair...")
