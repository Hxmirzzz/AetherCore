from typing import Dict
from src.infrastructure.database.connection import IDatabaseConnection

class SucursalRepository:
    def __init__(self, connection: IDatabaseConnection):
        self._conn = connection

    def obtener_todas(self) -> Dict[str, Dict[str, str]]:
        query = """
            SELECT cod_sucursal, nombre_sucursal
            FROM adm_sucursales
        """
        rows = self._conn.execute_query(query, [])
        return {
            str(r[0]).strip(): {
                "nombre_sucursal": (r[1] or "").strip()
            }
            for r in (rows or [])
        }