"""
Contenedor de Dependencias (DI) sin librerías externas.

Objetivos:
- Centralizar la creación de objetos con su configuración.
- Mantener bajo acoplamiento (DIP) y facilitar pruebas (mocks/fakes).

Este contenedor usa inicialización perezosa y devuelve SIEMPRE nuevas instancias
para repos/servicios (Factory), excepto para Config y Conexión DB que son Singleton “soft”.
"""
from __future__ import annotations
from typing import Optional

# Config y DB
from src.infrastructure.config.settings import get_config
from src.infrastructure.database.connection_manager import ConnectionManager
from src.infrastructure.database.unit_of_work import UnitOfWork

# Repos existentes (otros se agregarán cuando estén listos)
from src.infrastructure.repositories.ciudad_repository import CiudadRepository
from src.infrastructure.repositories.cliente_repository import ClienteRepository
from src.infrastructure.repositories.punto_repository import PuntoRepository
from src.infrastructure.repositories.sucursal_repository import SucursalRepository
from src.infrastructure.repositories.servicio_repository import ServicioRepository
from src.infrastructure.repositories.service_writer_repository import ServiceWriterRepository

# Servicios de aplicación
from src.application.services.data_mapper_service import DataMapperService
from src.application.services.insertion_service import InsertionService

# Excel styler
from src.infrastructure.excel.excel_styler import ExcelStyler

# XML processors
from src.application.processors.xml.xml_file_reader import XmlFileReader
from src.application.processors.xml.xml_data_transformer import XmlDataTransformer
from src.application.processors.xml.xml_processor import XMLProcessor

# TXT processors
from src.application.processors.txt.txt_file_reader import TxtFileReader
from src.application.processors.txt.txt_data_transformer import TxtDataTransformer
from src.application.processors.txt.txt_processor import TXTProcessor

from src.infrastructure.file_system.path_manager import PathManager
from src.infrastructure.file_system.file_watcher import DirectoryWatcher
from src.application.orchestrators.processing_orchestrator import ProcessingOrchestrator


class ApplicationContainer:
    """
    DI Container minimalista.

    Uso básico:
        container = ApplicationContainer()
        xml_proc = container.xml_processor()
        ok = xml_proc.procesar_archivo_xml(...)

    Nota: Para pruebas puedes inyectar dependencias alternas reemplazando los métodos factory.
    """

    # ====== SINGLETON-LIKE ======
    _config = None
    _conn_manager: Optional[ConnectionManager] = None

    # ---------- Config ----------
    def config(self):
        """Singleton soft de Config (Pydantic)."""
        if self._config is None:
            self._config = get_config()
        return self._config

    # ---------- DB Connection ----------
    def connection_manager(self) -> ConnectionManager:
        """
        Singleton soft de ConnectionManager.
        Maneja las DOS conexiones: prod (lectura) y test (escritura).
        """
        if self._conn_manager is None:
            self._conn_manager = ConnectionManager(self.config())
        return self._conn_manager

    # ---------- Conexiones individuales ----------
    def db_connection_read(self):
        """Conexión de LECTURA (prod)"""
        return self.connection_manager().get_read_connection()

    def db_connection_write(self):
        """Conexión de ESCRITURA (test)"""
        return self.connection_manager().get_write_connection()

    # ========== REPOSITORIOS ==========
    def ciudad_repository(self) -> CiudadRepository:
        """Repositorio de ciudades (usa conexión de LECTURA)"""
        return CiudadRepository(self.db_connection_read())

    def cliente_repository(self) -> ClienteRepository:
        """Repositorio de clientes (usa conexión de LECTURA)"""
        return ClienteRepository(self.db_connection_read())

    def sucursal_repository(self) -> SucursalRepository:
        """Repositorio de sucursales (usa conexión de LECTURA)"""
        return SucursalRepository(self.db_connection_read())

    def punto_repository(self) -> PuntoRepository:
        """Repositorio de puntos (usa conexión de LECTURA)"""
        return PuntoRepository(self.db_connection_read())

    def servicio_repository(self) -> ServicioRepository:
        """Repositorio de servicios (usa conexión de LECTURA)"""
        return ServicioRepository(self.db_connection_read())

    def service_writer_repository(self) -> ServiceWriterRepository:
        """Repositorio de escritura (usa conexión de ESCRITURA)"""
        return ServiceWriterRepository(self.db_connection_write())

    # ========== SERVICIOS DE APLICACIÓN ==========
    def data_mapper_service(self) -> DataMapperService:
        """Servicio de mapeo de datos archivo -> DTOs."""
        return DataMapperService(self.connection_manager())

    def insertion_service(self) -> InsertionService:
        """Servicio de inserción de servicios en BD."""
        return InsertionService(
            mapper_service=self.data_mapper_service(),
            writer=self.service_writer_repository()
        )

    # Si en algún lugar quieres un UoW desde el contenedor:
    def unit_of_work(self):
        return UnitOfWork(self.db_connection_read())

    # ====== EXCEL ======
    def excel_styler(self) -> ExcelStyler:
        """Factory simple; la clase es estática pero lo exponemos para mantener patrón uniforme."""
        return ExcelStyler()

    # ====== XML PROCESSORS ======
    def xml_file_reader(self) -> XmlFileReader:
        return XmlFileReader()

    def xml_data_transformer(self) -> XmlDataTransformer:
        return XmlDataTransformer()

    def xml_processor(self) -> XMLProcessor:
        """Factory principal para el caso de uso XML → Excel + Respuesta."""
        return XMLProcessor(
            reader=self.xml_file_reader(),
            transformer=self.xml_data_transformer(),
            insertion_service=self.insertion_service()
        )
        
    # ====== TXT PROCESSORS ======
    def txt_file_reader(self) -> TxtFileReader:
        return TxtFileReader()
    def txt_data_transformer(self) -> TxtDataTransformer:
        return TxtDataTransformer()
    def txt_processor(self) -> TXTProcessor:
        return TXTProcessor(
            reader=self.txt_file_reader(),
            transformer=self.txt_data_transformer(),
            paths=self.path_manager()
        )
        
    # ====== FILE SYSTEM ======
    def path_manager(self) -> PathManager:
        return PathManager()

    def watcher_factory(self):
        """
        Devuelve la clase DirectoryWatcher como factory para inyectarla al orquestador.
        Útil si luego quieres cambiar a watchdog u otra implementación.
        """
        return DirectoryWatcher

    # ====== ORCHESTRATORS ======
    def xml_orchestrator(self) -> ProcessingOrchestrator:
        return ProcessingOrchestrator(
            xml_processor=self.xml_processor(),
            path_manager=self.path_manager(),
            watcher_factory=self.watcher_factory(),
            debounce_ms=800,
            txt_processor=self.txt_processor(),
        )

    # ====== CLEANUP ======
    def close_all_connections(self):
        """Cierra todas las conexiones al finalizar"""
        if self._conn_manager:
            self._conn_manager.close_all()