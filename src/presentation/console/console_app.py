"""
Console Runner para AetherCore (XML/TXT) - MODO MANUAL CON PRE-VALIDACIÓN.

Uso:
    python -m src.presentation.console.console_app --watch
    python -m src.presentation.console.console_app --watch --only xml
"""
from __future__ import annotations
import argparse
import logging
import time
import requests
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.config.settings import get_config
from src.infrastructure.config.mapeos import ClienteMapeos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("console_app")

API_URL = "http://localhost:8000"

def _convertir_codigo_punto(codigo_bd: str) -> str:
    """
    Convierte un código de punto del formato de BD al formato de cliente.
    
    Ejemplos:
        "52-SUC-0075" -> "45-0075"
        "01-SUC-1234" -> "46-1234"
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
    """Construye diccionario de puntos con códigos en formato de cliente."""
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
        conn = container.db_connection_read()

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

def _notificar_api(archivo_info: dict) -> bool:
    """
    Notifica a la API REST sobre un archivo nuevo.
    
    Args:
        archivo_info: Diccionario con info del archivo pre-validado
        
    Returns:
        True si la notificación fue exitosa
    """
    try:
        response = requests.post(
            f"{API_URL}/api/archivos/nuevo",
            json=archivo_info,
            timeout=30
        )

        if response.status_code == 200:
            logger.info("Archivo notificado exitosamente: %s", archivo_info["nombre_archivo"])
            return True
        else:
            logger.error("✗ Error notificando archivo (HTTP %d): %s", 
                        response.status_code, archivo_info["nombre_archivo"])
            return False

    except requests.exceptions.Timeout:
        logger.error("Timeout al notificar archivo a la API")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("No se pudo conectar con la API endpoint %s", API_URL)
        return False
    except Exception as e:
        logger.exception("Error notificando archivo a la API: %s", e)
        return False

def _escanear_y_prevalidar(
    container: ApplicationContainer,
    archivos_notificados: Set[str],
    tipo: str,
    carpeta: Path
) -> None:
    """
    Escanea una carpeta y pre-valida archivos nuevos.
    
    Args:
        container: Contenedor de dependencias
        archivos_notificados: Set de archivos ya notificados (para evitar duplicados)
        tipo: "XML" o "TXT"
        carpeta: Path a la carpeta de entrada
    """
    try:
        orchestrator = container.orchestrator()
        conn = container.db_connection_read()
        
        patron = "*.xml" if tipo == "XML" else "*.txt"
        archivos = sorted(list(carpeta.glob(patron)))
        
        for archivo in archivos:
            archivo_key = f"{tipo}:{archivo.name}"

            if archivo_key in archivos_notificados:
                continue
            
            logger.info("Nuevo archivo detectado: %s", archivo.name)

            resultado = orchestrator._prevalidate_file(archivo, tipo, conn)

            archivo_info = {
                "archivo_id": resultado["archivo_id"],
                "nombre_archivo": archivo.name,
                "tipo": tipo,
                "num_registros": resultado["num_registros"],
                "errores": resultado["errores"],
                "preview": resultado["preview"],
                "ruta_interna": str(archivo.absolute()),
                "fecha_deteccion": datetime.now().isoformat()
            }

            if _notificar_api(archivo_info):
                archivos_notificados.add(archivo_key)
                logger.info("Archivo en espera de aprobación: %s", archivo.name)
                time.sleep(0.5)
            else:
                logger.info("✗ Error notificando archivo: %s", archivo.name)
                time.sleep(1)
        
    except Exception as e:
        logger.exception("Error escaneando y pre-validando archivos: %s", e)

def run_watch_manual(
    container: ApplicationContainer,
    puntos_info: Dict[str, Dict[str, Any]],
    only: str = None
):
    """
    Escanea carpetas periódicamente y pre-valida archivos nuevos.
    
    Args:
        container: Contenedor de dependencias
        puntos_info: Diccionario de puntos (no se usa en pre-validación)
        only: Filtro opcional ("xml" o "txt")
    """
    config = get_config()
    archivos_notificados: Set[str] = set()
    
    logger.info("=" * 70)
    logger.info("🔄 MODO MANUAL CON PRE-VALIDACIÓN ACTIVADO")
    logger.info("=" * 70)
    logger.info("📡 API REST: %s", API_URL)
    logger.info("⏱️  Intervalo de escaneo: 10 segundos")
    
    if only:
        logger.info("🔍 Procesando solo: %s", only.upper())
    
    try:
        while True:
            logger.debug("🔍 Escaneando carpetas...")
            
            # Escanear XML
            if only is None or only == "xml":
                carpeta_xml = config.paths.carpeta_entrada_xml
                _escanear_y_prevalidar(
                    container, 
                    archivos_notificados, 
                    "XML", 
                    carpeta_xml
                )
            
            # Escanear TXT
            if only is None or only == "txt":
                carpeta_txt = config.paths.carpeta_entrada_txt
                _escanear_y_prevalidar(
                    container, 
                    archivos_notificados, 
                    "TXT", 
                    carpeta_txt
                )
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("⏹️  Monitoreo detenido por el usuario")
        logger.info("=" * 70)

def main():
    """
    NUEVO USO - Solo modo --watch:
    
    python -m src.presentation.console.console_app --watch
    python -m src.presentation.console.console_app --watch --only xml
    python -m src.presentation.console.console_app --watch --only txt
    
    NOTA: El modo --once fue REMOVIDO porque ya no tiene sentido
          en un flujo manual con aprobación de usuario.
    """
    parser = argparse.ArgumentParser(description="AetherCore Runner")
    parser.add_argument("--watch", action="store_true", required=True)
    parser.add_argument("--only", choices=["xml", "txt"])
    parser.add_argument("--api-url", type=str, default="http://localhost:8000")

    parser.add_argument("--in-xml", type=str)
    parser.add_argument("--out-xml", type=str)
    parser.add_argument("--in-txt", type=str)
    parser.add_argument("--out-txt", type=str)
    
    args = parser.parse_args()

    global API_URL
    API_URL = args.api_url

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

    try:
        run_watch_manual(container, puntos_info, only=args.only)
    finally:
        try:
            container.close_all_connections()
            logger.info("Conexiones cerradas correctamente")
        except Exception:
            logger.exception("Error cerrando conexión")

if __name__ == "__main__":
    main()