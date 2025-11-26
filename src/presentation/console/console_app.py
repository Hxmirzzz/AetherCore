"""
Console Runner para AetherCore (XML).

- Lee configuración desde get_config() (tu .env/.yaml ya gestionado por settings.py).
- Resuelve dependencias con ApplicationContainer.
- Ejecuta en modo:
    --once  : procesa todos los XML pendientes en la carpeta de entrada.
    --watch : observa la carpeta y procesa los XML nuevos.

NOTA: No modifica repos ya existentes. Para construir `puntos_info`:
        1) Intenta usar un método del PuntoRepository si existe (p.ej. `obtener_diccionario_info()`).
        2) Si no existe, hace una consulta DIRECTA vía conexión (sin alterar tus repos) para
            armar un dict mínimo con las claves que requiere xml_mappers.py:
            - nombre_punto
            - nombre_cliente
            - ciudad
"""
from __future__ import annotations
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.config.settings import get_config
from src.infrastructure.config.mapeos import ClienteMapeos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("console_app")

def _convertir_codigo_punto(codigo_bd: str) -> str:
    """
    Convierte un código de punto del formato de BD al formato de cliente.
    
    Ejemplos de conversión:
        "52-SUC-0075" -> "45-0075"  (donde 52 es CC Code de cliente 45)
        "52-0075"     -> "45-0075"
        "01-SUC-1234" -> "46-1234"  (donde 01 es CC Code de cliente 46)
        "45-0075"     -> "45-0075"  (ya está en formato correcto)
    
    Args:
        codigo_bd: Código como viene de la base de datos
        
    Returns:
        Código en formato "CLIENTE-NUMERO"
    """
    if not codigo_bd or not isinstance(codigo_bd, str):
        return ""
    
    cc_to_cliente = {v: k for k, v in ClienteMapeos.CLIENTE_TO_CC.items()}
    codigo_normalizado = codigo_bd.replace("-SUC-", "-")
    partes = codigo_normalizado.split('-', 1)
    
    if len(partes) == 2:
        prefijo = partes[0]
        numero = partes[1]
        
        if prefijo in cc_to_cliente:
            codigo_cliente = cc_to_cliente[prefijo]
            codigo_convertido = f"{codigo_cliente}-{numero}"
            logger.debug(
                "Código convertido: '%s' -> '%s' (CC %s -> Cliente %s)",
                codigo_bd, codigo_convertido, prefijo, codigo_cliente
            )
            return codigo_convertido
        
        if prefijo in ClienteMapeos.CLIENTE_TO_CC:
            logger.debug("Código '%s' ya está en formato de cliente", codigo_bd)
            return codigo_normalizado
        
    logger.debug("No se pudo convertir código '%s', usando normalizado '%s'", codigo_bd, codigo_normalizado)
    return codigo_normalizado

def _build_puntos_info(container: ApplicationContainer) -> Dict[str, Dict[str, Any]]:
    """
    Construye diccionario de puntos con códigos en formato de cliente.
    
    El diccionario resultante tendrá:
    - Claves: códigos de punto en formato "CLIENTE-NUMERO" (ej: "45-0075")
    - Valores: dict con 'nombre_punto', 'nombre_cliente', 'ciudad'
    
    IMPORTANTE: Convierte automáticamente códigos de BD (con CC Code)
                al formato de cliente que espera el procesador XML.
    """
    try:
        puntos_repo = container.punto_repository()

        for candidate in ("obtener_diccionario_info", "obtener_todos_como_diccionario", "get_puntos_info_dict"):
            if hasattr(puntos_repo, candidate) and callable(getattr(puntos_repo, candidate)):
                logger.info("Usando PuntoRepository.%s() para construir puntos_info", candidate)
                raw_data = getattr(puntos_repo, candidate)()
                converted_data = {}
                for codigo_bd, info in raw_data.items():
                    codigo_convertido = _convertir_codigo_punto(str(codigo_bd))
                    converted_data[codigo_convertido] = info

                logger.info("Puntos cargados y convertidos: %d", len(converted_data))
                return converted_data

        logger.info("PuntoRepository no expone método dict; usando consulta directa (fallback).")
        conn = container.db_connection()

        query = """
            SELECT
                p.cod_punto        AS codigo_punto,
                p.nom_punto        AS nombre_punto,
                c.cliente          AS nombre_cliente,
                ciu.ciudad         AS ciudad
            FROM adm_puntos AS p
            LEFT JOIN adm_clientes AS c ON c.cod_cliente = p.cod_cliente
            LEFT JOIN adm_ciudades AS ciu ON ciu.cod_ciudad = p.cod_ciudad
        """
        rows = conn.execute_query(query, [])
        data: Dict[str, Dict[str, Any]] = {}
        codigos_convertidos = 0
        
        for r in rows or []:
            codigo_bd = str(r[0] or "").strip()
            if not codigo_bd:
                continue
            
            codigo_convertido = _convertir_codigo_punto(codigo_bd)
            if codigo_bd != codigo_convertido:
                codigos_convertidos += 1
            data[codigo_convertido] = {
                "nombre_punto": r[1] or "",
                "nombre_cliente": r[2] or "",
                "ciudad": r[3] or "",
            }
            
            if codigo_bd != codigo_convertido:
                data[codigo_bd] = data[codigo_convertido]
                
        logger.info(
            "Puntos cargados: %d únicos, %d convertidos (CC Code -> Cliente)",
            len({_convertir_codigo_punto(k) for k in data.keys()}),
            codigos_convertidos
        )
        logger.debug("Ejemplos de claves: %s", list(data.keys())[:5])
        
        return data

    except Exception:
        logger.exception("Error construyendo puntos_info")
        return {}

def main():
    """
    Procesar todo una vez:
    python -m src.presentation.console.console_app --once

    Watcher de todo:
    python -m src.presentation.console.console_app --watch

    Solo XML:
    --once --only xml ó --watch --only xml

    Solo TXT:
    --once --only txt ó --watch --only txt
    """
    parser = argparse.ArgumentParser(description="AetherCore Runner (auto XML/TXT)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Procesa TODO una sola vez (XML, TXT, etc.)")
    mode.add_argument("--watch", action="store_true", help="Observa TODAS las carpetas y procesa nuevos archivos")

    # Filtro opcional por tipo
    parser.add_argument("--only", choices=["xml", "txt"], help="Procesa solo un tipo (xml|txt)")

    # Overrides opcionales
    parser.add_argument("--in-xml", type=str, help="Override carpeta entrada XML")
    parser.add_argument("--out-xml", type=str, help="Override carpeta salida XML")
    parser.add_argument("--in-txt", type=str, help="Override carpeta entrada TXT")
    parser.add_argument("--out-txt", type=str, help="Override carpeta salida TXT")

    args = parser.parse_args()

    config = get_config()
    container = ApplicationContainer()

    # Overrides
    if args.in_xml:
        config.paths.carpeta_entrada_xml = Path(args.in_xml)
    if args.out_xml:
        config.paths.carpeta_salida_xml = Path(args.out_xml)
    if args.in_txt:
        config.paths.carpeta_entrada_txt = Path(args.in_txt)
    if args.out_txt:
        config.paths.carpeta_salida_txt = Path(args.out_txt)

    puntos_info = _build_puntos_info(container)
    
    logger.info("=== DEBUG puntos_info ===")
    logger.info("Total de puntos cargados: %d", len(puntos_info))
    if puntos_info:
        logger.info("Primeras 5 claves: %s", list(puntos_info.keys())[:5])
    logger.info("========================")
    
    conn = container.db_connection()
    orchestrator = container.xml_orchestrator()

    try:
        if args.once:
            logger.info("Ejecutando en modo --once (auto: todos los tipos)")
            orchestrator.run_once_all(puntos_info, conn, only=args.only)
        else:
            logger.info("Ejecutando en modo --watch (auto: todos los tipos) — Ctrl+C para salir")
            orchestrator.run_watch_all(puntos_info, conn, only=args.only)
    finally:
        try:
            conn.close()
        except Exception:
            logger.exception("Error cerrando conexión")

if __name__ == "__main__":
    main()