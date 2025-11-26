"""
Unit of Work pattern para gestión de transacciones y repositorios.

El Unit of Work coordina el trabajo de múltiples repositorios,
asegurando que todos compartan la misma conexión y transacción.
"""
from typing import Optional
import logging

from .connection import IDatabaseConnection
from ..repositories.ciudad_repository import CiudadRepository
from ..repositories.cliente_repository import ClienteRepository
from ..repositories.punto_repository import PuntoRepository
from ..repositories.sucursal_repository import SucursalRepository
from ..repositories.servicio_repository import ServicioRepository

logger = logging.getLogger(__name__)

class UnitOfWork:
    """
    Unit of Work que gestiona repositorios y transacciones.
    
    Todos los repositorios comparten la misma conexión a la base de datos,
    permitiendo coordinar transacciones entre múltiples operaciones.
    
    Usage:
        # Opción 1: UoW maneja la conexión completa
        with UnitOfWork(connection) as uow:
            ciudad = uow.ciudades.obtener_por_codigo("01")
            punto = uow.puntos.obtener_por_codigo(codigo_punto)
            # Commit automático si no hay errores
            # Rollback automático si hay excepción
            # Conexión cerrada automáticamente
        
        # Opción 2: Conexión externa (no cerrar al salir)
        conn = SqlServerConnection(config)
        conn.connect()
        with UnitOfWork(conn, close_on_exit=False) as uow:
            # ... trabajo ...
            pass
        # conn sigue abierta
        conn.close()
    """
    
    def __init__(self,
    connection: IDatabaseConnection,
    close_on_exit: bool = True,
    auto_transaction: bool = True):
        """
        Inicializa el Unit of Work con una conexión.
        
        Args:
            connection: Conexión a la base de datos
            close_on_exit: Si True, cierra la conexión al salir del contexto
            auto_transaction: Si True, inicia transacción automáticamente al entrar
        """
        self._connection = connection
        self._close_on_exite = close_on_exit,
        self._auto_transaction = auto_transaction
        self._opened_connection = False
        
        # Lazy initialization de repositorios
        self._ciudades: Optional[CiudadRepository] = None
        self._clientes: Optional[ClienteRepository] = None
        self._puntos: Optional[PuntoRepository] = None
        self._sucursales: Optional[SucursalRepository] = None
        self._servicios: Optional[ServicioRepository] = None
    
    @property
    def ciudades(self) -> CiudadRepository:
        """Repositorio de ciudades"""
        if self._ciudades is None:
            self._ciudades = CiudadRepository(self._connection)
        return self._ciudades
    
    @property
    def clientes(self) -> ClienteRepository:
        """Repositorio de clientes"""
        if self._clientes is None:
            self._clientes = ClienteRepository(self._connection)
        return self._clientes
    
    @property
    def puntos(self) -> PuntoRepository:
        """Repositorio de puntos"""
        if self._puntos is None:
            self._puntos = PuntoRepository(
                self._connection,
                ciudad_repo=self.ciudades,
                sucursal_repo=self.sucursales,
                cliente_repo=self.clientes
            )
        return self._puntos
    
    @property
    def sucursales(self) -> SucursalRepository:
        """Repositorio de sucursales"""
        if self._sucursales is None:
            self._sucursales = SucursalRepository(
                self._connection,
                ciudad_repo=self.ciudades
            )
        return self._sucursales
    
    @property
    def servicios(self) -> ServicioRepository:
        """Repositorio de servicios, categorías y tipos de valor"""
        if self._servicios is None:
            self._servicios = ServicioRepository(self._connection)
        return self._servicios
    
    def commit(self) -> None:
        """Confirma los cambios (commit)"""
        self._connection.commit()
        logger.debug("UnitOfWork: Cambios confirmados (commit)")
    
    def rollback(self) -> None:
        """Revierte los cambios (rollback)"""
        self._connection.rollback()
        logger.debug("UnitOfWork: Cambios revertidos (rollback)")
    
    def __enter__(self):
        """Context manager entry"""
        # Abrir conexión si no está abierta
        self._opened_connection = False
        if not self._connection.is_connected():
            self._connection.connect()
            self._opened_connection = True
            logger.debug("UnitOfWork: Conexión abierta")
        
        # Iniciar transacción si está configurado
        if self._auto_transaction:
            self._connection.begin_transaction()
            logger.debug("UnitOfWork: Transacción iniciada")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        try:
            if exc_type is not None:
                # Hubo una excepción, hacer rollback
                self.rollback()
                logger.error(f"UnitOfWork: Error detectado, rollback ejecutado: {exc_val}")
            else:
                # No hubo excepciones, hacer commit
                self.commit()
                logger.debug("UnitOfWork: Commit ejecutado exitosamente")
        except Exception as e:
            logger.error(f"UnitOfWork: Error durante commit/rollback: {e}", exc_info=True)
            # Intentar rollback como último recurso
            try:
                self.rollback()
            except Exception:
                pass
        finally:
            # Solo cerrar si:
            # 1. close_on_exit es True Y
            # 2. Nosotros abrimos la conexión
            if self._close_on_exit and self._opened_connection:
                self._connection.close()
                logger.debug("UnitOfWork: Conexión cerrada")