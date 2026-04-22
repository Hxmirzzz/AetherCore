"""
Orquestador XML: une reader + transformer + response generator.
Mantiene rutas de salida, nombres y formato de respuesta idénticos al código original.
"""
from __future__ import annotations
from pathlib import Path
from pydoc import cli
from typing import Dict, Any, List, Tuple
import os
import logging
from datetime import datetime

from src.infrastructure.config.settings import get_config
from src.infrastructure.config.mapeos import TextosConstantes, ClienteMapeos
from .xml_file_reader import XmlFileReader
from .xml_mappers import map_elements, extract_cc_from_filename, build_timestamp_for_response, resolver_codigos_xml
from .xml_data_transformer import XmlDataTransformer
from src.infrastructure.api.external_api_client import ExternalApiClient

Config = get_config()
logger = logging.getLogger(__name__)

class XMLResponseGenerator:
    """Genera archivos de respuesta .txt para XMLs procesados."""
    
    @staticmethod
    def generar_respuesta(lista_ids: List[str], nombre_archivo_original: str, estado: str, cc_code_from_filename_passed: str) -> bool:
        """
        Genera archivo de respuesta con formato: TR2_<COMPANY>_CCCODEAAMMDDHHMM.txt
        
        Args:
            lista_ids: Lista de IDs de órdenes/remesas
            nombre_archivo_original: Nombre del XML original
            estado: "1" éxito, "2" error/rechazo
            cc_code_from_filename_passed: CC Code extraído del nombre del archivo
            
        Returns:
            True si se generó correctamente, False en caso contrario
        """
        try:
            if not lista_ids:
                return False
            
            os.makedirs(Config.paths.carpeta_respuesta_txt, exist_ok=True)
            ts = build_timestamp_for_response(nombre_archivo_original)
            nombre_respuesta = f"TR2_{Config.paths.company_code}_{cc_code_from_filename_passed}{ts}.txt"
            ruta_respuesta = Config.paths.carpeta_respuesta_txt / nombre_respuesta
            with open(ruta_respuesta, 'w', encoding='utf-8') as f:
                for id_val in sorted(lista_ids):
                    f.write(f"{id_val.strip()},{estado}\n")
            return True
        except Exception:
            return False

class XMLProcessor:
    """
    Procesador principal de archivos XML.
    """
    def __init__(
        self,
        reader: XmlFileReader | None = None,
        transformer: XmlDataTransformer | None = None,
        external_api: ExternalApiClient | None = None
    ):
        self._reader = reader or XmlFileReader()
        self._transformer = transformer or XmlDataTransformer()
        self._external_api = external_api

    def procesar_archivo_xml(self, ruta_xml: Path, ruta_excel: Path) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Procesa un archivo XML y genera Excel + archivo de respuesta.
        
        Args:
            ruta_xml: Ruta al archivo XML
            ruta_excel: Ruta donde guardar el Excel
            
        Returns:
            (Exito_booleano, Lista_de_Servicios_Payload)
        """
        try:
            logger.info("Iniciando procesamiento del archivo XML: '%s'", ruta_xml.name)
            
            info = self._reader.read(ruta_xml)
            if info.get("empty", False):
                self._manejar_xml_fallido(ruta_xml, "2", "XML vacío")
                return False, []

            root = info["root"]
            ordenes_elements = self._reader.find_elements(root, "order")
            remesas_elements = self._reader.find_elements(root, "remit")
            ordenes_filas = map_elements(ordenes_elements, TextosConstantes.SERVICIO_PROVISION_XML)
            remesas_filas = map_elements(remesas_elements, TextosConstantes.SERVICIO_RECOLECCION_XML)
            
            logger.info(
                "Elementos procesados: %d órdenes, %d remesas",
                len(ordenes_filas), len(remesas_filas)
            )
            
            if not ordenes_filas and not remesas_filas:
                logger.warning("XML '%s' no contiene órdenes ni remesas", ruta_xml.name)
                self._manejar_xml_fallido(ruta_xml, "2", "XML sin datos de órdenes/remesas")
                return False, []

            payload_servicios = []

            clients_dict = self._external_api.get_clients_mapping() if self._external_api else {}

            name_for_internal_code = {}
            for nit, info in clients_dict.items():
                raw_code = info.get("code")
                if raw_code:
                    try:
                        norm_code = str(int(str(raw_code).strip()))
                    except (ValueError, TypeError):
                        norm_code = str(raw_code).strip()
                    name_for_internal_code[norm_code] = info.get("name", "")

            logger.info("Diccionario de nombres por código interno: %s", name_for_internal_code)

            def build_payload(filas: List[Dict[str, Any]], tipo_servicio_api: str):
                for fila in filas:
                    codigo_raw = str(fila.get("CODIGO", ""))
                    client_code_raw, punto_limpio, es_sucursal = resolver_codigos_xml(codigo_raw, ruta_xml.name)
                    try:
                        client_code = str(int(str(client_code_raw).strip()))
                    except ValueError:
                        client_code = str(client_code_raw).strip()
                    codigo_concatenado = f"{client_code}-{punto_limpio}" if punto_limpio else ""

                    point_code = codigo_concatenado if es_sucursal else ""
                    atm_code = codigo_concatenado if not es_sucursal else ""
                    
                    fecha_str = fila.get("FECHA DE ENTREGA", "")
                    try:
                        fecha_api = datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d") if fecha_str else datetime.today().strftime("%Y-%m-%d")
                    except ValueError:
                        fecha_api = datetime.today().strftime("%Y-%m-%d")

                    if tipo_servicio_api == "RC":
                        valor_general = 0
                        denominaciones = []
                    else:
                        valor_general = str(fila.get("GENERAL", "0")).replace("$", "").replace(".", "").replace(",", "")
                        denominaciones = fila.get("RAW_DENOMINATIONS", [])

                    rango = str(fila.get("RANGO", "")).strip()
                    bank_name = name_for_internal_code.get(client_code, "Cliente Desconocido")

                    servicio = {
                        "client_code": client_code,
                        "service_type": tipo_servicio_api,
                        "point_code": point_code,
                        "atm_code": atm_code,
                        "service_date": fecha_api,
                        "time_window_start": f"{rango}:00.000Z" if len(rango) == 5 and ":" in rango else "08:00:00.000Z",
                        "time_window_end": "18:00:00.000Z",
                        "declared_amount": valor_general,
                        "currency": "COP",
                        "observations": "Procesado desde XML",
                        "bank_name": bank_name,
                        "bank_account_number": "",
                        "bank_account_holder": "",
                        "requested_denominations": denominaciones
                    }
                    payload_servicios.append(servicio)

            build_payload(ordenes_filas, "PV") # Provision(order)
            build_payload(remesas_filas, "RC") # Recolección(remit)

            dfs = self._transformer.to_dataframes(ordenes_filas, remesas_filas)
            ok_excel = self._transformer.write_excel_and_style(ruta_excel, dfs["ordenes"], dfs["remesas"])
            if not ok_excel:
                self._manejar_xml_fallido(ruta_xml, "2", "Error escribiendo Excel")
                return False, []

            id_para_respuesta = []
            if not dfs["ordenes"].empty:
                id_para_respuesta.extend(dfs["ordenes"]['ID'].dropna().unique().tolist())
            if not dfs["remesas"].empty:
                id_para_respuesta.extend(dfs["remesas"]['ID'].dropna().unique().tolist())

            if id_para_respuesta:
                cc_code = extract_cc_from_filename(ruta_xml.name)
                XMLResponseGenerator.generar_respuesta(id_para_respuesta, ruta_xml.name, "1", cc_code)

            try:
                destino = Config.paths.carpeta_gestionados_xml / ruta_xml.name
                os.makedirs(Config.paths.carpeta_gestionados_xml, exist_ok=True)
                os.rename(ruta_xml, destino)
                logger.info("Archivo XML '%s' movido a gestionados", ruta_xml.name)
            except Exception:
                logger.exception("Error moviendo XML a gestionados (se conserva el éxito del procesamiento)")
            return True, payload_servicios

        except Exception as e:
            logger.exception("Error inesperado procesando XML '%s'", ruta_xml.name)
            self._manejar_xml_fallido(ruta_xml, "2", f"Error inesperado: {e}")
            return False, []
                
    def _manejar_xml_fallido(
        self,
        ruta_xml: Path,
        estado_respuesta: str,
        razon_error: str
    ):
        """
        Maneja archivos XML que fallaron el procesamiento.
        Genera respuesta de rechazo y mueve a carpeta de errores.
        """        
        try:
            cc_local = extract_cc_from_filename(ruta_xml.name)
            XMLResponseGenerator.generar_respuesta(
                [ruta_xml.name],
                ruta_xml.name,
                estado_respuesta,
                cc_local
            )
            
            destino = Config.paths.carpeta_errores_xml / ruta_xml.name
            os.makedirs(Config.paths.carpeta_errores_xml, exist_ok=True)
            os.rename(ruta_xml, destino)
            
        except Exception:
            logger.exception(
                "Error crítico manejando XML fallido '%s'. "
                "El archivo permanece en la carpeta de entrada.",
                ruta_xml.name
            )