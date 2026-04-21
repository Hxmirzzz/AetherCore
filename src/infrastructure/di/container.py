"""
Contenedor de Dependencias (DI) sin librerías externas.

Objetivos:
- Centralizar la creación de objetos con su configuración.
- Mantener bajo acoplamiento (DIP) y facilitar pruebas (mocks/fakes).
"""
from src.infrastructure.config.settings import get_config
from src.infrastructure.file_system.path_manager import PathManager
from src.infrastructure.file_system.file_watcher import DirectoryWatcher

# XML processors
from src.application.processors.xml.xml_file_reader import XmlFileReader
from src.application.processors.xml.xml_data_transformer import XmlDataTransformer
from src.application.processors.xml.xml_processor import XMLProcessor

# TXT processors
from src.application.processors.txt.txt_file_reader import TxtFileReader
from src.application.processors.txt.txt_data_transformer import TxtDataTransformer
from src.application.processors.txt.txt_processor import TXTProcessor

from src.infrastructure.api.internal_api_client import InternalApiClient
from src.infrastructure.api.external_api_client import ExternalApiClient
from src.application.orchestrators.processing_orchestrator import ProcessingOrchestrator


class ApplicationContainer:
    """
    DI Container.

    Uso básico:
        container = ApplicationContainer()
        xml_proc = container.xml_processor()
        ok = xml_proc.procesar_archivo_xml(...)
    """

    # ====== SINGLETON-LIKE ======
    _config = None

    # ---------- Config ----------
    def config(self):
        """Singleton soft de Config (Pydantic)."""
        if self._config is None:
            self._config = get_config()
        return self._config

    def xml_processor(self) -> XMLProcessor:
        """Factory principal para el caso de uso XML → Excel + Respuesta."""
        return XMLProcessor(
            reader=XmlFileReader(),
            transformer=XmlDataTransformer(),
            external_api=self.external_api_client()
        )
    
    def txt_processor(self) -> TXTProcessor:
        return TXTProcessor(
            reader=TxtFileReader(),
            transformer=TxtDataTransformer(),
            paths=self.path_manager(),
            external_api=self.external_api_client()
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

    def internal_api_client(self) -> InternalApiClient:
        return InternalApiClient(self.config())
    
    def external_api_client(self) -> ExternalApiClient:
        return ExternalApiClient(self.config())

    # ====== ORCHESTRATORS ======
    def orchestrator(self) -> ProcessingOrchestrator:
        return ProcessingOrchestrator(
            xml_processor=self.xml_processor(),
            path_manager=self.path_manager(),
            watcher_factory=self.watcher_factory(),
            internal_api_client=self.internal_api_client(),
            external_api_client=self.external_api_client(),
            debounce_ms=800,
            txt_processor=self.txt_processor()
        )