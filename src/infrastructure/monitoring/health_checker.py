from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import logging

from src.infrastructure.config.settings import get_config

@dataclass
class HealthStatus:
    is_healthy: bool
    componente: str
    detalles: str
    timestamp: datetime

class HealthChecker:
    """Verifica el estado de los componentes críticos del sistema."""

    def __init__(self, conn_manager, email_notifier):
        self._conn_manager = conn_manager
        self._email = email_notifier
        self._logger = logging.getLogger(__name__)
        self._ultimo_estado = {}

    def check_database(self) -> HealthStatus:
        """Verifica el estado de la base de datos."""
        try:
            conn = self._conn_manager.get_read_connection()
            conn.execute("SELECT 1")
            return HealthStatus(
                is_healthy=True,
                componente="Database",
                detalles="Conexión exitosa",
                timestamp=datetime.now()
            )
        except Exception as e:
            status = HealthStatus(
                is_healthy=False,
                componente="Database",
                detalles=str(e),
                timestamp=datetime.now()
            )

            if self._ultimo_estado.get("Database", True):
                self._email.enviar_alerta_bd_caida()

            self._ultimo_estado["Database"] = False
            return status

    def check_folders(self) -> Dict[str, HealthStatus]:
        """Verifica el estado de las carpetas críticas."""
        config = get_config()
        
        carpetas = {
            "Entrada XML": config.paths.carpeta_entrada_xml,
            "Salida XML": config.paths.carpeta_salida_xml,
            "Entrada TXT": config.paths.carpeta_entrada_txt,
            "Salida TXT": config.paths.carpeta_salida_txt
        }
        
        resultados = {}
        for nombre, carpeta in carpetas.items():
            try:
                carpeta.mkdir(parents=True, exist_ok=True)
                test_file = carpeta / ".health_check"
                test_file.touch()
                test_file.unlink()

                resultados[nombre] = HealthStatus(
                    is_healthy=True,
                    componente=nombre,
                    detalles=f"Directorio creado/verificado: {ruta}",
                    timestamp=datetime.now()
                )
            except Exception as e:
                resultados[nombre] = HealthStatus(
                    is_healthy=False,
                    componente=nombre,
                    detalles=f"Error al crear/verificar {nombre}: {str(e)}",
                    timestamp=datetime.now()
                )
                    
        return resultados

    def check_all(self) -> Dict[str, Any]:
        """Health check completo"""
        return {
            "database": self.check_database(),
            "folders": self.check_folders(),
            "timestamp": datetime.now().isoformat()
        }