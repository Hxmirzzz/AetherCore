"""
Entidades del dominio relacionadas con geografía y ubicación.

Estas entidades representan conceptos del negocio y son independientes
de cualquier detalle de implementación (base de datos, UI, etc.).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Ciudad:
    """
    Entidad que representa una ciudad en el sistema.
    
    Attributes:
        codigo: Código único de la ciudad (ej. "01")
        nombre: Nombre de la ciudad (ej. "BOGOTÁ")
    """
    codigo: str
    nombre: str
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de ciudad no puede estar vacío")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre de ciudad no puede estar vacío")
    
    @property
    def descripcion_completa(self) -> str:
        """Retorna la descripción completa: 'CODIGO - NOMBRE'"""
        return f"{self.codigo} - {self.nombre}"
    
    def __str__(self) -> str:
        return self.descripcion_completa


@dataclass(frozen=True)
class Sucursal:
    """
    Entidad que representa una sucursal de un cliente.
    
    Attributes:
        codigo: Código único de la sucursal
        nombre: Nombre de la sucursal
        ciudad: Ciudad donde está ubicada la sucursal
    """
    codigo: str
    nombre: str
    ciudad: Optional[Ciudad] = None
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de sucursal no puede estar vacío")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre de sucursal no puede estar vacío")
    
    @property
    def descripcion_completa(self) -> str:
        """Retorna la descripción completa: 'CODIGO - NOMBRE'"""
        return f"{self.codigo} - {self.nombre}"
    
    def __str__(self) -> str:
        return self.descripcion_completa