"""
Gestión central de rutas para XML/TXT (solo path building).
Mantiene nombres y convenciones iguales a Config.
"""
from __future__ import annotations
from pathlib import Path
from src.infrastructure.config.settings import get_config

Config = get_config()

class PathManager:
    # --- XML ---
    def input_xml_dir(self) -> Path:
        return Path(Config.paths.carpeta_entrada_xml)

    def output_xml_dir(self) -> Path:
        return Path(Config.paths.carpeta_salida_xml)

    def errores_xml_dir(self) -> Path:
        return Path(Config.paths.carpeta_errores_xml)

    def gestionados_xml_dir(self) -> Path:
        return Path(Config.paths.carpeta_gestionados_xml)

    def build_output_excel_path(self, ruta_xml: Path) -> Path:
        name_wo_ext = ruta_xml.name[:-4] if ruta_xml.name.lower().endswith(".xml") else ruta_xml.stem
        return self.output_xml_dir() / f"{name_wo_ext}.xlsx"

    # --- TXT (por si luego lo usamos) ---
    def input_txt_dir(self) -> Path:
        return Config.paths.carpeta_entrada_txt
    def output_txt_dir(self) -> Path:
        return Config.paths.carpeta_salida_txt
    def respuestas_txt_dir(self) -> Path:
        return Config.paths.carpeta_respuesta_txt
    def gestionados_txt_dir(self) -> Path:
        return Config.paths.carpeta_gestionados_txt
    def errores_txt_dir(self) -> Path:
        return (Config.paths.carpeta_errores_txt)