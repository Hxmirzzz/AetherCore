from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import logging, os
import pandas as pd

from .txt_file_reader import TxtFileReader
from .txt_data_transformer import TxtDataTransformer
from src.infrastructure.file_system.path_manager import PathManager
from src.infrastructure.config.mapeos import TextosConstantes
from src.application.processors.xml.xml_mappers import extract_cc_from_filename, build_timestamp_for_response
from .txt_mappers import parse_tipo_records
from src.infrastructure.config.mapeos import ClienteMapeos

from src.infrastructure.repositories.ciudad_repository import CiudadRepository
from src.infrastructure.repositories.sucursal_repository import SucursalRepository
from src.infrastructure.repositories.cliente_repository import ClienteRepository
from src.infrastructure.repositories.punto_repository import PuntoRepository
from src.domain.value_objects.codigo_punto import CodigoPunto

logger = logging.getLogger(__name__)

class TXTResponseGenerator:
    @staticmethod
    def generar_respuesta(
        ids: List[str],
        nombre_archivo_original: str,
        carpeta_respuesta: Path,
        estado: str = "1",
        cc_override: str | None = None,
    ) -> bool:
        try:
            if not ids:
                return False
            os.makedirs(carpeta_respuesta, exist_ok=True)
            ts = build_timestamp_for_response(nombre_archivo_original)
            if cc_override and cc_override.strip():
                cc = cc_override.strip()
            else:
                cc = extract_cc_from_filename(nombre_archivo_original)
            nombre = f"TR2_VATCO_{cc}{ts}.txt"
            ruta = carpeta_respuesta / nombre
            with open(ruta, "w", encoding="utf-8") as f:
                for i in sorted(ids):
                    f.write(f"{str(i).strip()},{estado}\n")
            logger.info("Respuesta TXT generada: %s", nombre)
            return True
        except Exception:
            logger.exception("Error generando respuesta TXT")
            return False

    @staticmethod
    def generar_respuesta_por_id(
        pares_id_estado: List[tuple[str, str]],
        nombre_archivo_original: str,
        carpeta_respuesta: Path,
        cc_override: str | None = None,
    ) -> bool:
        """
        Genera respuesta por cada ID con su propio estado.
        pares_id_estado: lista de tuplas (ID, estado)
        """
        try:
            if not pares_id_estado:
                return False

            os.makedirs(carpeta_respuesta, exist_ok=True)
            ts = build_timestamp_for_response(nombre_archivo_original)

            if cc_override and cc_override.strip():
                cc = cc_override.strip()
            else:
                cc = extract_cc_from_filename(nombre_archivo_original)

            nombre = f"TR2_VATCO_{cc}{ts}.txt"
            ruta = carpeta_respuesta / nombre

            with open(ruta, "w", encoding="utf-8") as f:
                # Ordenamos por ID solo para dejar la salida ordenada
                for id_val, est in sorted(pares_id_estado, key=lambda t: str(t[0])):
                    f.write(f"{str(id_val).strip()},{str(est).strip()}\n")

            logger.info("Respuesta TXT generada (por ID): %s", nombre)
            return True
        except Exception:
            logger.exception("Error generando respuesta TXT por ID")
            return False
        
class TXTProcessor:
    def __init__(self, reader: TxtFileReader | None = None, transformer: TxtDataTransformer | None = None, paths: PathManager | None = None):
        self._reader = reader or TxtFileReader()
        self._transformer = transformer or TxtDataTransformer()
        self._paths = paths or PathManager()

    def procesar_archivo_txt(self, ruta_txt: Path, conn: Any) -> bool:
        try:
            info = self._reader.read(ruta_txt)
            if info.get("empty", False):
                self._manejar_txt_fallido(ruta_txt, "2", "TXT vacío", conn)
                return False

            df_raw = info["df"]

            enc = info.get("encoding") or "utf-8"
            with open(ruta_txt, "r", encoding=enc, errors="ignore") as f:
                raw_lines = [ln.rstrip("\n") for ln in f.readlines()]

            has_t1 = any(ln.startswith("1,") for ln in raw_lines)
            has_t2 = any(ln.startswith("2,") for ln in raw_lines)
            has_t3 = any(ln.startswith("3,") for ln in raw_lines)
            es_por_tipos = has_t1 and has_t2 and has_t3

            out_xlsx = self._paths.output_txt_dir() / f"{ruta_txt.stem}.xlsx"

            if es_por_tipos:
                ciud_repo = CiudadRepository(conn)
                punto_repo = PuntoRepository(conn)
                
                dict_ciudades = ciud_repo.obtener_todas()
                dict_clientes, dict_sucursales = punto_repo.mapas_para_mappers()
                dict_clientes    = { CodigoPunto.from_raw(k).parte_numerica: v for k, v in dict_clientes.items() }
                dict_sucursales  = { CodigoPunto.from_raw(k).parte_numerica: v for k, v in dict_sucursales.items() }
                
                dict_tipos_servicio = {}
                dict_categorias = {}
                dict_tipo_valor = {}
    
                df1, df2, df3 = parse_tipo_records(
                    raw_lines,
                    dict_ciudades,
                    dict_tipos_servicio,
                    dict_categorias,
                    dict_tipo_valor,
                    dict_sucursales,
                    dict_clientes
                )

                ok_excel = self._transformer.write_excel_consolidated(out_xlsx, df1, df2, df3, hoja_titulo="Consolidado")
                if not ok_excel:
                    self._manejar_txt_fallido(ruta_txt, "2", "Error escribiendo Excel consolidado", conn)
                    return False

                ids = []
                if df2 is not None and not df2.empty and 'CODIGO' in df2.columns:
                    ids = sorted(set(str(x).strip() for x in df2['CODIGO'].dropna().tolist()))
                if not ids:
                    ids = [ruta_txt.name]
                    
                cc_from_client = None
                if df2 is not None and not df2.empty and 'CODIGO PUNTO' in df2.columns:
                    for punto_cod in df2['CODIGO PUNTO'].dropna().unique():
                        try:
                            punto_cod = str(punto_cod).strip()
                            info_cli = dict_clientes.get(punto_cod, {})
                            cod_cliente_raw = info_cli.get('cod_cliente')
                            
                            if cod_cliente_raw:
                                cc_from_client = ClienteMapeos.get_cc_code(str(cod_cliente_raw).strip())
                                if cc_from_client and cc_from_client != "00":
                                    break
                        except Exception:
                            continue

                if not cc_from_client or cc_from_client == "00":
                    cc_from_client = extract_cc_from_filename(ruta_txt.name)

                estados_por_id = self._estados_por_codigo(df2 if df2 is not None else pd.DataFrame())

                if estados_por_id:
                    pares_id_estado = [
                        (id_val, estados_por_id.get(id_val, "1"))
                        for id_val in ids
                    ]

                    TXTResponseGenerator.generar_respuesta_por_id(
                        pares_id_estado,
                        ruta_txt.name,
                        self._paths.respuestas_txt_dir(),
                        cc_override=cc_from_client,
                    )
                else:
                    estado = self._estado_para_respuesta(df2 if df2 is not None else pd.DataFrame())
                    TXTResponseGenerator.generar_respuesta(
                        ids,
                        ruta_txt.name,
                        self._paths.respuestas_txt_dir(),
                        estado=estado,
                        cc_override=cc_from_client,
                    )

            try:
                destino = self._paths.gestionados_txt_dir() / ruta_txt.name
                os.makedirs(self._paths.gestionados_txt_dir(), exist_ok=True)
                os.rename(ruta_txt, destino)
                logger.info("Archivo TXT movido a gestionados: %s", destino)
            except Exception:
                logger.exception("Error moviendo TXT a gestionados (se conserva el éxito del procesamiento)")

            return True

        except Exception as e:
            logger.exception("Error inesperado en procesamiento TXT")
            self._manejar_txt_fallido(ruta_txt, "2", f"Error inesperado: {e}", conn)
            return False

    def _manejar_txt_fallido(self, ruta_txt: Path, estado_respuesta: str, razon_error: str, conn: Any):
        """Maneja archivos TXT que fallaron en el procesamiento"""
        try:
            logger.error("Manejando TXT fallido '%s': %s", ruta_txt.name, razon_error)
            
            ids_dummy = [ruta_txt.name]
            TXTResponseGenerator.generar_respuesta(ids_dummy, ruta_txt.name, self._paths.respuestas_txt_dir(), estado=estado_respuesta)
            destino = self._paths.errores_txt_dir() / ruta_txt.name
            os.makedirs(self._paths.errores_txt_dir(), exist_ok=True)
            os.rename(ruta_txt, destino)
        except Exception:
            logger.exception("Error manejando TXT fallido")
            
    def _estado_para_respuesta(self, df: pd.DataFrame) -> str:
        """
        Determina el estado de respuesta basado en valores 'no encontrado'.
        
        Returns:
            "1" si todo está OK, "2" si hay errores
        """
        textos_error = {
            TextosConstantes.CLIENTE_NO_ENCONTRADO,
            TextosConstantes.CIUDAD_NO_ENCONTRADA,
            TextosConstantes.SUCURSAL_NO_ENCONTRADA,
            TextosConstantes.TIPO_NO_ENCONTRADO,
            TextosConstantes.PUNTO_NO_ENCONTRADO_XML,
            TextosConstantes.CATEGORIA_NO_ENCONTRADA,
        }
        try:
            for col in df.columns:
                serie = df[col].astype(str)
                for texto_error in textos_error:
                    if serie.str.contains(texto_error, case=False, regex=False).any():
                        logger.warning("Estado '2' por encontrar: %s en columna %s", texto_error, col)
                        return "2"
            return "1"
        except Exception:
            logger.exception("Error determinando estado de respuesta")
            return "1"

    def _estados_por_codigo(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Determina el estado de respuesta por CODIGO (ID de solicitud).
        
        Retorna un dict { '59729603': '2', '59729604': '1', ... }.
        """
        estados: dict[str, str] = {}

        if df is None or df.empty or 'CODIGO' not in df.columns:
            return estados

        textos_error = {
            TextosConstantes.CLIENTE_NO_ENCONTRADO,
            TextosConstantes.CIUDAD_NO_ENCONTRADA,
            TextosConstantes.SUCURSAL_NO_ENCONTRADA,
            TextosConstantes.TIPO_NO_ENCONTRADO,
            TextosConstantes.PUNTO_NO_ENCONTRADO_XML,
            TextosConstantes.CATEGORIA_NO_ENCONTRADA,
        }

        try:
            for codigo, subdf in df.groupby('CODIGO'):
                estado = "1"
                for col in subdf.columns:
                    serie = subdf[col].astype(str)
                    for texto_error in textos_error:
                        if serie.str.contains(texto_error, case=False, regex=False).any():
                            estado = "2"
                            break
                    if estado == "2":
                        break

                estados[str(codigo).strip()] = estado

        except Exception:
            logger.exception("Error determinando estado por CODIGO")
        return estados
    
    def _estados_por_codigo(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Determina el estado de respuesta por CODIGO (ID de solicitud).
        
        Retorna un dict { '59729603': '2', '59729604': '1', ... }.
        """
        estados: dict[str, str] = {}

        if df is None or df.empty or 'CODIGO' not in df.columns:
            return estados

        textos_error = {
            TextosConstantes.CLIENTE_NO_ENCONTRADO,
            TextosConstantes.CIUDAD_NO_ENCONTRADA,
            TextosConstantes.SUCURSAL_NO_ENCONTRADA,
            TextosConstantes.TIPO_NO_ENCONTRADO,
            TextosConstantes.PUNTO_NO_ENCONTRADO_XML,
            TextosConstantes.CATEGORIA_NO_ENCONTRADA,
        }

        try:
            for codigo, subdf in df.groupby('CODIGO'):
                estado = "1"
                for col in subdf.columns:
                    serie = subdf[col].astype(str)
                    for texto_error in textos_error:
                        if serie.str.contains(texto_error, case=False, regex=False).any():
                            estado = "2"
                            break
                    if estado == "2":
                        break

                estados[str(codigo).strip()] = estado

        except Exception:
            logger.exception("Error determinando estado por CODIGO")
        return estados