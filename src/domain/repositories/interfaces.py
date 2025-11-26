"""
Interfaces de repositorios del dominio (Dependency Inversion Principle).

Estas interfaces definen contratos que la capa de infraestructura debe implementar.
El dominio depende de abstracciones, no de implementaciones concretas.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..entities.ciudad import Ciudad, Sucursal
from ..entities.cliente import Cliente, Punto
from ..entities.servicio import Servicio, Categoria, TipoValor
from ..value_objects.codigo_punto import CodigoPunto, CodigoCliente


class ICiudadRepository(ABC):
    """Interfaz para repositorio de ciudades"""
    
    @abstractmethod
    def obtener_por_codigo(self, codigo: str) -> Optional[Ciudad]:
        """
        Obtiene una ciudad por su código.
        
        Args:
            codigo: Código de la ciudad
            
        Returns:
            Ciudad encontrada o None
        """
        pass
    
    @abstractmethod
    def obtener_todas(self) -> Dict[str, Ciudad]:
        """
        Obtiene todas las ciudades del sistema.
        
        Returns:
            Diccionario {codigo: Ciudad}
        """
        pass


class IClienteRepository(ABC):
    """Interfaz para repositorio de clientes"""
    
    @abstractmethod
    def obtener_por_codigo(self, codigo: CodigoCliente) -> Optional[Cliente]:
        """
        Obtiene un cliente por su código.
        
        Args:
            codigo: CodigoCliente value object
            
        Returns:
            Cliente encontrado o None
        """
        pass
    
    @abstractmethod
    def obtener_por_nit(self, nit: str) -> Optional[Cliente]:
        """
        Obtiene un cliente por su NIT.
        
        Args:
            nit: NIT del cliente
            
        Returns:
            Cliente encontrado o None
        """
        pass
    
    @abstractmethod
    def obtener_todos(self) -> List[Cliente]:
        """
        Obtiene todos los clientes permitidos.
        
        Returns:
            Lista de clientes
        """
        pass


class IPuntoRepository(ABC):
    """Interfaz para repositorio de puntos"""
    
    @abstractmethod
    def obtener_por_codigo(self, codigo: CodigoPunto) -> Optional[Punto]:
        """
        Obtiene un punto por su código.
        
        Args:
            codigo: CodigoPunto value object
            
        Returns:
            Punto encontrado o None
        """
        pass
    
    @abstractmethod
    def obtener_todos_por_cliente(self, codigo_cliente: CodigoCliente) -> List[Punto]:
        """
        Obtiene todos los puntos de un cliente.
        
        Args:
            codigo_cliente: CodigoCliente value object
            
        Returns:
            Lista de puntos del cliente
        """
        pass
    
    @abstractmethod
    def obtener_todos(self) -> Dict[str, Punto]:
        """
        Obtiene todos los puntos del sistema (de clientes permitidos).
        
        Returns:
            Diccionario {codigo_numerico: Punto}
        """
        pass
    
    @abstractmethod
    def obtener_cliente_por_punto(
        self, 
        codigo_punto: CodigoPunto,
        clientes_permitidos: List[CodigoCliente]
    ) -> Optional[Cliente]:
        """
        Obtiene el cliente asociado a un punto, con lógica de priorización.
        
        Args:
            codigo_punto: CodigoPunto value object
            clientes_permitidos: Lista de códigos de clientes permitidos
            
        Returns:
            Cliente encontrado o None
        """
        pass


class ISucursalRepository(ABC):
    """Interfaz para repositorio de sucursales"""
    
    @abstractmethod
    def obtener_por_codigo(self, codigo: str) -> Optional[Sucursal]:
        """
        Obtiene una sucursal por su código.
        
        Args:
            codigo: Código de la sucursal
            
        Returns:
            Sucursal encontrada o None
        """
        pass
    
    @abstractmethod
    def obtener_por_punto(self, codigo_punto: CodigoPunto) -> Optional[Sucursal]:
        """
        Obtiene la sucursal asociada a un punto.
        
        Args:
            codigo_punto: CodigoPunto value object
            
        Returns:
            Sucursal encontrada o None
        """
        pass
    
    @abstractmethod
    def obtener_todas(self) -> Dict[str, Sucursal]:
        """
        Obtiene todas las sucursales.
        
        Returns:
            Diccionario {codigo_punto: Sucursal}
        """
        pass


class IServicioRepository(ABC):
    """Interfaz para repositorio de servicios"""
    
    @abstractmethod
    def obtener_servicio_por_codigo(self, codigo: str) -> Optional[Servicio]:
        """Obtiene un servicio por su código"""
        pass
    
    @abstractmethod
    def obtener_todos_servicios(self) -> Dict[str, Servicio]:
        """Obtiene todos los servicios"""
        pass
    
    @abstractmethod
    def obtener_categoria_por_codigo(self, codigo: str) -> Optional[Categoria]:
        """Obtiene una categoría por su código"""
        pass
    
    @abstractmethod
    def obtener_todas_categorias(self) -> Dict[str, Categoria]:
        """Obtiene todas las categorías"""
        pass
    
    @abstractmethod
    def obtener_tipo_valor_por_codigo(self, codigo: str) -> Optional[TipoValor]:
        """Obtiene un tipo de valor por su código"""
        pass
    
    @abstractmethod
    def obtener_todos_tipos_valor(self) -> Dict[str, TipoValor]:
        """Obtiene todos los tipos de valor"""
        pass