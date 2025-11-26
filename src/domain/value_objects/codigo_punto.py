"""
Value Objects para códigos de dominio (punto y cliente).
Inmutables, comparan por valor y validan formato básico.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CodigoPunto:
    """
    Value Object que representa un código de punto.
    
    Maneja diferentes formatos:
    - "47-0033" (formato con cliente)
    - "0033" (formato numérico)
    - "XX-SUC-0033" (formato con sucursal)
    """
    valor: str
    
    def __post_init__(self):
        if not self.valor or not self.valor.strip():
            raise ValueError("El código de punto no puede estar vacío")
        
        # Normalizar y validar
        valor_limpio = self.valor.strip()
        
        # Validación opcional: formato básico
        if not valor_limpio:
            raise ValueError("Código de punto inválido")
        
        object.__setattr__(self, 'valor', valor_limpio)
    
    @classmethod
    def from_raw(cls, codigo_raw: str) -> 'CodigoPunto':
        """Crea un CodigoPunto desde un código raw"""
        if not codigo_raw:
            raise ValueError("El código raw no puede estar vacío")
        return cls(valor=codigo_raw.strip())
    
    @property
    def parte_numerica(self) -> str:
        """
        Extrae solo la parte numérica del código.
        
        Ejemplos:
            "47-0033" -> "0033"
            "0033" -> "0033"
            "XX-SUC-0033" -> "0033"
        """
        if '-' in self.valor:
            return self.valor.split('-')[-1]
        return self.valor
    
    @property
    def codigo_cliente(self) -> Optional[str]:
        """
        Extrae el código de cliente si existe.
        
        Ejemplos:
            "47-0033" -> "47"
            "0033" -> None
        """
        if '-' in self.valor:
            partes = self.valor.split('-')
            if partes[0].isdigit() and len(partes) >= 2:
                return partes[0]
        return None
    
    def con_cliente(self, codigo_cliente: str) -> 'CodigoPunto':
        """
        Retorna un nuevo CodigoPunto con el cliente prefijado.
        """
        if self.codigo_cliente:
            # Ya tiene cliente, reemplazar
            return CodigoPunto(valor=f"{codigo_cliente}-{self.parte_numerica}")
        else:
            # No tiene cliente, añadir
            return CodigoPunto(valor=f"{codigo_cliente}-{self.valor}")
    
    def __str__(self) -> str:
        return self.valor
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, CodigoPunto):
            return False
        # Comparar por parte numérica
        return self.parte_numerica == other.parte_numerica


@dataclass(frozen=True)
class CodigoCliente:
    """
    Value Object que representa un código de cliente.
    
    Valida que el código esté dentro de los clientes permitidos.
    """
    valor: str
    
    # Clientes permitidos (idealmente inyectado desde config)
    CLIENTES_PERMITIDOS = {"45", "46", "47", "48"}
    
    def __post_init__(self):
        if not self.valor or not self.valor.strip():
            raise ValueError("El código de cliente no puede estar vacío")
        
        valor_limpio = self.valor.strip()
        object.__setattr__(self, 'valor', valor_limpio)
        
        if valor_limpio not in self.CLIENTES_PERMITIDOS:
            raise ValueError(
                f"Cliente '{valor_limpio}' no permitido. "
                f"Clientes válidos: {self.CLIENTES_PERMITIDOS}"
            )
    
    @classmethod
    def from_raw(cls, codigo_raw: str) -> 'CodigoCliente':
        """Crea un CodigoCliente desde un código raw"""
        return cls(valor=codigo_raw.strip())
    
    @property
    def cc_code(self) -> str:
        """
        Retorna el CC Code asociado al cliente.
        
        Mapeo:
            "45" -> "52"
            "46" -> "01"
            "47" -> "02"
            "48" -> "23"
        """
        mapeo = {
            "45": "52",
            "46": "01",
            "47": "02",
            "48": "23"
        }
        return mapeo.get(self.valor, "00")
    
    def __str__(self) -> str:
        return self.valor