"""Serviço para gerenciamento de palavras-chave."""
from app import db
from app.models.keyword import Keyword


class KeywordService:
    """Serviço para operações com palavras-chave."""

    def load_keywords_from_file(self, file_path: str, sheet_name: str | int = 0) -> int:
        """Carrega palavras-chave de um arquivo."""
        from automation.words import get_word_list, normalize_word

        words = get_word_list(file_path=file_path, sheet_name=sheet_name)

        # Limpar palavras existentes do mesmo arquivo
        # (opcional: pode manter histórico removendo is_active)

        count = 0
        for word in words:
            normalized = normalize_word(word)
            existing = Keyword.query.filter_by(normalized_word=normalized).first()
            if existing:
                existing.is_active = True
                existing.source_file = file_path.split('/')[-1]
            else:
                keyword = Keyword(
                    word=word,
                    normalized_word=normalized,
                    is_active=True,
                    source_file=file_path.split('/')[-1]
                )
                db.session.add(keyword)
                count += 1

        db.session.commit()
        return count

    def get_active_keywords(self) -> list[Keyword]:
        """Retorna palavras-chave ativas."""
        return Keyword.query.filter_by(is_active=True).all()

    def get_word_list(self) -> list[str]:
        """Retorna lista de palavras como strings."""
        keywords = self.get_active_keywords()
        return [k.word for k in keywords]

    def deactivate_all(self) -> None:
        """Desativa todas as palavras-chave."""
        Keyword.query.update({'is_active': False})
        db.session.commit()

    def add_keyword(self, word: str, source_file: str = None) -> Keyword:
        """Adiciona uma palavra-chave."""
        from automation.words import normalize_word

        normalized = normalize_word(word)
        existing = Keyword.query.filter_by(normalized_word=normalized).first()
        if existing:
            existing.is_active = True
            existing.source_file = source_file or existing.source_file
            db.session.commit()
            return existing
        else:
            keyword = Keyword(
                word=word,
                normalized_word=normalized,
                is_active=True,
                source_file=source_file
            )
            db.session.add(keyword)
            db.session.commit()
            return keyword
