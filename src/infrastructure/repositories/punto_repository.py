from typing import Dict, List
from src.infrastructure.database.connection_manager import ConnectionManager
from src.infrastructure.config.mapeos import ClienteMapeos

class PuntoRepository:
    def __init__(self, connection: ConnectionManager):
        self._conn = connection

    def obtener_todo_compuesto(self) -> List[dict]:
        clientes_permitidos = ClienteMapeos.get_clientes_permitidos()
        if not clientes_permitidos:
            return []
        placeholders = ','.join(['?'] * len(clientes_permitidos))

        query = f"""
            SELECT  p.cod_punto,
                    p.nom_punto,
                    p.cod_cliente,
                    c.cliente,
                    p.cod_suc,
                    s.sucursal,
                    ci.cod_ciudad,
                    ci.ciudad
            FROM adm_puntos p
            LEFT JOIN adm_clientes  c   ON c.cod_cliente = p.cod_cliente
            LEFT JOIN adm_sucursales s  ON s.cod_suc     = p.cod_suc
            LEFT JOIN adm_ciudades  ci ON ci.cod_suc     = s.cod_suc
            WHERE p.cod_cliente IN ({placeholders})
        """
        rows = self._conn.execute_query(query, clientes_permitidos)
        return [
            {
                "cod_punto":   (str(r[0]).strip() if r[0] is not None else ""),
                "nom_punto":   (r[1] or "").strip(),
                "cod_cliente": (str(r[2]).strip() if r[2] is not None else ""),
                "cliente":     (r[3] or "").strip(),
                "cod_suc":     (str(r[4]).strip() if r[4] is not None else ""),
                "sucursal":    (r[5] or "").strip(),
                "cod_ciudad":  (str(r[6]).strip() if r[6] is not None else ""),
                "ciudad":      (r[7] or "").strip(),
            }
            for r in (rows or [])
        ]

    def mapas_para_mappers(self) -> (Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]):
        """
        Retorna (DIC_PUNTOS_CLIENTES, DIC_PUNTOS_SUCURSALES) indexados por cod_punto (string).
        """
        rows = self.obtener_todo_compuesto()
        dic_clientes: Dict[str, Dict[str, str]] = {}
        dic_sucursales: Dict[str, Dict[str, str]] = {}

        for r in rows:
            clave = r["cod_punto"] or ""
            # Si tus TXT traen "47-0033" y quieres indexar por "0033", normaliza aquí:
            # from src.domain.value_objects.codigo_punto import CodigoPunto
            # clave = CodigoPunto.from_raw(clave).parte_numerica

            dic_clientes[clave] = {
                "cliente": r.get("cliente", "") or "",
                "cod_cliente": r.get("cod_cliente", "") or "",
            }
            dic_sucursales[clave] = {
                "sucursal":   r.get("sucursal", "") or "",
                "cod_suc":    r.get("cod_suc", "") or "",
                "cod_ciudad": r.get("cod_ciudad", "") or "",
                "ciudad":     r.get("ciudad", "") or "",
            }

        return dic_clientes, dic_sucursales