from typing import Dict
from src.infrastructure.database.connection_manager import ConnectionManager

class SucursalRepository:
    def __init__(self, connection: ConnectionManager):
        self._conn = connection

    def obtener_todas(self) -> Dict[str, Dict[str, str]]:
        query = """
            SELECT cod_suc, sucursal
            FROM adm_sucursales
        """
        rows = self._conn.execute_query(query, [])
        return {
            str(r[0]).strip(): {
                "sucursal": (r[1] or "").strip()
            }
            for r in (rows or [])
        }