"""
Console Runner para AetherCore (XML/TXT) - MODO MANUAL CON PRE-VALIDACIÓN.

Uso normal:
    python -m src.presentation.console.console_app --watch
    python -m src.presentation.console.console_app --watch --only xml
    python -m src.presentation.console.console_app --watch --only txt

Uso de PRUEBA LOCAL (Autoprocesa sin frontend):
    python -m src.presentation.console.console_app --watch --local-test
"""
from __future__ import annotations
import argparse
import logging
import time
import requests
import os
from pathlib import Path
from typing import Dict, Any, Set
from datetime import datetime

from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.config.settings import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("console_app")

API_URL = "http://localhost:8000"

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
    carpeta: Path,
    local_test: bool = False
) -> None:
    """
    Escanea una carpeta y pre-valida archivos nuevos.
    
    Args:
        container: Contenedor de dependencias
        archivos_notificados: Set de archivos ya notificados (para evitar duplicados)
        tipo: "XML" o "TXT"
        carpeta: Path a la carpeta de entrada
        local_test: Si True, autoprocesa sin notificar a la API
    """
    try:
        orchestrator = container.orchestrator()
        patron = "*.xml" if tipo == "XML" else "*.txt"
        archivos = sorted(list(carpeta.glob(patron)))
        
        for archivo in archivos:
            archivo_key = f"{tipo}:{archivo.name}"

            if archivo_key in archivos_notificados:
                continue
            
            logger.info("Nuevo archivo detectado: %s", archivo.name)

            resultado = orchestrator._prevalidate_file(archivo, tipo)

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

            if local_test:
                logger.info("🔧 MODO PRUEBA LOCAL: Autoprocesando archivo sin notificar a API")
                exito = orchestrator.process_approved_file(resultado["archivo_id"], archivo, tipo)
                archivos_notificados.add(archivo_key)
                if exito:
                    logger.info("✅ Procesamiento y comunicación con APIs completado con éxito.")
                else:
                    logger.error("❌ Error en el procesamiento y comunicación con APIs.")
            else:
                if _notificar_api(archivo_info):
                    archivos_notificados.add(archivo_key)
                    logger.info("Archivo en espera de aprobación: %s", archivo.name)
                    time.sleep(0.5)
                else:
                    logger.error("❌ Error notificando archivo a API: %s", archivo.name)
                    time.sleep(1)
        
    except Exception as e:
        logger.exception("Error escaneando y pre-validando archivos: %s", e)

def _inicializar_direectiorios(config) -> None:
    """Crea todas las carpetas necesarias si no existen."""
    rutas_a_crear = [
        config.paths.carpeta_entrada_xml,
        config.paths.carpeta_salida_xml,
        config.paths.carpeta_gestionados_xml,
        config.paths.carpeta_errores_xml,
        config.paths.carpeta_entrada_txt,
        config.paths.carpeta_salida_txt,
        config.paths.carpeta_gestionados_txt,
        config.paths.carpeta_errores_txt,
        config.paths.carpeta_respuesta_txt
    ]
    
    logger.info("Creando carpetas necesarias...")
    for ruta in rutas_a_crear:
        if ruta:
            os.makedirs(ruta, exist_ok=True)
            logger.info("✓ Carpeta creada: %s", ruta)
    logger.info("✓ Todas las carpetas necesarias creadas")

def run_watch_manual(
    container: ApplicationContainer,
    only: str = None,
    local_test: bool = False
):
    """
    Escanea carpetas periódicamente y pre-valida archivos nuevos.
    
    Args:
        container: Contenedor de dependencias
        only: Filtro opcional ("xml" o "txt")
        local_test: Si True, procesa archivos sin notificar a API (modo prueba)
    """
    config = get_config()
    archivos_notificados: Set[str] = set()
    _inicializar_direectiorios(config)
    
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
                    carpeta_xml,
                    local_test
                )
            
            # Escanear TXT
            if only is None or only == "txt":
                carpeta_txt = config.paths.carpeta_entrada_txt
                _escanear_y_prevalidar(
                    container, 
                    archivos_notificados, 
                    "TXT", 
                    carpeta_txt,
                    local_test
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
    """
    parser = argparse.ArgumentParser(description="AetherCore Runner")
    parser.add_argument("--watch", action="store_true", required=True)
    parser.add_argument("--only", choices=["xml", "txt"])
    parser.add_argument("--api-url", type=str, default="http://localhost:8000")
    parser.add_argument("--local-test", action="store_true", help="Modo prueba: autoprocesa archivos sin notificar a API")

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
    
    run_watch_manual(container, only=args.only, local_test=args.local_test)

if __name__ == "__main__":
    main()