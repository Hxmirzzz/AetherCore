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
from src.application.services.insertion_service import InsertionService, ResultadoInsercion

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
    def __init__(
        self,
        reader: XmlFileReader | None = None,
        transformer: XmlDataTransformer | None = None,
        insertion_service: InsertionService | None = None
    ):
        self._reader = reader or XmlFileReader()
        self._transformer = transformer or XmlDataTransformer()
        self._insertion = insertion_service

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
            
            resultados_insercion: List[ResultadoInsercion] = []
            
            if self._insertion:
                logger.info("Iniciando inserción en BD...")
                
                for fila in ordenes_filas:
                    order_data = self._fila_to_order_data(fila)
                    resultado = self._insertion.insertar_desde_xml_order(
                        order_data, 
                        ruta_xml.name
                    )
                    resultados_insercion.append(resultado)
                    
                    if resultado.exitoso:
                        logger.info(f"✅ Order {resultado.numero_pedido} → {resultado.orden_servicio}")
                    else:
                        logger.warning(f"❌ Order {resultado.numero_pedido} → Error: {resultado.error}")
                
                for fila in remesas_filas:
                    remit_data = self._fila_to_remit_data(fila)
                    resultado = self._insertion.insertar_desde_xml_remit(
                        remit_data, 
                        ruta_xml.name
                    )
                    resultados_insercion.append(resultado)
                    
                    if resultado.exitoso:
                        logger.info(f"✅ Remit {resultado.numero_pedido} → {resultado.orden_servicio}")
                    else:
                        logger.warning(f"❌ Remit {resultado.numero_pedido} → Error: {resultado.error}")
                
                # Resumen
                exitosos = sum(1 for r in resultados_insercion if r.exitoso)
                logger.info(f"Inserción completada: {exitosos}/{len(resultados_insercion)} exitosos")
                if exitosos < len(resultados_insercion):
                    logger.warning("Hubo errores en la inserción a BD, pero el procesamiento XML continúa")
            else:
                logger.warning("InsertionService no disponible, se omite inserción en BD")

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

    def _fila_to_order_data(self, fila: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte una fila de order a formato compatible con InsertionService"""
        # Extraer denominaciones
        denominaciones = []
        for key, value in fila.items():
            if isinstance(key, str) and key.startswith('$'):
                # Parsear valor (ej: "$5.000.000" → 5000000)
                valor_str = str(value).replace('$', '').replace('.', '').replace(',', '')
                try:
                    amount = int(valor_str)
                    if amount > 0:
                        # Extraer código (ej: "$50000 AD" → "50000AD")
                        code = key.replace('$', '').replace(' ', '')
                        denominaciones.append({'code': code, 'amount': amount})
                except ValueError:
                    continue
        
        return {
            'id': fila.get('ID', ''),
            'entityReferenceID': fila.get('CODIGO', ''),
            'deliveryDate': self._parse_fecha_display(fila.get('FECHA DE ENTREGA', '')),
            'orderDate': self._parse_fecha_display(fila.get('FECHA DE ENTREGA', '')),
            'primaryTransport': fila.get('TRANSPORTADORA', ''),
            'denominaciones': denominaciones,
            'divisa': 'COP'
        }
    
    def _fila_to_remit_data(self, fila: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte una fila de remit a formato compatible con InsertionService"""
        return {
            'id': fila.get('ID', ''),
            'entityReferenceID': fila.get('CODIGO', ''),
            'pickupDate': self._parse_fecha_display(fila.get('FECHA DE ENTREGA', '')),
            'divisa': 'COP'
        }
    
    def _parse_fecha_display(self, fecha_display: str) -> str:
        """Convierte fecha DD/MM/YYYY a YYYY-MM-DD"""
        if not fecha_display or '/' not in fecha_display:
            return ''
        try:
            parts = fecha_display.split('/')
            return f"{parts[2]}-{parts[1]}-{parts[0]}"  # YYYY-MM-DD
        except:
            return ''

    def _estados_por_id(self, df_ordenes: pd.DataFrame, df_remesas: pd.DataFrame) -> Dict[str, str]:
        """
        Determina el estado por ID combinando:
        1. Validación de datos (puntos no encontrados, etc.)
        2. Resultado de inserción en BD
        
        Returns:
            Dict {ID: estado} donde estado es "1" (éxito) o "2" (error)
        """
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