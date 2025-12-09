"""
Gestor de conexiones múltiples a base de datos.

Proporciona acceso controlado a las dos bases de datos:
- BD de Producción (lectura): Para consultar datos de referencia
- BD de Pruebas/Local (escritura): Para ejecutar SPs de inserción
"""
from typing import Optional
import logging

from .connection import IDatabaseConnection, SqlServerConnection, ConnectionFactory
from ..config.settings import AppConfig, DatabaseConfig


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestor centralizado de conexiones múltiples.
    
    Responsabilidades:
    - Crear conexiones de lectura (BD producción)
    - Crear conexiones de escritura (BD pruebas/local)
    - Gestionar el ciclo de vida de las conexiones
    - Proveer contextos para operaciones específicas
    
    Usage:
        manager = ConnectionManager(config)
        
        # Para consultas (lectura)
        with manager.get_read_connection() as conn:
            ciudades = obtener_ciudades(conn)
        
        # Para inserción (escritura)
        with manager.get_write_connection() as conn:
            orden = insertar_servicio(conn)
    """
    
    def __init__(self, config: AppConfig):
        """
        Inicializa el gestor con la configuración de la aplicación.
        
        Args:
            config: Configuración de la aplicación
        """
        self._config = config
        self._read_connection: Optional[IDatabaseConnection] = None
        self._write_connection: Optional[IDatabaseConnection] = None
    
    # ═══════════════════════════════════════════════════════════
    # CONEXIÓN DE LECTURA (BD Producción)
    # ═══════════════════════════════════════════════════════════
    
    def get_read_connection(self) -> IDatabaseConnection:
        """
        Obtiene una conexión para LECTURA (consultas de datos de referencia).
        
        Esta conexión apunta a la BD de producción y debe usarse para:
        - Consultar ciudades, clientes, puntos, sucursales
        - Obtener datos de catálogos
        - Cualquier operación de solo lectura
        
        Returns:
            Conexión a BD de producción
            
        Example:
            with manager.get_read_connection() as conn:
                ciudades = ciudad_repo.obtener_todas()
        """
        if self._read_connection is None or not self._read_connection.is_connected():
            db_config = self._config.database_read
            self._read_connection = ConnectionFactory.create_sql_server_connection(db_config)
            logger.info(
                f"Creada conexión de LECTURA a: "
                f"{db_config.server}/{db_config.database}"
            )
        
        return self._read_connection
    
    # ═══════════════════════════════════════════════════════════
    # CONEXIÓN DE ESCRITURA (BD Pruebas/Local)
    # ═══════════════════════════════════════════════════════════
    
    def get_write_connection(self) -> IDatabaseConnection:
        """
        Obtiene una conexión para ESCRITURA (inserción de servicios).
        
        Esta conexión apunta a la BD de pruebas/local y debe usarse para:
        - Ejecutar el SP AddServiceTransaction
        - Insertar servicios y transacciones
        - Cualquier operación de escritura
        
        Returns:
            Conexión a BD de pruebas/local
            
        Example:
            with manager.get_write_connection() as conn:
                orden = service_writer.insertar_servicio(conn)
        """
        if self._write_connection is None or not self._write_connection.is_connected():
            db_config = self._config.database_write
            self._write_connection = ConnectionFactory.create_sql_server_connection(db_config)
            logger.info(
                f"Creada conexión de ESCRITURA a: "
                f"{db_config.server}/{db_config.database}"
            )
        
        return self._write_connection
    
    # ═══════════════════════════════════════════════════════════
    # GESTIÓN DE RECURSOS
    # ═══════════════════════════════════════════════════════════
    
    def close_all(self):
        """
        Cierra todas las conexiones activas.
        
        Debe llamarse al finalizar el procesamiento para liberar recursos.
        """
        if self._read_connection:
            try:
                self._read_connection.close()
                logger.info("Conexión de LECTURA cerrada")
            except Exception as e:
                logger.warning(f"Error cerrando conexión de lectura: {e}")
            finally:
                self._read_connection = None
        
        if self._write_connection:
            try:
                self._write_connection.close()
                logger.info("Conexión de ESCRITURA cerrada")
            except Exception as e:
                logger.warning(f"Error cerrando conexión de escritura: {e}")
            finally:
                self._write_connection = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cierra todas las conexiones"""
        self.close_all()
    
    def __del__(self):
        """Destructor - asegura que las conexiones se cierren"""
        self.close_all()


class DualConnectionUnitOfWork:
    """
    Unit of Work que maneja DOS conexiones:
    - Conexión de lectura (para repositorios de consulta)
    - Conexión de escritura (para inserción)
    
    Usage:
        with DualConnectionUnitOfWork(conn_manager) as uow:
            # Lectura (desde BD producción)
            ciudad = uow.ciudades.obtener_por_codigo("01")
            
            # Escritura (a BD pruebas/local)
            orden = uow.service_writer.insertar_servicio(servicio_dto)
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        Inicializa el UoW dual.
        
        Args:
            connection_manager: Gestor de conexiones
        """
        self._conn_manager = connection_manager
        
        # Lazy initialization
        from ..repositories.ciudad_repository import CiudadRepository
        from ..repositories.cliente_repository import ClienteRepository
        from ..repositories.punto_repository import PuntoRepository
        from ..repositories.sucursal_repository import SucursalRepository
        from ..repositories.servicio_repository import ServicioRepository
        from ..repositories.service_writer_repository import ServiceWriterRepository
        
        self._ciudad_repo = None
        self._cliente_repo = None
        self._punto_repo = None
        self._sucursal_repo = None
        self._servicio_repo = None
        self._service_writer = None
    
    # ═══════════════════════════════════════════════════════════
    # REPOSITORIOS DE LECTURA (BD Producción)
    # ═══════════════════════════════════════════════════════════
    
    @property
    def ciudades(self):
        """Repositorio de ciudades (lectura)"""
        if self._ciudad_repo is None:
            from ..repositories.ciudad_repository import CiudadRepository
            self._ciudad_repo = CiudadRepository(self._conn_manager.get_read_connection())
        return self._ciudad_repo
    
    @property
    def clientes(self):
        """Repositorio de clientes (lectura)"""
        if self._cliente_repo is None:
            from ..repositories.cliente_repository import ClienteRepository
            self._cliente_repo = ClienteRepository(self._conn_manager.get_read_connection())
        return self._cliente_repo
    
    @property
    def puntos(self):
        """Repositorio de puntos (lectura)"""
        if self._punto_repo is None:
            from ..repositories.punto_repository import PuntoRepository
            self._punto_repo = PuntoRepository(
                self._conn_manager.get_read_connection(),
                ciudad_repo=self.ciudades,
                sucursal_repo=self.sucursales,
                cliente_repo=self.clientes
            )
        return self._punto_repo
    
    @property
    def sucursales(self):
        """Repositorio de sucursales (lectura)"""
        if self._sucursal_repo is None:
            from ..repositories.sucursal_repository import SucursalRepository
            self._sucursal_repo = SucursalRepository(
                self._conn_manager.get_read_connection(),
                ciudad_repo=self.ciudades
            )
        return self._sucursal_repo
    
    @property
    def servicios(self):
        """Repositorio de servicios/categorías/valores (lectura)"""
        if self._servicio_repo is None:
            from ..repositories.servicio_repository import ServicioRepository
            self._servicio_repo = ServicioRepository(self._conn_manager.get_read_connection())
        return self._servicio_repo
    
    # ═══════════════════════════════════════════════════════════
    # REPOSITORIO DE ESCRITURA (BD Pruebas/Local)
    # ═══════════════════════════════════════════════════════════
    
    @property
    def service_writer(self):
        """Repositorio de escritura de servicios (escritura)"""
        if self._service_writer is None:
            from ..repositories.service_writer_repository import ServiceWriterRepository
            self._service_writer = ServiceWriterRepository(
                self._conn_manager.get_write_connection()
            )
        return self._service_writer
    
    # ═══════════════════════════════════════════════════════════
    # CONTEXT MANAGER
    # ═══════════════════════════════════════════════════════════
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # El ConnectionManager ya maneja el cierre
        pass