from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.repository.vector.db import VectorDB

settings = get_settings()
_vector_db: Optional["VectorDB"] = None


def get_vector_db() -> "VectorDB":
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDB(Path(settings.vector_db_path))
    return _vector_db


class VectorStore:
    """Adapter around the vector similarity database."""

    def word_exists(self, word: str) -> bool:
        return get_vector_db().word_exists(word)

    def refresh_for_target(self, target_word: str) -> int:
        return get_vector_db().update_similarities(target_word)

    def get_similarity_and_rank(self, word: str) -> tuple[float, int] | None:
        return get_vector_db().get_word_similarity_and_rank(word)
