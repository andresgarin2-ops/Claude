"""
Persistencia de estado usando un archivo JSON.
Diseñado para GitHub Actions: el archivo se commitea al repo después de cada ejecución.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StateStore:
    def __init__(self, path: str = "state.json"):
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"No se pudo leer {self.path}: {exc}. Iniciando estado vacío.")
                return {}
        return {}

    def get_last_state(self, codigo: str) -> dict | None:
        """Devuelve el último estado guardado para un expediente, o None si es nuevo."""
        return self._data.get(codigo)

    def save_state(self, codigo: str, state: dict):
        """Guarda el estado actual de un expediente y persiste en disco."""
        self._data[codigo] = state
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug(f"Estado de {codigo} guardado en {self.path}")
