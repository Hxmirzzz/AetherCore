from typing import Dict

class ClienteRepository:
    def __init__(self, conn):
        self._conn = conn

    def obtener_todos(self) -> Dict[str, Dict[str, str]]:
        sql = """
        SELECT cod_cliente, cliente
        FROM adm_clientes
        """
        with self._conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return {
            str(r.cod_cliente).strip(): { "cliente": (r.cliente or "").strip() }
            for r in rows
        }