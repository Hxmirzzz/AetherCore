from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging, os
import pandas as pd
from datetime import datetime

from .txt_file_reader import TxtFileReader
from .txt_data_transformer import TxtDataTransformer
from src.infrastructure.file_system.path_manager import PathManager
from src.application.processors.xml.xml_mappers import extract_cc_from_filename, build_timestamp_for_response
from .txt_mappers import parse_tipo_records
from src.infrastructure.config.settings import get_config
from src.infrastructure.api.external_api_client import ExternalApiClient
from src.domain.entities.catalogs import ServicioCatalogo

Config = get_config()
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
                for id_val, est in sorted(pares_id_estado, key=lambda t: str(t[0])):
                    f.write(f"{str(id_val).strip()},{str(est).strip()}\n")

            logger.info("Respuesta TXT generada (por ID): %s", nombre)
            return True
        except Exception:
            logger.exception("Error generando respuesta TXT por ID")
            return False
        
class TXTProcessor:
    def __init__(
        self,
        reader: TxtFileReader | None = None,
        transformer: TxtDataTransformer | None = None,
        paths: PathManager | None = None,
        external_api: ExternalApiClient | None = None,
    ):
        self._reader = reader or TxtFileReader()
        self._transformer = transformer or TxtDataTransformer()
        self._paths = paths or PathManager()
        self._external_api = external_api

    def procesar_archivo_txt(self, ruta_txt: Path) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Retorna una tupla: (Exito_booleano, Lista_de_Servicios_Payload)
        """
        try:
            info = self._reader.read(ruta_txt)
            if info.get("empty", False):
                self._manejar_txt_fallido(ruta_txt, "2", "TXT vacío")
                return False, []

            df_raw = info["df"]
            enc = info.get("encoding") or "utf-8"

            with open(ruta_txt, "r", encoding=enc, errors="ignore") as f:
                raw_lines = [ln.rstrip("\n") for ln in f.readlines()]

            has_t1 = any(ln.startswith("1,") for ln in raw_lines)
            has_t2 = any(ln.startswith("2,") for ln in raw_lines)
            has_t3 = any(ln.startswith("3,") for ln in raw_lines)
            es_por_tipos = has_t1 and has_t2 and has_t3

            out_xlsx = self._paths.output_txt_dir() / f"{ruta_txt.stem}.xlsx"
            payload_servicios = []

            if es_por_tipos:
                df1, df2, df3 = parse_tipo_records(
                    raw_lines,
                    dict_ciudades={},
                    dict_tipos_servicio={},
                    dict_categorias={},
                    dict_tipo_valor={},
                    dict_sucursales={},
                    dict_clientes={}
                )

                clientes_dict = self._external_api.get_clients_mapping() if self._external_api else {}
                fecha_programacion = datetime.now().strftime("%Y-%m-%d")
                nit_client = ""

                if df1 is not None and not df1.empty:
                    if 'FECHA GENERACION' in df1.columns:
                        fecha_str = str(df1['FECHA GENERACION'].iloc[0]).strip()
                        if fecha_str:
                            try:
                                fecha_programacion = datetime.strptime(fecha_str, "%Y%m%d").strftime("%Y-%m-%d")
                            except:
                                pass
                    if 'NIT CLIENTE' in df1.columns:
                        nit_client = str(df1['NIT CLIENTE'].iloc[0]).strip()

                info_client = clientes_dict.get(nit_client, {})
                client_code = info_client.get("code", "") or extract_cc_from_filename(ruta_txt.name)
                bank_name = info_client.get("name", "")

                if df2 is not None and not df2.empty:
                    if bank_name:
                        df2['CLIENTE'] = bank_name

                ok_excel = self._transformer.write_excel_consolidated(out_xlsx, df1, df2, df3, hoja_titulo="Consolidado")
                if not ok_excel:
                    self._manejar_txt_fallido(ruta_txt, "2", "Error escribiendo Excel consolidado")
                    return False, []

                if df2 is not None and not df2.empty:
                    for _, row in df2.iterrows():
                        punto_limpio = str(row.get("CODIGO PUNTO", "")).strip()
                        atm_code = f"{client_code}-{punto_limpio}" if punto_limpio else ""

                        codigo_servicio = row.get("SERVICIO", 0)
                        try:
                            codigo_servicio = int(codigo_servicio)
                        except ValueError:
                            codigo_servicio = 0
                        service_type_code = ServicioCatalogo.obtener_codigo_api(codigo_servicio, default="PA")
                        
                        valor_total = str(row.get("TOTAL_VALOR", "0")).replace("$", "").replace(".", "").replace(",", "").strip()

                        denominations_array = []
                        for col in df2.columns:
                            if isinstance(col, str) and col.startswith("GAV") and "DENOMINACION" in col:
                                cant_col = col.replace("DENOMINACION", "CANTIDAD")

                                if cant_col in df2.columns:
                                    denom_str = str(row.get(col, "0")).replace("$", "").replace(".", "").replace(",", "").strip()
                                    cant_str = str(row.get(cant_col, "0")).replace("$", "").replace(".", "").replace(",", "").strip()

                                    try:
                                        denom_int = int(denom_str)
                                        cant_int = int(cant_str)

                                        if denom_int > 0 and cant_int > 0:
                                            denominations_array.append({
                                                "denomination_value": f"{denom_int}.00",
                                                "quality": "PA",
                                                "quantity": cant_int
                                            })
                                    except ValueError:
                                        pass
                        
                        servicio = {
                            "client_code": client_code,
                            "service_type": service_type_code,
                            "atm_code": atm_code,
                            "service_date": fecha_programacion,
                            "time_window_start": "08:00:00.000Z",
                            "time_window_end": "18:00:00.000Z",
                            "declared_amount": valor_total,
                            "currency": "COP",
                            "observations": str(row.get("OBSERVACIONES", "")).strip(),
                            "bank_name": bank_name,
                            "bank_account_number": "",
                            "bank_account_holder": "",
                            "requested_denominations": denominations_array
                        }
                        payload_servicios.append(servicio)

                ids = [] 
                if df2 is not None and not df2.empty and 'CODIGO' in df2.columns:
                    ids = sorted(set(str(x).strip() for x in df2['CODIGO'].dropna().tolist()))
                if not ids:
                    ids = [ruta_txt.name]
                    
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
                os.replace(ruta_txt, destino)
                logger.info("Archivo TXT movido a gestionados: %s", destino)
            except Exception:
                logger.exception("Error moviendo TXT a gestionados (se conserva el éxito del procesamiento)")

            return True, payload_servicios

        except Exception as e:
            logger.exception("Error inesperado en procesamiento TXT")
            self._manejar_txt_fallido(ruta_txt, "2", f"Error inesperado: {e}")
            return False, []

    def _manejar_txt_fallido(self, ruta_txt: Path, estado_respuesta: str, razon_error: str):
        """Maneja archivos TXT que fallaron en el procesamiento"""
        try:
            logger.error("Manejando TXT fallido '%s': %s", ruta_txt.name, razon_error)
            
            ids_dummy = [ruta_txt.name]
            TXTResponseGenerator.generar_respuesta(ids_dummy, ruta_txt.name, self._paths.respuestas_txt_dir(), estado=estado_respuesta)
            destino = Config.paths.carpeta_errores_txt / ruta_txt.name
            os.makedirs(Config.paths.carpeta_errores_txt, exist_ok=True)
            os.replace(ruta_txt, destino)
        except Exception:
            logger.exception("Error manejando TXT fallido")
            
    def _estado_para_respuesta(self, df: pd.DataFrame = None) -> str:
        return "1"

    def _estados_por_codigo(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Determina el estado de respuesta por CODIGO (ID de solicitud).
        
        Retorna un dict { '59729603': '2', '59729604': '1', ... }.
        """
        estados: dict[str, str] = {}

        if df is None or df.empty or 'CODIGO' not in df.columns:
            return estados

        try:
            for codigo, _ in df.groupby('CODIGO'):
                estados[str(codigo).strip()] = "1"
        except Exception:
            logger.exception("Error determinando estado por CODIGO")
        return estados