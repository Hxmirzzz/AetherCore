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
from src.infrastructure.database.connection import SqlServerConnection, IDatabaseConnection
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
    _db_conn: Optional[IDatabaseConnection] = None

    # ---------- Config ----------
    def config(self):
        """Singleton soft de Config (Pydantic)."""
        if self._config is None:
            self._config = get_config()
        return self._config

    # ---------- DB Connection ----------
    def db_connection(self) -> IDatabaseConnection:
        """
        Singleton soft de conexión a SQL Server.
        Si tu SqlServerConnection ya lee las credenciales desde Config internamente, basta instanciarlo.
        Si requiere parámetros explícitos, extrae aquí desde self.config().
        """
        if self._db_conn is None:
            self._db_conn = SqlServerConnection(self.config().database)
        return self._db_conn

    def ciudad_repository(self) -> CiudadRepository:
        return CiudadRepository(self.db_connection())

    def cliente_repository(self) -> ClienteRepository:
        return ClienteRepository(self.db_connection())

    def sucursal_repository(self) -> SucursalRepository:
        return SucursalRepository(self.db_connection())

    def punto_repository(self) -> PuntoRepository:
        return PuntoRepository(self.db_connection())

    def servicio_repository(self) -> ServicioRepository:
        return ServicioRepository(self.db_connection())

    def service_writer_repository(self) -> ServiceWriterRepository:
        """Repositorio de escritura para insertar servicios."""
        return ServiceWriterRepository(self.db_connection())

    # ========== SERVICIOS DE APLICACIÓN (NUEVO) ==========
    def data_mapper_service(self) -> DataMapperService:
        """Servicio de mapeo de datos archivo -> DTOs."""
        return DataMapperService(self.unit_of_work())

    def insertion_service(self) -> InsertionService:
        """Servicio de inserción de servicios en BD."""
        return InsertionService(
            mapper_service=self.data_mapper_service(),
            writer=self.service_writer_repository()
        )

    # Si en algún lugar quieres un UoW desde el contenedor:
    def unit_of_work(self):
        from src.infrastructure.database.unit_of_work import UnitOfWork
        return UnitOfWork(self.db_connection())

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
            insertion_service=self.insertion_service()  # 🆕 NUEVO
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
            paths=self.path_manager(),
            insertion_service=self.insertion_service()  # 🆕 NUEVO
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