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
from typing import Dict, Any, Optional, Callable, List
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
from src.infrastructure.config.settings import get_config
from src.application.processors.xml.xml_processor import XMLResponseGenerator
from src.application.processors.txt.txt_processor import TXTResponseGenerator
from src.application.processors.xml.xml_mappers import extract_cc_from_filename
from src.infrastructure.api.internal_api_client import InternalApiClient
from src.infrastructure.api.external_api_client import ExternalApiClient    

Config = get_config()
logger = logging.getLogger(__name__)

class ProcessingOrchestrator:
    def __init__(
        self,
        xml_processor: XMLProcessor,
        path_manager: PathManager,
        watcher_factory: Callable,
        internal_api_client: InternalApiClient,
        external_api_client: ExternalApiClient,
        debounce_ms: int = 800,
        txt_processor: TXTProcessor | None = None,
    ):
        self._xml = xml_processor
        self._txt = txt_processor
        self._paths = path_manager
        self._Watcher = watcher_factory
        self._debounce_ms = debounce_ms
        self._internal_api = internal_api_client
        self._external_api = external_api_client
        self._bulk_limit = Config.external_api.bulk_limit

    def _ejecutar_pipeline_apis(self, file_path: Path, tipo: str, payload_servicios: List[Dict[str, Any]]) -> bool:
        """
        Orquesta el envío de datos: Primero a DB local (Pendiente), luego API Externa, y actualiza estado.
        """
        if not payload_servicios:
            logger.warning("No hay servicios para procesar en %s", file_path.name)
            return False
        
        log_inicial = {
            "App": "AetherCore_1",
            "Name": file_path.name,
            "FileType": tipo.upper(),
            "Estado": "PENDIENTE",
            "RecordCount": len(payload_servicios)
        }
        
        try:
            respuesta_interna = self._internal_api.register_event(log_inicial)
            log_id = respuesta_interna.get("id")
            
            if not log_id:
                logger.error("No se recibió un ID válido desde la base de datos local.")
                return False
        except Exception as e:
            logger.error("Error al registrar evento en DB local: %s", e)
            return False
        
        try:
            respuesta_externa = None
            if len(payload_servicios) > self._bulk_limit:
                logger.info("Cantidad de servicios (%d) mayor al límite (%d). Procesando en lotes.", len(payload_servicios), self._bulk_limit)
                respuesta_externa = self._external_api.create_bulk_orders(payload_servicios)
            else:
                logger.info("Cantidad de servicios (%d) menor o igual al límite (%d). Procesando individualmente.", len(payload_servicios), self._bulk_limit)
                respuestas = []
                for orden in payload_servicios:
                    resp = self._external_api.create_service_order(orden)
                    respuestas.append(resp)
                respuesta_externa = {"status": "success", "data": respuestas}
            
            if respuesta_externa and respuesta_externa.get("status") == "success":
                self._internal_api.update_event(log_id, {
                    "Estado": "PROCESADO_BULK" if len(payload_servicios) > self._bulk_limit else "APROBADO",
                    "ResponseJson": str(respuesta_externa.get("data"))
                })
                return True
            else:
                raise Exception(str(respuesta_externa))
        except Exception as e:
            logger.error("Error al enviar a API Externa: %s", e)
            self._internal_api.update_event(log_id, {
                "Estado": "ERROR",
                "ErrorDetails": str(e)
            })
            return False

    def process_approved_file(self, archivo_id: str, ruta: Path, tipo: str) -> bool:
        try:
            logger.info(f"Procesando archivo aprobado: {ruta.name} (ID: {archivo_id})")
            
            payload_servicios = []
            exito = False

            if tipo.upper() == "XML":
                ruta_excel = self._paths.output_xml_dir() / f"{ruta.stem}.xlsx"
                exito, payload_servicios = self._xml.procesar_archivo_xml(ruta, ruta_excel)
            elif tipo.upper() == "TXT":
                if self._txt is None: return False
                exito, payload_servicios = self._txt.procesar_archivo_txt(ruta)
            
            if exito and payload_servicios:
                return self._ejecutar_pipeline_apis(ruta, tipo, payload_servicios)
            
            return False
        except Exception as e:
            logger.error(f"Error al procesar archivo aprobado: {ruta.name} - {e}")
            return False

    # ===== XML =====
    def run_once_xml(self):
        entrada = self._paths.input_xml_dir()
        for xml_file in sorted(Path(entrada).glob("*.xml")):
            self.process_approved_file(str(uuid.uuid4()), xml_file, "XML")

    def run_watch_xml(self):
        entrada = self._paths.input_xml_dir()
        def on_file_callback(file_path: Path):
            if file_path.suffix.lower() == '.xml':
                self.process_approved_file(str(uuid.uuid4()), file_path, "XML")
        
        watcher = self._Watcher(entrada, on_new_file=on_file_callback, debounce_ms=self._debounce_ms)
        watcher.start()

    # ===== TXT =====
    def run_once_txt(self):
        entrada = self._paths.input_txt_dir()
        for txt in sorted(Path(entrada).glob("*.txt")):
            self.process_approved_file(str(uuid.uuid4()), txt, "TXT")

    def run_watch_txt(self):
        entrada = self._paths.input_txt_dir()
        
        def on_file_callback(file_path: Path):
            if file_path.suffix.lower() == '.txt':
                self.process_approved_file(str(uuid.uuid4()), file_path, "TXT")
        
        watcher = self._Watcher(entrada, on_new_file=on_file_callback, debounce_ms=self._debounce_ms)
        watcher.start()

    # ===== ALL =====
    def run_once(self, only: Optional[str] = None):
        if only is None or only == "xml":
            self.run_once_xml()
        if only is None or only == "txt":
            self.run_once_txt()

    def run_watch(self, only: Optional[str] = None):
        threads = []

        def _t(fn, name):
            t = threading.Thread(target=fn, name=name, daemon=True)
            threads.append(t)
            t.start()

        if only is None or only == "xml":
            _t(lambda: self.run_watch_xml(), "watch-xml")

        if only is None or only == "txt":
            _t(lambda: self.run_watch_txt(), "watch-txt")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo watchers…")

    def _prevalidate_file(self, ruta: Path, tipo: str) -> dict:
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

        if keyword and tipo.upper() == "XML":
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
            lista_ids = []
            cc_code = "00"

            if tipo.upper() == "XML":
                cc_code = extract_cc_from_filename(ruta.name)
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
            
            elif tipo.upper() == "TXT":
                cc_code = "00"
                try:
                    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("2,"):
                                parts = line.split(",")
                                if len(parts) > 17:
                                    id_val = parts[16].strip()
                                    if id_val:
                                        lista_ids.append(id_val)
                                elif len(parts) > 0:
                                    id_val = parts[-1].strip()
                                    if id_val:
                                        lista_ids.append(id_val)
                    
                except Exception as e:
                    logger.exception(f"Error al procesar TXT {ruta.name}")

            if not lista_ids:
                lista_ids = [ruta.name]

            lista_ids = sorted(list(set(lista_ids)))

            if tipo.upper() == "XML":
                XMLResponseGenerator.generar_respuesta(
                    lista_ids=lista_ids,
                    nombre_archivo_original=ruta.name,
                    punto_de_referencia="RECHAZO_MANUAL",
                    estado="2",
                    cc_code_from_filename_passed=cc_code,
                )
            elif tipo.upper() == "TXT":
                TXTResponseGenerator.generar_respuesta(
                    ids=lista_ids,
                    nombre_archivo_original=ruta.name,
                    carpeta_respuesta=Config.paths.carpeta_respuesta_txt,
                    estado="2",
                    cc_override=cc_code,
                )

            if tipo.upper() == "XML":
                carpeta_errores = self._paths.errores_xml_dir()
            else:
                carpeta_errores = self._paths.errores_txt_dir()

            os.makedirs(carpeta_errores, exist_ok=True)
            destino = carpeta_errores / ruta.name
            shutil.move(str(ruta), str(destino))
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