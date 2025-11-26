from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, List, Dict
from datetime import datetime
import re

from src.infrastructure.file_system.path_manager import PathManager

class ResponseService:
    """
    Genera el TXT de respuesta al estilo de tu XMLResponseGenerator original.
    Nombre: TR2_VATCO_<CCCODE><AAMMDDHHMMSS>.txt
    Contenido: una línea por ID:  ID,ESTADO
    """

    def __init__(self, paths: PathManager):
        self._paths = paths

    # --------- Helpers internos ---------
    @staticmethod
    def _extract_cc_code_from_filename(xml_name: str) -> str:
        """
        Del nombre 'ICOREX_C4U-01-Vatco_2656_YYYYMMDD_HHMMSS.xml' extrae '01' (si existe).
        Si no se puede, usa '00'.
        """
        try:
            parts = xml_name.split('_')
            if len(parts) > 1 and parts[1].startswith('C4U-'):
                segment = parts[1][4:]  # después de 'C4U-'
                m = re.match(r'^\d{2}', segment)
                if m:
                    return m.group(0)
        except Exception:
            pass
        return '00'

    @staticmethod
    def _extract_timestamp_for_name(xml_name: str) -> str:
        """
        Usa YYYYMMDD y HHMMSS del nombre para armar AAMMDDHHMMSS.
        Si falla, usa ahora().
        """
        try:
            parts = xml_name.split('_')
            if len(parts) >= 5:
                ymd = parts[3]                         # '20250512'
                hms_with_ext = parts[4]                # '164009.xml' o '164009 (1).xml'
                hms = hms_with_ext.split('.')[0]       # '164009' o '164009 (1)'
                # Si trae " (1)" u otro sufijo, limpiar a dígitos:
                hms = ''.join(ch for ch in hms if ch.isdigit())
                if len(ymd) == 8 and len(hms) >= 4:    # mínimo HHMM
                    # si no trae segundos, asumimos '00'
                    if len(hms) == 4:
                        hms = hms + '00'
                    elif len(hms) > 6:
                        hms = hms[:6]
                    dt = datetime.strptime(ymd + hms, '%Y%m%d%H%M%S')
                    return dt.strftime('%y%m%d%H%M%S')
        except Exception:
            pass
        return datetime.now().strftime('%y%m%d%H%M%S')

    @staticmethod
    def _collect_ids(dataset: Any) -> List[str]:
        """
        Soporta:
        - Pandas DataFrames (con columna 'ID')
        - Lista[Dict] con clave 'ID'
        - Dict con DataFrames/listas dentro
        """
        ids: List[str] = []

        # Pandas DataFrame
        try:
            import pandas as pd  # opcional
            if isinstance(dataset, pd.DataFrame):
                if 'ID' in dataset.columns:
                    ids = [str(x) for x in dataset['ID'].dropna().astype(str).tolist()]
                    return ids
        except Exception:
            pass

        # Lista de dicts
        if isinstance(dataset, list) and dataset and isinstance(dataset[0], dict):
            for row in dataset:
                val = row.get('ID')
                if val is not None:
                    ids.append(str(val))
            return ids

        # Dict con posibles estructuras dentro
        if isinstance(dataset, dict):
            # Intenta 'provision'/'recoleccion' tipo DataFrame/lista
            for key in ('provision', 'recoleccion', 'ordenes', 'remesas', 'rows', 'data'):
                sub = dataset.get(key)
                if sub is None:
                    continue
                sub_ids = ResponseService._collect_ids(sub)
                if sub_ids:
                    ids.extend(sub_ids)
            # Como fallback, si hay 'ID' plano
            val = dataset.get('ID')
            if val is not None:
                ids.append(str(val))

        # Unificar + sin duplicados
        return sorted(list(set(ids)))

    @staticmethod
    def _compute_estado(dataset: Any) -> str:
        """
        Estado '2' si hay NO ENCONTRADO en:
        - NOMBRE PUNTO
        - ENTIDAD
        - CIUDAD
        En DataFrames o listas de dicts.
        """
        # Pandas DataFrame
        try:
            import pandas as pd
            if isinstance(dataset, pd.DataFrame) and not dataset.empty:
                cols = dataset.columns.str.upper()
                def has_bad(col_name: str) -> bool:
                    if col_name in cols:
                        s = dataset[dataset.columns[cols.get_loc(col_name)]].astype(str)
                        return s.str.contains('NO ENCONTRADO', case=False, na=False).any()
                    return False
                if has_bad('NOMBRE PUNTO') or has_bad('ENTIDAD') or has_bad('CIUDAD'):
                    return '2'
        except Exception:
            pass

        # Lista de dicts
        if isinstance(dataset, list) and dataset and isinstance(dataset[0], dict):
            for row in dataset:
                for k in ('NOMBRE PUNTO', 'ENTIDAD', 'CIUDAD'):
                    val = str(row.get(k, '')).upper()
                    if 'NO ENCONTRADO' in val:
                        return '2'

        # Dict con subestructuras
        if isinstance(dataset, dict):
            for key in ('provision', 'recoleccion', 'ordenes', 'remesas', 'rows', 'data'):
                sub = dataset.get(key)
                if sub is not None and ResponseService._compute_estado(sub) == '2':
                    return '2'
        return '1'

    # --------- API principal ---------
    def generate_and_save(self, dataset: Any, ruta_excel: Path, source_xml_path: str) -> Path | None:
        """
        Genera el TXT de respuesta en la carpeta de respuesta (paths['respuesta_txt']).
        dataset: info ya transformada.
        ruta_excel: ruta del excel generado (puede ser None).
        source_xml_path: ruta del XML original (para nombre y cc_code).
        """
        try:
            xml_name = Path(source_xml_path).name

            ids = self._collect_ids(dataset)
            if not ids:
                # Si no hay IDs, por compatibilidad, usa el nombre del archivo como único ID
                ids = [xml_name]

            estado = self._compute_estado(dataset)
            cc_code = self._extract_cc_code_from_filename(xml_name)
            timestamp = self._extract_timestamp_for_name(xml_name)

            file_name = f"TR2_VATCO_{cc_code}{timestamp}.txt"

            out_dir = self._paths.get('respuesta_txt')
            out_dir.mkdir(parents=True, exist_ok=True)

            out_path = out_dir / file_name
            with out_path.open('w', encoding='utf-8') as f:
                for _id in sorted(set(ids)):
                    f.write(f"{_id.strip()},{estado}\n")

            return out_path
        except Exception:
            # No levantes; deja que XmlProcessor registre la excepción
            return None