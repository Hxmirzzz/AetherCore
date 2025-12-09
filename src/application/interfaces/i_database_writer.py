"""
Interfaz para escritura en base de datos (Dependency Inversion Principle).

Define el contrato que deben implementar los repositorios de escritura,
permitiendo que la capa de aplicación dependa de abstracciones.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..dto.servicio_dto import ServicioDTO
from ..dto.transaccion_dto import TransaccionDTO


class IDatabaseWriter(ABC):
    """
    Interfaz para escritura de servicios y transacciones en base de datos.
    
    Esta interfaz define el contrato para insertar datos en la BD,
    sin exponer detalles de implementación (stored procedures, queries, etc.).
    """
    
    @abstractmethod
    def insertar_servicio_con_transaccion(
        self,
        servicio_dto: ServicioDTO,
        transaccion_dto: TransaccionDTO
    ) -> Optional[str]:
        """
        Inserta un servicio junto con su transacción CEF en la base de datos.
        
        Args:
            servicio_dto: DTO con datos del servicio
            transaccion_dto: DTO con datos de la transacción
            
        Returns:
            Orden de Servicio generada (ej: "S-000123") o None si falla
            
        Raises:
            DatabaseWriteException: Si ocurre un error durante la inserción
            
        Notes:
            Esta operación debe ser atómica (transacción de BD).
            Si falla la inserción del servicio o la transacción,
            ambas deben revertirse (rollback).
        """
        pass
    
    @abstractmethod
    def verificar_servicio_existe(self, numero_pedido: str) -> bool:
        """
        Verifica si un servicio ya existe en la base de datos.
        
        Args:
            numero_pedido: Número de pedido a verificar
            
        Returns:
            True si el servicio ya existe, False en caso contrario
            
        Notes:
            Útil para evitar duplicados antes de insertar.
        """
        pass


class DatabaseWriteException(Exception):
    """
    Excepción lanzada cuando falla una operación de escritura en BD.
    
    Attributes:
        message: Descripción del error
        inner_exception: Excepción original (si existe)
        orden_servicio: Orden de servicio afectada (si aplica)
    """
    
    def __init__(
        self,
        message: str,
        inner_exception: Optional[Exception] = None,
        orden_servicio: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.inner_exception = inner_exception
        self.orden_servicio = orden_servicio
    
    def __str__(self) -> str:
        result = self.message
        if self.orden_servicio:
            result += f" (Orden: {self.orden_servicio})"
        if self.inner_exception:
            result += f" - Error original: {self.inner_exception}"
        return result