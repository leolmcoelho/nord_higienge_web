"""Definições e criação de WebDriver centralizado.

Este módulo encapsula a criação do Chrome WebDriver para reutilização
em múltiplos pontos do código.
"""
import logging
from typing import Iterable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Suprime logs do WebDriver Manager
logging.getLogger('WDM').setLevel(logging.ERROR)


def create_driver(headless: bool = False, extra_args: Optional[Iterable[str]] = None) -> webdriver.Chrome:
    """Cria e retorna uma instância de Chrome WebDriver pré-configurada.

    Args:
        headless (bool): Se True, inicia o Chrome em modo headless.
        extra_args (Iterable[str] | None): Lista/iterável de argumentos adicionais
            para o Chrome.

    Returns:
        webdriver.Chrome: Instância pronta para uso.
    """
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    # Configurações básicas recomendadas para ambientes de container / estabilidade
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')

    for arg in (extra_args or []):
        options.add_argument(arg)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

__all__ = ['create_driver']
