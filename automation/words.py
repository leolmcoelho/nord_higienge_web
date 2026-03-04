import builtins as _builtins
import os
import re
import unicodedata

import pandas as pd


def load_words(file_path: str = None, sheet_name: str | int | None = 0) -> pd.DataFrame:
    """Carrega uma lista de palavras de um arquivo CSV.

    Args:
        file_path (str): Caminho para o arquivo CSV contendo as palavras.
        sheet_name (str | int | None): Nome ou índice da aba do Excel. Default 0.

    Returns:
        pd.DataFrame: DataFrame contendo as palavras carregadas.
    """
    file_path = file_path or "Palavras_Concurso.xlsx"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_excel(file_path, sheet_name=sheet_name)


def get_word_list(file_path: str = None, sheet_name: str | int | None = 0) -> list:
    """Retorna uma lista de palavras específicas.

    Returns:
        list: Lista de palavras.
    """
    data = load_words(file_path=file_path, sheet_name=sheet_name)
    if _builtins.isinstance(data, dict):
        # Todas as abas
        words = []
        for df in data.values():
            for col in df.columns:
                col_words = df[col].dropna().astype(str).tolist()
                words.extend(col_words)
    else:
        # Uma aba específica
        if 'Palavra-chave / Expressão' in data.columns:
            words = (
                data['Palavra-chave / Expressão']
                .dropna()
                .astype(str)
                .tolist()
            )
        else:
            # Carregar todas as abas e pegar todas as colunas
            all_data = load_words(file_path=file_path, sheet_name=None)
            words = []
            if _builtins.isinstance(all_data, dict):
                dfs = all_data.values()
            else:
                dfs = [all_data]

            for df in dfs:
                for col in df.columns:
                    col_words = df[col].dropna().astype(str).tolist()
                    words.extend(col_words)

    #remover designacao, transporte, codigo cpv, consumiveis

    # termos a remover (normalizados)
    blacklist = {
        'designacao',
        'transporte',
        'codigo cpv',
        'consumiveis',
        "diversos",
        "dispensadores",
        "residuos",
        "desinfecao"
    }

    # normalização + filtro
    words = [
        normalize_word(w)
        for w in words
        if w.strip() and normalize_word(w) not in blacklist
    ]

            
    return words


def normalize_word(word: str) -> str:
    """Normaliza uma palavra para comparação/pesquisa.

    - Converte para lowercase
    - Remove espaços no início/fim e comprime múltiplos espaços internos
    - Remove acentos (decomposição unicode NFKD e remoção de diacríticos)
    - Mantém apenas caracteres básicos (letras, números, espaço) removendo outros símbolos leves

    Args:
        word (str): Palavra original.

    Returns:
        str: Palavra normalizada.
    """
    if not _builtins.isinstance(word, str):
        return ""
    # lower + strip
    w = word.strip().lower()
    # decomposição unicode e remoção de diacríticos
    w = unicodedata.normalize('NFKD', w)
    w = ''.join(ch for ch in w if not unicodedata.combining(ch))
    # comprimir espaços
    w = re.sub(r'\s+', ' ', w)
    # remover caracteres não alfanuméricos (exceto espaço)
    w = re.sub(r'[^0-9a-zA-Z ]+', '', w)
    return w

if __name__ == "__main__":
    from logger import logger
    df = load_words()
    logger.info(get_word_list())


