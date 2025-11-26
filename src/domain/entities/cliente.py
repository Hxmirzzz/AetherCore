"""
Entidades de cliente, sucursal y punto (Dominio).
Inmutables y sin dependencias de infraestructura.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .ciudad import Ciudad, Sucursal


@dataclass(frozen=True)
class Cliente:
    codigo: str
    nombre: str
    razon_social: Optional[str] = None
    sigla: Optional[str] = None
    
    @classmethod
    def crear_desde_db(cls, row) -> 'Cliente':
        """Factory method para crear desde resultado de DB"""
        return cls(
            codigo=str(row.cod_cliente),
            nombre=row.cliente,
            razon_social=getattr(row, 'razon_social', None),
            sigla=getattr(row, 'sigla', None)
        )


@dataclass(frozen=True)
class Punto:
    """
    Entidad que representa un punto de servicio (ATM, oficina, etc.).
    
    SIEMPRE debe tener todas sus relaciones completas.
    """
    codigo: str
    nombre: str
    cliente: Cliente
    ciudad: Ciudad
    sucursal: Sucursal
    
    def __post_init__(self):
        if not self.codigo or not self.codigo.strip():
            raise ValueError("El código de punto no puede estar vacío")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre de punto no puede estar vacío")
        
        if self.cliente is None:
            raise ValueError("El punto debe tener un cliente asociado")
        if self.ciudad is None:
            raise ValueError("El punto debe tener una ciudad asociada")
        if self.sucursal is None:
            raise ValueError("El punto debe tener una sucursal asociada")
    
    @property
    def codigo_numerico(self) -> str:
        """
        Extrae solo la parte numérica del código.
        
        Si el código es "47-0033", retorna "0033".
        Si el código es "0033", retorna "0033".
        """
        if '-' in self.codigo:
            return self.codigo.split('-')[-1]
        return self.codigo