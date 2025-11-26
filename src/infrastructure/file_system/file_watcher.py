"""
Watcher simple de directorio (pooling), sin dependencias externas.
- Detecta nuevos archivos por nombre (creación o copia).
- Aplica 'debounce' para evitar procesar mientras se está copiando.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Set
import time
import threading

class DirectoryWatcher:
    def __init__(self, directory: Path, on_new_file: Callable[[Path], None], debounce_ms: int = 800, interval_sec: float = 1.0):
        self._dir = directory
        self._on_new_file = on_new_file
        self._debounce_ms = debounce_ms
        self._interval_sec = interval_sec
        self._stop = threading.Event()
        self._seen: Set[str] = set()

    def _scan_once(self):
        if not self._dir.exists():
            self._dir.mkdir(parents=True, exist_ok=True)
        for p in self._dir.iterdir():
            if not p.is_file():
                continue
            name = p.name
            if name not in self._seen:
                self._seen.add(name)
                # No llamamos inmediatamente el callback; el orquestador aplica el sleep (debounce) previo al procesado.
                self._on_new_file(p)

    def start(self):
        def _loop():
            while not self._stop.is_set():
                try:
                    self._scan_once()
                    time.sleep(self._interval_sec)
                except Exception:
                    # Evitar que caiga el hilo por excepciones del callback
                    time.sleep(self._interval_sec)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def stop(self):
        self._stop.set()