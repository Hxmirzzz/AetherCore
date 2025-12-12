from typing import Dict
from src.infrastructure.database.connection_manager import ConnectionManager

class ClienteRepository:
    def __init__(self, connection: ConnectionManager):
        self._conn = connection

    def obtener_todos(self) -> Dict[str, Dict[str, str]]:
        sql = """
        SELECT cod_cliente, cliente
        FROM adm_clientes
        """
        
        rows = self._conn.execute_query(sql)

        return {
            str(r[0]).strip(): {
                "cliente": (r[1] or "").strip()
            }
            for r in (rows or [])
        }