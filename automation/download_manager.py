import datetime
import os
import shutil
import time
import uuid
import zipfile

from logger import logger


class DownloadManager:
    """Gerenciador centralizado de downloads para os clientes de automação."""
    
    def __init__(self, driver, download_base: str = None):
        """Inicializa o gerenciador de downloads.
        
        Args:
            driver: Instância do WebDriver (Chrome/Firefox)
            download_base: Pasta base para downloads (padrão: ./downloads)
        """
        self.driver = driver
        self.download_base = download_base or os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_base, exist_ok=True)
        self.current_download_folder = None

    def prepare_download_folder(self, identifier: str = None) -> str:
        """Cria uma pasta dinâmica para downloads e configura o navegador.
        
        Args:
            identifier: Nome da pasta (se None, gera automaticamente)
            
        Returns:
            Caminho completo da pasta criada
        """
        name = identifier or (datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
        path = os.path.join(self.download_base, name)
        os.makedirs(path, exist_ok=True)

        # Configura o Chrome para baixar nessa pasta via CDP
        try:
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow", 
                "downloadPath": path
            })
            logger.info(f"📁 Pasta de download configurada: {path}")
        except Exception as e:
            # Fallback para opções experimentais (alguns drivers podem não suportar CDP)
            logger.warning(f"⚠️ CDP não disponível, tentando fallback: {e}")
            try:
                prefs = {
                    "download.default_directory": path,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True
                }
                self.driver.execute_script(
                    "window.localStorage.setItem('webdriver.downloadPrefs', arguments[0])", 
                    prefs
                )
                logger.info(f"📁 Pasta de download configurada (fallback): {path}")
            except Exception:
                logger.warning("⚠️ Não foi possível configurar pasta de download dinamicamente")

        self.current_download_folder = path
        return path

    def wait_for_downloads(self, folder: str, timeout: int = 60) -> list:
        """Aguarda até que todos os downloads sejam concluídos.
        
        Args:
            folder: Pasta onde os downloads estão sendo salvos
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            Lista de arquivos baixados
            
        Raises:
            TimeoutError: Se o tempo limite for excedido
        """
        logger.info(f"⏳ Aguardando downloads na pasta: {folder}")
        end_time = time.time() + timeout
        stable_count = 0
        last_file_count = 0
        no_files_duration = 0
        start_time = time.time()

        while time.time() < end_time:
            try:
                files = [f for f in os.listdir(folder) if not f.startswith('.')]
            except FileNotFoundError:
                files = []
                time.sleep(0.5)
                continue

            # Aguarda até que apareçam arquivos
            if not files:
                no_files_duration = time.time() - start_time
                if no_files_duration > 10 and int(no_files_duration) % 10 == 0:
                    logger.warning(f"⏳ Aguardando arquivos há {int(no_files_duration)}s na pasta...")
                time.sleep(0.5)
                continue
            
            # Log quando detectar novos arquivos
            if len(files) != last_file_count:
                logger.info(f"📄 {len(files)} arquivo(s) detectado(s): {files}")
                last_file_count = len(files)

            # Verifica se há arquivos temporários em progresso
            temp_files = [f for f in files if f.endswith('.crdownload') or f.endswith('.part') or f.endswith('.tmp')]
            if temp_files:
                logger.debug(f"⏳ Arquivos temporários em download: {temp_files}")
                stable_count = 0
                time.sleep(0.6)
                continue

            # Verifica estabilidade de tamanho (arquivos não estão mais crescendo)
            sizes = {}
            for f in files:
                try:
                    sizes[f] = os.path.getsize(os.path.join(folder, f))
                except OSError:
                    sizes[f] = -1

            time.sleep(0.5)

            sizes2 = {}
            for f in files:
                try:
                    sizes2[f] = os.path.getsize(os.path.join(folder, f))
                except OSError:
                    sizes2[f] = -1

            if sizes == sizes2:
                stable_count += 1
                if stable_count == 1:
                    logger.debug(f"✓ Tamanhos estáveis: {sizes}")
            else:
                stable_count = 0
                logger.debug(f"⏳ Arquivos ainda crescendo...")

            # Considera completo após 2 verificações estáveis consecutivas
            if stable_count >= 2:
                logger.info(f"✅ Download concluído: {len(files)} arquivo(s)")
                return files

        raise TimeoutError(f"⏱️ Timeout aguardando downloads na pasta: {folder}")

    def extract_zips(self, folder: str) -> list:
        """Extrai todos os arquivos ZIP em uma pasta e remove os ZIPs.
        
        Args:
            folder: Pasta contendo os arquivos ZIP
            
        Returns:
            Lista de arquivos ZIP processados
        """
        extracted_zips = []
        
        for fname in list(os.listdir(folder)):
            if not fname.lower().endswith('.zip'):
                continue
                
            zip_path = os.path.join(folder, fname)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(folder)
                os.remove(zip_path)
                logger.info(f"📦 ZIP extraído e removido: {fname}")
                extracted_zips.append(fname)
            except zipfile.BadZipFile:
                logger.error(f"❌ Arquivo ZIP corrompido: {fname}")
            except Exception as e:
                logger.error(f"❌ Falha ao extrair ZIP {fname}: {e}", exc_info=True)
        
        return extracted_zips

    def move_downloaded_files(
        self, 
        src_folder: str, 
        identifier: str = None, 
        category: str = 'archive'
    ) -> str:
        """Move arquivos de uma pasta temporária para o destino final.
        
        Args:
            src_folder: Pasta de origem (temporária)
            identifier: Nome da subpasta destino (ex: NIF_123456789)
            category: Categoria/raiz de destino (ex: 'vortal', 'acingov')
            
        Returns:
            Caminho da pasta de destino
        """
        root = os.path.join(self.download_base, category)
        os.makedirs(root, exist_ok=True)
        
        name = identifier or (datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
        dest = os.path.join(root, name)
        os.makedirs(dest, exist_ok=True)

        moved_count = 0
        files = os.listdir(src_folder)
        
        for f in files:
            # Ignora arquivos ocultos e temporários
            if f.startswith('.') or f.endswith('.crdownload') or f.endswith('.tmp'):
                continue
                
            src = os.path.join(src_folder, f)
            dst = os.path.join(dest, f)
            try:
                shutil.move(src, dst)
                moved_count += 1
                logger.debug(f"✅ Movido: {f}")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao mover {f}, tentando copiar: {e}")
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    moved_count += 1
                    logger.debug(f"✅ Copiado: {f}")
                except Exception as e2:
                    logger.error(f"❌ Falha ao copiar {f}: {e2}")
        
        if moved_count > 0:
            logger.info(f"📁 {moved_count} arquivo(s) movido(s) para: {dest}")
        else:
            logger.warning(f"⚠️ Nenhum arquivo foi movido de {src_folder}")
        
        return dest

    def cleanup_temp_folder(self, folder: str) -> bool:
        """Remove uma pasta temporária de forma robusta.

        Estratégia:
        - tenta ``shutil.rmtree`` com handler ``onerror`` para ajustar permissões;
        - se falhar, remove arquivos e subpastas individualmente;
        - último recurso: renomeia a pasta e tenta novamente.

        Retorna True se removida com sucesso, False caso contrário (faz log do que restar).
        """
        if not os.path.exists(folder):
            logger.debug(f"ℹ️ Pasta temporária já não existe: {folder}")
            return True

        # Handler para erros do shutil.rmtree (tenta ajustar permissões e repetir)
        def _on_rm_error(func, path, exc_info):
            try:
                os.chmod(path, 0o777)
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.remove(path)
            except Exception as e:
                logger.debug(f"on_rm_error: falha ao remover {path}: {e}")

        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            # 1) Tenta rmtree com onerror
            try:
                shutil.rmtree(folder, onerror=_on_rm_error)
            except Exception as e:
                logger.debug(f"⏳ Tentativa {attempt}/{max_attempts}: shutil.rmtree falhou: {e}")

            # Verifica se a pasta foi removida
            if not os.path.exists(folder):
                logger.info(f"🗑️ Pasta temporária removida: {folder}")
                return True

            # 2) Tenta remover entradas manualmente (arquivos primeiro, depois diretórios)
            try:
                for root, dirs, files in os.walk(folder, topdown=False):
                    for name in files:
                        path = os.path.join(root, name)
                        try:
                            os.chmod(path, 0o777)
                            shutil.rmtree(path)
                        except Exception as e:
                            logger.debug(f"⏳ Falha ao remover arquivo {path}: {e}")
                    for name in dirs:
                        dpath = os.path.join(root, name)
                        try:
                            os.chmod(dpath, 0o777)
                            shutil.rmtree(dpath)
                        except Exception as e:
                            logger.debug(f"⏳ Falha ao remover diretório {dpath}: {e}")
            except Exception as e:
                logger.debug(f"⏳ Erro ao caminhar pela pasta para remoção manual: {e}")

            # Se ainda existir, tenta renomear + rmtree como último recurso
            if os.path.exists(folder):
                try:
                    alt = folder + f".deleteme_{int(time.time())}"
                    os.rename(folder, alt)
                    try:
                        shutil.rmtree(alt, onerror=_on_rm_error)
                    except Exception as e:
                        logger.debug(f"⏳ Tentativa de remover pasta renomeada falhou: {e}")
                except Exception as e:
                    logger.debug(f"⏳ Não foi possível renomear pasta (tentativa {attempt}): {e}")

            if not os.path.exists(folder):
                logger.info(f"🗑️ Pasta temporária removida após tentativa {attempt}: {folder}")
                return True

            # Pequena pausa antes da próxima tentativa
            time.sleep(0.5)

        # Falha definitiva — lista o conteúdo restante para diagnóstico
        remaining = []
        try:
            for root, dirs, files in os.walk(folder):
                for name in files:
                    remaining.append(os.path.join(root, name))
                for name in dirs:
                    remaining.append(os.path.join(root, name))
        except Exception as e:
            logger.debug(f"Erro ao listar conteúdo restante da pasta: {e}")

        sample = remaining[:20]
        logger.warning(
            f"⚠️ Falha ao remover pasta temporária {folder}. Conteúdo restante (exemplo): {sample}{'...' if len(remaining) > 20 else ''}"
        )
        return False

    def download_and_organize(
        self,
        download_timeout: int = 120,
        identifier: str = None,
        category: str = 'archive',
        extract_zips: bool = True,
        cleanup: bool = True
    ) -> str:
        """Fluxo completo: prepara pasta, aguarda downloads, extrai ZIPs e organiza.
        
        Args:
            download_timeout: Tempo máximo de espera pelos downloads
            identifier: Nome da pasta de destino final
            category: Categoria de destino (vortal/acingov/etc)
            extract_zips: Se True, extrai arquivos ZIP automaticamente
            cleanup: Se True, remove pasta temporária após mover arquivos
            
        Returns:
            Caminho da pasta de destino final
            
        Raises:
            RuntimeError: Se nenhum arquivo for baixado
        """
        # 1. Prepara pasta temporária
        temp_folder = self.prepare_download_folder()
        
        try:
            # 2. Aguarda downloads
            try:
                files = self.wait_for_downloads(temp_folder, timeout=download_timeout)
                if not files:
                    raise RuntimeError("Nenhum arquivo foi baixado")
            except TimeoutError as e:
                logger.warning(f"⚠️ {e}")
                # Verifica se pelo menos algum arquivo foi baixado
                files = [f for f in os.listdir(temp_folder) if not f.startswith('.')]
                if not files:
                    raise RuntimeError("Timeout e nenhum arquivo baixado")
            
            # 3. Extrai ZIPs se necessário
            if extract_zips:
                self.extract_zips(temp_folder)
            
            # 4. Move para destino final
            dest = self.move_downloaded_files(temp_folder, identifier=identifier, category=category)
            
            # Pequeno delay para garantir que todos os handles de arquivo foram liberados
            time.sleep(0.5)
            
            return dest
            
        finally:
            # 5. Limpa pasta temporária
            if cleanup:
                # Aguarda um pouco antes de tentar limpar
                time.sleep(0.3)
                self.cleanup_temp_folder(temp_folder)
