"""
Orquestador de procesamiento (XML).
- run_once(): procesa todos los XML pendientes en la carpeta de entrada.
- run_watch(): observa la carpeta y procesa a medida que lleguen archivos (usa debounce).
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import time
import threading

from src.application.processors.xml.xml_processor import XMLProcessor
from src.application.processors.txt.txt_processor import TXTProcessor
from src.infrastructure.file_system.path_manager import PathManager

logger = logging.getLogger(__name__)

class ProcessingOrchestrator:
    def __init__(
        self,
        xml_processor: XMLProcessor,
        path_manager: PathManager,
        watcher_factory: Callable,
        debounce_ms: int = 800,
        txt_processor: TXTProcessor | None = None,
    ):
        self._xml = xml_processor
        self._txt = txt_processor
        self._paths = path_manager
        self._Watcher = watcher_factory
        self._debounce_ms = debounce_ms

    # ===== XML existentes (asumidos) =====
    def run_once(self, puntos_info: Dict[str, Dict[str, str]], conn: Any):
        entrada = self._paths.input_xml_dir()
        salida = self._paths.output_xml_dir()
        logger.info("Procesando XML (once) en: %s", str(entrada))
        for xml_file in sorted(Path(entrada).glob("*.xml")):
            out_xlsx = self._paths.build_output_excel_path(xml_file)
            self._xml.procesar_archivo_xml(xml_file, out_xlsx, puntos_info, conn)

    def run_watch(self, puntos_info: Dict[str, Dict[str, str]], conn: Any):
        entrada = self._paths.input_xml_dir()
        logger.info("Observando carpeta XML: %s", str(entrada))
        
        def on_file_callback(file_path: Path):
            if file_path.suffix.lower() == '.xml':
                self._xml.procesar_archivo_xml(
                    file_path, 
                    self._paths.build_output_excel_path(file_path), 
                    puntos_info, 
                    conn
                )
        
        watcher = self._Watcher(entrada, on_new_file=on_file_callback, debounce_ms=self._debounce_ms)
        watcher.start()

    # ===== TXT mínimos (si no los tienes, usa estos placeholders) =====
    def run_once_txt(self, puntos_info, conn):
        if self._txt is None:
            logger.warning("TXTProcessor no inyectado; se omite procesamiento TXT.")
            return
        entrada = self._paths.input_txt_dir()
        logger.info("Procesando TXT (once) en: %s", str(entrada))
        for txt in sorted(Path(entrada).glob("*.txt")):
            self._txt.procesar_archivo_txt(txt, conn)

    def run_watch_txt(self, puntos_info, conn):
        if self._txt is None:
            logger.warning("TXTProcessor no inyectado; se omite watch TXT.")
            return
        entrada = self._paths.input_txt_dir()
        logger.info("Observando carpeta TXT: %s", str(entrada))
        
        def on_file_callback(file_path: Path):
            if file_path.suffix.lower() == '.txt':
                self._txt.procesar_archivo_txt(file_path, conn)
        
        watcher = self._Watcher(entrada, on_new_file=on_file_callback, debounce_ms=self._debounce_ms)
        watcher.start()

    # ===== ALL =====
    def run_once_all(self, puntos_info: Dict[str, Dict[str, str]], conn: Any, only: Optional[str] = None):
        if only is None or only == "xml":
            self.run_once(puntos_info, conn)
        if only is None or only == "txt":
            self.run_once_txt(puntos_info, conn)

    def run_watch_all(self, puntos_info: Dict[str, Dict[str, str]], conn: Any, only: Optional[str] = None):
        threads = []

        def _t(fn, name):
            t = threading.Thread(target=fn, name=name, daemon=True)
            threads.append(t)
            t.start()

        if only is None or only == "xml":
            _t(lambda: self.run_watch(puntos_info, conn), "watch-xml")

        if only is None or only == "txt":
            _t(lambda: self.run_watch_txt(puntos_info, conn), "watch-txt")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo watchers…")