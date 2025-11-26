"""
Lector de archivos XML (solo parseo y extracción cruda).
No conoce de pandas ni de Excel; entrega estructuras listas para transformar.
"""
from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class XmlFileReader:
    def read(self, ruta_xml: Path) -> Dict[str, Any]:
        if not ruta_xml.exists():
            raise FileNotFoundError(f"XML no existe: {ruta_xml}")
        if ruta_xml.stat().st_size == 0:
            return {"empty": True}
        try:
            tree = ET.parse(ruta_xml)
            root = tree.getroot()
            return {"empty": False, "root": root, "name": ruta_xml.name}
        except ET.ParseError as e:
            logger.exception("Error parseando XML: %s", ruta_xml.name)
            raise e

    def find_elements(self, root: ET.Element, tag: str) -> List[ET.Element]:
        return root.findall(f'.//{tag}')