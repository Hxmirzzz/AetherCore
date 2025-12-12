"""
Repositorio de Servicios/Catálogos (Servicio, Categoría, TipoValor).
Implementa IServicioRepository (según tus contratos en domain.repositories.interfaces).
"""
from __future__ import annotations
from typing import Dict, Optional, Any
import logging

from src.infrastructure.database.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

class ServicioRepository:
    def __init__(self, connection: ConnectionManager):
        self._conn = connection

    # ---- Servicios ----
    def obtener_servicio_por_codigo(self, orden_servicio: str) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT s.orden_servicio, s.numero_pedido AS numero_pedido, s.cod_concepto
                FROM cgs_servicios AS s
                WHERE s.orden_servicio = ?
            """
            rows = self._conn.execute_query(query, [orden_servicio])
            if not rows:
                return None
            r = rows[0]
            return {
                "orden_servicio": str(r[0]),
                "numero_pedido": r[1] or "",
                "cod_concepto": str(r[2]) if r[2] is not None else "",
            }
        except Exception:
            logger.exception("Error en ServicioRepository.obtener_servicio_por_codigo(%s)", orden_servicio)
            return None

    def obtener_servicios(self) -> Dict[str, Dict[str, Any]]:
        data: Dict[str, Dict[str, Any]] = {}
        try:
            query = """
                SELECT s.orden_servicio, s.numero_pedido AS numero_pedido, s.cod_concepto
                FROM cgs_servicios AS s
            """
            rows = self._conn.execute_query(query, [])
            for r in rows or []:
                codigo = str(r[0])
                data[codigo] = {
                    "orden_servicio": codigo,
                    "numero_pedido": r[1] or "",
                    "cod_concepto": str(r[2]) if r[2] is not None else "",
                }
        except Exception:
            logger.exception("Error en ServicioRepository.obtener_servicios()")
        return data

    # ---- Categorías ----
    def obtener_categoria_por_codigo(self, cod_categoria: str) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT c.cod_concepto, c.nombre_concepto
                FROM adm_conceptos AS c
                WHERE c.cod_concepto = ?
            """
            rows = self._conn.execute_query(query, [cod_categoria])
            if not rows:
                return None
            r = rows[0]
            return {
                "cod_concepto": str(r[0]),
                "nombre_concepto": r[1] or "",
            }
        except Exception:
            logger.exception("Error en ServicioRepository.obtener_categoria_por_codigo(%s)", cod_categoria)
            return None

    def obtener_categorias(self) -> Dict[str, Dict[str, Any]]:
        data: Dict[str, Dict[str, Any]] = {}
        try:
            query = """
                SELECT c.cod_concepto, c.nombre_concepto
                FROM adm_conceptos AS c
            """
            rows = self._conn.execute_query(query, [])
            for r in rows or []:
                codigo = str(r[0])
                data[codigo] = {
                    "cod_concepto": codigo,
                    "nombre_concepto": r[1] or "",
                }
        except Exception:
            logger.exception("Error en ServicioRepository.obtener_categorias()")
        return data

    # ---- Tipos de valor (opcional, si existe tabla) ----
    def obtener_tipos_valor(self) -> Dict[str, Dict[str, Any]]:
        """
        Si manejas 'tipo de valor' (billete/moneda/mixto) en tabla, ajusta nombres y SELECT.
        Si no existe tabla, puedes dejar este método como passthrough de enums/mapeos.
        """
        data: Dict[str, Dict[str, Any]] = {}
        try:
            query = """
                SELECT tv.cod_tipo_valor, tv.tipo_valor
                FROM adm_tipos_valor AS tv
            """
            rows = self._conn.execute_query(query, [])
            for r in rows or []:
                codigo = str(r[0])
                data[codigo] = {
                    "cod_tipo_valor": codigo,
                    "tipo_valor": r[1] or "",
                }
        except Exception:
            # Si no existe la tabla, no queremos romper el flujo: log y devolver vacío.
            logger.warning("Tabla adm_tipos_valor no disponible o error consultando tipos de valor.")
        return data