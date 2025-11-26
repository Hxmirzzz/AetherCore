"""
Abstracción de conexión a base de datos (Dependency Inversion Principle).

Define interfaces y implementaciones para conexiones de base de datos,
permitiendo cambiar de proveedor sin afectar el resto de la aplicación.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from contextlib import contextmanager
import pyodbc
import logging

from ..config.settings import DatabaseConfig


logger = logging.getLogger(__name__)


class IDatabaseConnection(ABC):
    """
    Interfaz para conexiones a base de datos.
    
    Cualquier implementación de base de datos debe implementar esta interfaz.
    """
    
    @abstractmethod
    def connect(self) -> None:
        """Establece la conexión a la base de datos"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Cierra la conexión a la base de datos"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica si la conexión está activa"""
        pass
    
    @abstractmethod
    def execute_query(
        self, 
        query: str, 
        params: Optional[List[Any]] = None
    ) -> List[Any]:
        """
        Ejecuta una query SELECT y retorna los resultados.
        
        Args:
            query: Query SQL a ejecutar (debe ser SELECT)
            params: Parámetros para la query (opcional)
            
        Returns:
            Lista de resultados (filas)
            
        Raises:
            ValueError: Si la query no es un SELECT
        """
        pass
    
    @abstractmethod
    def execute_scalar(
        self, 
        query: str, 
        params: Optional[List[Any]] = None
    ) -> Optional[Any]:
        """
        Ejecuta una query y retorna un único valor escalar.
        
        Args:
            query: Query SQL a ejecutar
            params: Parámetros para la query (opcional)
            
        Returns:
            Valor escalar o None
        """
        pass
    
    @abstractmethod
    def execute_non_query(
        self, 
        query: str, 
        params: Optional[List[Any]] = None
    ) -> int:
        """
        Ejecuta una query que no retorna resultados (INSERT, UPDATE, DELETE).
        
        Args:
            query: Query SQL a ejecutar
            params: Parámetros para la query (opcional)
            
        Returns:
            Número de filas afectadas
        """
        pass
    
    @abstractmethod
    def begin_transaction(self) -> None:
        """Inicia una transacción explícitamente"""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Confirma la transacción actual"""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Revierte la transacción actual"""
        pass
    
    @abstractmethod
    @contextmanager
    def transaction(self):
        """
        Context manager para transacciones.
        
        Usage:
            with connection.transaction():
                connection.execute_non_query(...)
                connection.execute_non_query(...)
        """
        pass


class SqlServerConnection(IDatabaseConnection):
    """Implementación de conexión para SQL Server usando pyodbc"""
    
    def __init__(self, config: DatabaseConfig):
        self._config = config
        self._connection: Optional[pyodbc.Connection] = None

    def connect(self) -> None:
        """Establece la conexión a SQL Server"""
        try:
            if self._connection is not None:
                logger.debug("Conexión ya existente, reutilizando")
                return

            logger.info("Estableciendo conexión a SQL Server...")
            self._connection = pyodbc.connect(self._config.connection_string)
            logger.info("Conexión a SQL Server establecida correctamente")

        except pyodbc.Error as e:
            logger.error(f"Error al conectar a SQL Server: {e}", exc_info=True)
            raise ConnectionError(f"No se pudo conectar a la base de datos: {e}")

    def close(self) -> None:
        """Cierra la conexión en forma idempotente"""
        try:
            if getattr(self, "_connection", None) is not None:
                try:
                    self._connection.close()
                except Exception:
                    pass
                finally:
                    self._connection = None
            logger.debug("Conexión a SQL Server cerrada correctamente")
        except Exception as e:
            logger.warning(f"Error al cerrar conexión (ignorado): {e}")

    def is_connected(self) -> bool:
        """Verifica si tenemos objeto conexión"""
        return self._connection is not None

    def _ensure_connection(self) -> None:
        """Asegura que la conexión esté establecida"""
        if not self.is_connected():
            self.connect()

    def _get_cursor(self) -> pyodbc.Cursor:
        """Devuelve un cursor nuevo"""
        self._ensure_connection()
        return self._connection.cursor()

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Any]:
        """
        Ejecuta una query SELECT y retorna los resultados.
        
        Valida que la query sea realmente un SELECT.
        """
        # Validación de tipo de query
        query_clean = query.strip().upper()
        if not query_clean.startswith('SELECT') and not query_clean.startswith('WITH'):
            raise ValueError("execute_query solo acepta queries SELECT o WITH (CTEs)")
        
        cursor = None
        try:
            cursor = self._get_cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            logger.debug(f"Query ejecutada, {len(rows)} filas retornadas")
            return rows
        except pyodbc.Error as e:
            logger.error(f"Error ejecutando query: {e}\nQuery: {query}", exc_info=True)
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def execute_scalar(self, query: str, params: Optional[List[Any]] = None) -> Optional[Any]:
        """Ejecuta una query y retorna un único valor escalar"""
        cursor = None
        try:
            cursor = self._get_cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
        except pyodbc.Error as e:
            logger.error(f"Error ejecutando scalar query: {e}\nQuery: {query}", exc_info=True)
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def execute_non_query(self, query: str, params: Optional[List[Any]] = None) -> int:
        """
        Ejecuta una query que no retorna resultados (INSERT, UPDATE, DELETE).
        
        Hace commit automáticamente.
        """
        cursor = None
        try:
            cursor = self._get_cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self._connection.commit()
            rows_affected = cursor.rowcount
            logger.debug(f"Non-query ejecutada, {rows_affected} filas afectadas")
            return rows_affected
        except pyodbc.Error as e:
            logger.error(f"Error ejecutando non-query: {e}\nQuery: {query}", exc_info=True)
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def begin_transaction(self) -> None:
        """
        Inicia una transacción explícitamente.
        
        pyodbc está en modo autocommit por defecto, así que no necesitamos BEGIN TRANSACTION.
        """
        self._ensure_connection()
        # pyodbc maneja transacciones automáticamente
        logger.debug("Transacción iniciada (implícita en pyodbc)")

    def commit(self) -> None:
        """Confirma la transacción actual"""
        self._ensure_connection()
        try:
            self._connection.commit()
            logger.debug("Transacción confirmada (commit)")
        except pyodbc.Error as e:
            logger.error(f"Error al hacer commit: {e}", exc_info=True)
            raise

    def rollback(self) -> None:
        """Revierte la transacción actual"""
        self._ensure_connection()
        try:
            self._connection.rollback()
            logger.debug("Transacción revertida (rollback)")
        except pyodbc.Error as e:
            logger.error(f"Error al hacer rollback: {e}", exc_info=True)
            raise

    @contextmanager
    def transaction(self):
        """Context manager para transacciones"""
        self._ensure_connection()
        try:
            yield self
            self._connection.commit()
            logger.debug("Transacción confirmada (commit)")
        except Exception as e:
            try:
                self._connection.rollback()
            except Exception:
                pass
            logger.error(f"Transacción revertida (rollback) por error: {e}", exc_info=True)
            raise

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __del__(self):
        """Destructor para asegurar cierre de conexión"""
        self.close()


class ConnectionFactory:
    """Factory para crear conexiones a base de datos"""
    
    @staticmethod
    def create_sql_server_connection(config: DatabaseConfig) -> IDatabaseConnection:
        """Crea una conexión a SQL Server"""
        return SqlServerConnection(config)
    
    @staticmethod
    def create_connection(db_type: str, config: DatabaseConfig) -> IDatabaseConnection:
        """
        Crea una conexión basada en el tipo especificado.
        
        Args:
            db_type: Tipo de base de datos ("sqlserver", etc.)
            config: Configuración de base de datos
            
        Returns:
            Instancia de IDatabaseConnection
            
        Raises:
            ValueError: Si el tipo de BD no es soportado
        """
        if db_type.lower() in ('sqlserver', 'mssql', 'sql_server'):
            return SqlServerConnection(config)
        else:
            raise ValueError(f"Tipo de base de datos no soportado: {db_type}")