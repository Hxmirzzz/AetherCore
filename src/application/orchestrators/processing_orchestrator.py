"""
Orquestador de procesamiento (XML/TXT).
- run_once(): procesa todos los archivos pendientes en la carpeta de entrada.
- run_watch(): observa la carpeta y procesa a medida que lleguen archivos (usa debounce).
- _prevalidate_file(): pre-valida archivos SIN procesarlos (para aprobación manual).
- process_approved_file(): procesa archivo después de aprobación del usuario.
- reject_file(): mueve archivo rechazado a carpeta de errores.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import time
import threading
import uuid
import os
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET

from src.application.processors.xml.xml_processor import XMLProcessor
from src.application.processors.txt.txt_processor import TXTProcessor
from src.infrastructure.file_system.path_manager import PathManager
from src.infrastructure.repositories.punto_repository import PuntoRepository
from src.infrastructure.config.settings import get_config
from src.application.processors.xml.xml_processor import XMLResponseGenerator
from src.application.processors.xml.xml_mappers import extract_cc_from_filename

Config = get_config()
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

    def _prevalidate_file(self, ruta: Path, tipo: str, conn) -> dict:
        """
        Pre-valida archivo SIN procesarlo completamente.
        
        ¿Para qué sirve?
        - Verifica que el archivo se pueda abrir
        - Cuenta registros rápidamente
        - Detecta errores básicos de formato
        - NO genera Excel ni inserta en BD
        
        Args:
            ruta: Path al archivo
            tipo: "XML" o "TXT" (mayúsculas)
            conn: Conexión a BD (no se usa en validación básica)
        
        Returns:
            {
                "archivo_id": "uuid-generado",
                "errores": ["error1", "error2"],
                "num_registros": 123,
                "preview": {...}
            }
        """
        archivo_id = str(uuid.uuid4())
        errores_detectados = []
        keyword = Config.validation.valid_filename_keyword.lower()

        if keyword:
            if keyword not in ruta.name.lower():
                errores_detectados.append(f"Nombre de archivo inválido: No contiene el identificador de la empresa ('{keyword}')")

        if tipo.upper() == "XML":
            try:
                tree = ET.parse(ruta)
                root = tree.getroot()
                ordenes = len(root.findall(".//order"))
                remesas = len(root.findall(".//remit"))

                if (ordenes + remesas) == 0:
                    errores_detectados.append("No se encontraron órdenes ni remesas")

                return {
                    "archivo_id": archivo_id,
                    "errores": errores_detectados,
                    "num_registros": ordenes + remesas,
                    "preview": {
                        "ordenes": ordenes,
                        "remesas": remesas,
                    }
                }
            except Exception as e:
                logger.exception(f"Error pre-validando XML {ruta.name}")
                return {
                    "archivo_id": archivo_id,
                    "errores": [f"Error al parsear XML: {str(e)}"],
                    "num_registros": 0,
                    "preview": {}
                }

        elif tipo.upper() == "TXT":
            try:
                with open(ruta, "r", encoding="utf-8-sig") as f:
                    lineas = [ln.strip() for ln in f.readlines() if ln.strip()]

                tipo2 = sum(1 for ln in lineas if ln.startswith("2,"))

                if tipo2 == 0:
                    errores_detectados.append("No se encontraron registros tipo 2")

                return {
                    "archivo_id": archivo_id,
                    "errores": errores_detectados,
                    "num_registros": tipo2,
                    "preview": {
                        "tipo2": tipo2,
                    }
                }
            except Exception as e:
                logger.exception(f"Error pre-validando TXT {ruta.name}")
                return {
                    "archivo_id": archivo_id,
                    "errores": [f"Error al leer TXT: {str(e)}"],
                    "num_registros": 0,
                    "preview": {}
                }
        
        else:
            errores_detectados.append(f"Tipo de archivo desconocido: {tipo}")
            return {
                "archivo_id": archivo_id,
                "errores": errores_detectados,
                "num_registros": 0,
                "preview": {}
            }

    def process_approved_file(self, archivo_id: str, ruta: Path, tipo: str, conn) -> bool:
        """
        Procesa archivo que fue APROBADO por el usuario.
        
        ¿Cuándo se llama?
        - Usuario hace clic en "Aprobar" en el Dashboard
        - Backend llama a este método vía endpoint /api/archivos/aprobar
        
        Args:
            archivo_id: UUID del archivo (para logging/tracking)
            ruta: Path al archivo físico
            tipo: "XML" o "TXT"
            conn: Conexión a BD
        
        Returns:
            True si procesó exitosamente, False si falló
        """
        try:
            logger.info(f"Procesando archivo aprobado: {ruta.name} (ID: {archivo_id})")
            
            if tipo.upper() == "XML":
                punto_repo = PuntoRepository(conn)
                dict_clientes, dict_sucursales = punto_repo.mapas_para_mappers()
                puntos_info = {**dict_clientes, **dict_sucursales}

                ruta_excel = self._paths.output_xml_dir() / f"{ruta.stem}.xlsx"
                exito = self._xml.procesar_archivo_xml(ruta, ruta_excel, puntos_info, conn)
                
                if exito:
                    logger.info(f"Archivo XML {ruta.name} procesado exitosamente")
                else:
                    logger.error(f"Error procesando archivo XML {ruta.name}")
                
                return exito
            
            elif tipo.upper() == "TXT":
                if self._txt is None:
                    logger.error("TXTProcessor no disponible")
                    return False
                
                exito = self._txt.procesar_archivo_txt(ruta, conn)
                
                if exito:
                    logger.info(f"Archivo TXT {ruta.name} procesado exitosamente")
                else:
                    logger.error(f"Error procesando archivo TXT {ruta.name}")
                
                return exito
            
            else:
                logger.error(f"Tipo de archivo desconocido: {tipo}")
                return False
                
        except Exception as e:
            logger.exception(f"Error procesando archivo aprobado {archivo_id}")
            return False

    def reject_file(self, archivo_id: str, ruta: Path, tipo: str, motivo: str = None) -> bool:
        """
        Mueve archivo RECHAZADO a carpeta de errores.
        
        Args:
            archivo_id: UUID del archivo (para logging)
            ruta: Path al archivo físico
            tipo: "XML" o "TXT"
            motivo: Motivo del rechazo (opcional)
        
        Returns:
            True si movió exitosamente, False si falló
        """        
        try:
            logger.info(f"Rechazando archivo: {ruta.name} (ID: {archivo_id})")

            if tipo.upper() == "XML":
                lista_ids = []
                try:
                    tree = ET.parse(ruta)
                    root = tree.getroot()

                    for elem in root.iter():
                        tag_limpio = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

                        if tag_limpio.lower() in ['order', 'remit']:
                            id_val = elem.get("id") or elem.get("ID")
                            if not id_val:
                                for child in elem:
                                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                                    if child_tag.upper() == "ID" and child.text:
                                        id_val = child.text
                                        break
                            if id_val:
                                lista_ids.append(id_val)

                except Exception as e:
                    logger.exception(f"Error al parsear XML {ruta.name}")

                if not lista_ids:
                    lista_ids = [ruta.name]

                cc_code = extract_cc_from_filename(ruta.name)

                XMLResponseGenerator.generar_respuesta(
                    lista_ids=lista_ids,
                    nombre_archivo_original=ruta.name,
                    punto_de_referencia="RECHAZO_MANUAL",
                    estado="2",
                    cc_code_from_filename_passed=cc_code,
                    conn=None
                )

            if tipo.upper() == "XML":
                carpeta_errores = self._paths.errores_xml_dir()
            else:
                carpeta_errores = self._paths.errores_txt_dir()

            os.makedirs(carpeta_errores, exist_ok=True)
            destino = carpeta_errores / ruta.name
            shutil.move(ruta, destino)
            logger.info(f"Archivo movido a: {destino}")
            
            if motivo:
                motivo_path = carpeta_errores / f"{ruta.stem}_MOTIVO.txt"
                with open(motivo_path, "w", encoding="utf-8") as f:
                    f.write(f"Archivo: {ruta.name}\n")
                    f.write(f"Fecha rechazo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Motivo: {motivo}\n")
                logger.info(f"Motivo de rechazo guardado en: {motivo_path}")
            
            logger.info(f"Archivo rechazado exitosamente: {ruta.name}")
            return True
        except Exception as e:
            logger.error(f"Error al rechazar archivo {ruta}: {str(e)}")
            return False