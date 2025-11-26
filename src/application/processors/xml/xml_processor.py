"""
Orquestador XML: une reader + transformer + response generator.
Mantiene rutas de salida, nombres y formato de respuesta idénticos al código original.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import os
import logging
import pandas as pd

from src.infrastructure.config.settings import get_config
from src.infrastructure.config.mapeos import TextosConstantes
from .xml_file_reader import XmlFileReader
from .xml_mappers import map_elements, extract_cc_from_filename, build_timestamp_for_response
from .xml_data_transformer import XmlDataTransformer

Config = get_config()
logger = logging.getLogger(__name__)

class XMLResponseGenerator:
    """Genera archivos de respuesta .txt para XMLs procesados."""
    
    @staticmethod
    def generar_respuesta(lista_ids: List[str], nombre_archivo_original: str,
        punto_de_referencia: str, estado: str,
        cc_code_from_filename_passed: str, conn: Any) -> bool:
        """
        Genera archivo de respuesta con formato: TR2_VATCO_CCCODEAAMMDDHHMM.txt
        
        Args:
            lista_ids: Lista de IDs de órdenes/remesas
            nombre_archivo_original: Nombre del XML original
            punto_de_referencia: Primer punto encontrado (para logs)
            estado: "1" éxito, "2" error/rechazo
            cc_code_from_filename_passed: CC Code extraído del nombre del archivo
            conn: Conexión a BD (para compatibilidad)
            
        Returns:
            True si se generó correctamente, False en caso contrario
        """
        try:
            if not lista_ids:
                logger.warning("No hay IDs para generar respuesta XML para '%s'", nombre_archivo_original)
                return False
            
            os.makedirs(Config.paths.carpeta_respuesta_txt, exist_ok=True)
            ts = build_timestamp_for_response(nombre_archivo_original)
            nombre_respuesta = f"TR2_VATCO_{cc_code_from_filename_passed}{ts}.txt"
            ruta_respuesta = Config.paths.carpeta_respuesta_txt / nombre_respuesta
            with open(ruta_respuesta, 'w', encoding='utf-8') as f:
                for id_val in sorted(lista_ids):
                    f.write(f"{id_val.strip()},{estado}\n")
            logger.info("Respuesta XML generada: %s con estado '%s'", nombre_respuesta, estado)
            return True
        except Exception:
            logger.exception("Error generando respuesta XML para '%s'", nombre_archivo_original)
            return False

class XMLProcessor:
    """
    Procesador principal de archivos XML.
    Replica EXACTAMENTE la lógica del código original.
    """
    def __init__(self, reader: XmlFileReader | None = None, transformer: XmlDataTransformer | None = None):
        self._reader = reader or XmlFileReader()
        self._transformer = transformer or XmlDataTransformer()

    def procesar_archivo_xml(self, ruta_xml: Path, ruta_excel: Path, puntos_info: Dict[str, Dict[str, str]], conn: Any) -> bool:
        """
        Procesa un archivo XML y genera Excel + archivo de respuesta.
        
        Args:
            ruta_xml: Ruta al archivo XML
            ruta_excel: Ruta donde guardar el Excel
            puntos_info: Diccionario con información de puntos de la BD
            conn: Conexión a la base de datos
            
        Returns:
            True si el procesamiento fue exitoso, False en caso contrario
        """
        try:
            logger.info("Iniciando procesamiento del archivo XML: '%s'", ruta_xml.name)
            
            info = self._reader.read(ruta_xml)
            if info.get("empty", False):
                logger.error("Archivo XML vacío: '%s'", ruta_xml.name)
                self._manejar_xml_fallido(ruta_xml, "2", "Archivo XML vacío", conn)
                return False

            root = info["root"]
            ordenes_elements = self._reader.find_elements(root, "order")
            remesas_elements = self._reader.find_elements(root, "remit")
            ordenes_filas = map_elements(ordenes_elements, TextosConstantes.SERVICIO_PROVISION_XML, puntos_info)
            remesas_filas = map_elements(remesas_elements, TextosConstantes.SERVICIO_RECOLECCION_XML, puntos_info)
            
            logger.info(
                "Elementos procesados: %d órdenes, %d remesas",
                len(ordenes_filas), len(remesas_filas)
            )
            
            if not ordenes_filas and not remesas_filas:
                logger.warning("XML '%s' no contiene órdenes ni remesas", ruta_xml.name)
                self._manejar_xml_fallido(ruta_xml, "2", "XML sin datos de órdenes/remesas", conn)
                return False

            dfs = self._transformer.to_dataframes(ordenes_filas, remesas_filas)
            df_ordenes = dfs["ordenes"]
            df_remesas = dfs["remesas"]
            
            ok_excel = self._transformer.write_excel_and_style(ruta_excel, df_ordenes, df_remesas)
            if not ok_excel:
                logger.error("Error escribiendo Excel para '%s'", ruta_xml.name)
                self._manejar_xml_fallido(ruta_xml, "2", "Error escribiendo Excel", conn)
                return False
            
            estados_por_id = self._estados_por_id(df_ordenes, df_remesas)

            id_para_respuesta: list[str] = []
            if not df_ordenes.empty:
                id_para_respuesta.extend(df_ordenes['ID'].dropna().unique().tolist())
            if not df_remesas.empty:
                id_para_respuesta.extend(df_remesas['ID'].dropna().unique().tolist())

            id_para_respuesta = sorted(set(str(i).strip() for i in id_para_respuesta))

            if id_para_respuesta:
                # Determinar si TODOS los estados son "2" (rechazo)
                estados_usados = {estados_por_id.get(str(i), "1") for i in id_para_respuesta}
                solo_errores = estados_usados and estados_usados.issubset({"2"})

                if solo_errores:
                    cc_code = "00"
                else:
                    cc_code = extract_cc_from_filename(ruta_xml.name)

                os.makedirs(Config.paths.carpeta_respuesta_txt, exist_ok=True)
                ts = build_timestamp_for_response(ruta_xml.name)
                nombre_respuesta = f"TR2_VATCO_{cc_code}{ts}.txt"
                ruta_respuesta = Config.paths.carpeta_respuesta_txt / nombre_respuesta

                with open(ruta_respuesta, "w", encoding="utf-8") as f:
                    for id_val in id_para_respuesta:
                        estado = estados_por_id.get(str(id_val), "1")
                        f.write(f"{str(id_val).strip()},{estado}\n")

                logger.info("Respuesta XML generada (por ID): %s", nombre_respuesta)
            else:
                logger.warning(
                    "No se encontraron IDs para generar respuesta para '%s'",
                    ruta_xml.name
                )

            try:
                destino = Config.paths.carpeta_gestionados_xml / ruta_xml.name
                os.makedirs(Config.paths.carpeta_gestionados_xml, exist_ok=True)
                os.rename(ruta_xml, destino)
                logger.info("Archivo XML '%s' movido a gestionados", ruta_xml.name)
            except Exception:
                logger.exception("Error moviendo XML a gestionados (se conserva el éxito del procesamiento)")
            return True

        except Exception as e:
            logger.exception("Error inesperado procesando XML '%s'", ruta_xml.name)
            self._manejar_xml_fallido(ruta_xml, "2", f"Error inesperado: {e}", conn)
            return False

    def _determinar_estado_respuesta(
        self,
        df_ordenes: pd.DataFrame,
        df_remesas: pd.DataFrame
    ) -> str:
        """
        Determina el estado de respuesta basado en si hay puntos no encontrados.
        
        Returns:
            "1" si todos los puntos fueron encontrados
            "2" si algún punto no fue encontrado
        """
        textos_error = [
            TextosConstantes.PUNTO_NO_ENCONTRADO_XML,
            TextosConstantes.CLIENTE_NO_ENCONTRADO,
            TextosConstantes.CIUDAD_NO_ENCONTRADA
        ]

        def tiene_errores(df: pd.DataFrame) -> bool:
            if df.empty:
                return False
            for col in ['NOMBRE PUNTO', 'ENTIDAD', 'CIUDAD']:
                if col in df.columns and not df[col].empty:
                    col_series = df[col].astype(str)
                    for texto_error in textos_error:
                        if col_series.str.contains(texto_error, case=False, na=False).any():
                            logger.warning(
                                "Estado '2': encontrado '%s' en columna '%s'",
                                texto_error, col
                            )
                            return True
            return False

        if tiene_errores(df_ordenes) or tiene_errores(df_remesas):
            return "2"
        return "1"

    def _estados_por_id(self, df_ordenes: pd.DataFrame, df_remesas: pd.DataFrame) -> Dict[str, str]:
        textos_error = [
            TextosConstantes.PUNTO_NO_ENCONTRADO_XML,
            TextosConstantes.CLIENTE_NO_ENCONTRADO,
            TextosConstantes.CIUDAD_NO_ENCONTRADA,
        ]

        def estado_de_row(row: pd.Series) -> str:
            for col in ['NOMBRE PUNTO', 'ENTIDAD', 'CIUDAD']:
                if col in row and isinstance(row[col], str):
                    for t in textos_error:
                        if t.lower() in row[col].lower():
                            return "2"
            return "1"  

        estados: Dict[str, str] = {}

        if not df_ordenes.empty:
            for _, row in df_ordenes.iterrows():
                if 'ID' in row and pd.notna(row['ID']):
                    estados[str(row['ID'])] = estado_de_row(row)

        if not df_remesas.empty:
            for _, row in df_remesas.iterrows():
                if 'ID' in row and pd.notna(row['ID']):
                    estados[str(row['ID'])] = estado_de_row(row)

        return estados
                
    def _manejar_xml_fallido(
        self,
        ruta_xml: Path,
        estado_respuesta: str,
        razon_error: str,
        conn: Any
    ):
        """
        Maneja archivos XML que fallaron el procesamiento.
        Genera respuesta de rechazo y mueve a carpeta de errores.
        """
        logger.error(
            "Manejando XML fallido: '%s'. Razón: %s. Estado: '%s'",
            ruta_xml.name, razon_error, estado_respuesta
        )
        
        try:
            # Generar respuesta de error
            ids_dummy = [ruta_xml.name]
            cc_local = extract_cc_from_filename(ruta_xml.name)
            
            XMLResponseGenerator.generar_respuesta(
                ids_dummy,
                ruta_xml.name,
                "N/A",
                estado_respuesta,
                cc_local,
                conn
            )
            
            logger.info("Respuesta '%s' generada para XML fallido: '%s'", estado_respuesta, ruta_xml.name)
            
            # Mover a carpeta de errores
            destino = Config.paths.carpeta_errores_xml / ruta_xml.name
            os.makedirs(Config.paths.carpeta_errores_xml, exist_ok=True)
            os.rename(ruta_xml, destino)
            
            logger.info("Archivo XML '%s' movido a errores", ruta_xml.name)
            
        except Exception:
            logger.exception(
                "Error crítico manejando XML fallido '%s' (razón: %s). "
                "El archivo permanece en la carpeta de entrada.",
                ruta_xml.name, razon_error
            )