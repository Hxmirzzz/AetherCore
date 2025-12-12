from typing import Dict
from src.infrastructure.database.connection_manager import ConnectionManager

class CiudadRepository:
    def __init__(self, connection: ConnectionManager):
        self._conn = connection

    def obtener_todas(self) -> Dict[str, str]:
        query = """
            SELECT cod_ciudad, ciudad
            FROM adm_ciudades
        """
        rows = self._conn.execute_query(query, [])
        return {
            str(r[0]).strip(): (r[1] or "").strip()
            for r in (rows or [])
        }