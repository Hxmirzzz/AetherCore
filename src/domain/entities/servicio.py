"""
Entidades de servicio y catálogos (Dominio).
Inmutables y sin dependencias de infraestructura.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class Servicio:
    """
    Entidad que representa un servicio ofrecido.
    """
    codigo: str
    descripcion: str
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de servicio no puede estar vacío")
        if not self.descripcion or not self.descripcion.strip():
            raise ValueError("La descripción de servicio no puede estar vacía")
    
    @property
    def descripcion_completa(self) -> str:
        """Retorna la descripción completa: 'CODIGO - DESCRIPCION'"""
        return f"{self.codigo} - {self.descripcion}"
    
    def __str__(self) -> str:
        return self.descripcion_completa


@dataclass(frozen=True)
class Categoria:
    """
    Entidad que representa una categoría de gaveta.
    """
    codigo: str
    descripcion: str
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de categoría no puede estar vacío")
        if not self.descripcion or not self.descripcion.strip():
            raise ValueError("La descripción de categoría no puede estar vacía")
    
    @property
    def descripcion_completa(self) -> str:
        return f"{self.codigo} - {self.descripcion}"
    
    def __str__(self) -> str:
        return self.descripcion_completa


@dataclass(frozen=True)
class TipoValor:
    """
    Entidad que representa un tipo de valor (divisa).
    """
    codigo: str
    divisa: str
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de tipo valor no puede estar vacío")
        if not self.divisa or not self.divisa.strip():
            raise ValueError("La divisa no puede estar vacía")
    
    def __str__(self) -> str:
        return f"{self.codigo} - {self.divisa}"