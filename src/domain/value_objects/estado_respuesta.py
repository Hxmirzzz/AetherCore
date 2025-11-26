"""
Value Objects relacionados con estados de procesamiento.

Los Value Objects son inmutables y se comparan por valor, no por identidad.
"""
from enum import Enum


class EstadoRespuesta(Enum):
    """
    Estado de respuesta para archivos procesados.
    
    Attributes:
        EXITO: Procesamiento exitoso (valor: "1")
        ERROR: Procesamiento con errores o rechazo (valor: "2")
    """
    EXITO = "1"
    ERROR = "2"
    
    @classmethod
    def from_string(cls, valor: str) -> 'EstadoRespuesta':
        """
        Crea un EstadoRespuesta desde un string.
        
        Args:
            valor: String "1" o "2"
            
        Returns:
            EstadoRespuesta correspondiente
            
        Raises:
            ValueError: Si el valor no es "1" o "2"
        """
        if valor == "1":
            return cls.EXITO
        elif valor == "2":
            return cls.ERROR
        else:
            raise ValueError(f"Estado inválido: '{valor}'. Debe ser '1' o '2'")
    
    @property
    def es_exitoso(self) -> bool:
        """Retorna True si el estado es EXITO"""
        return self == EstadoRespuesta.EXITO
    
    @property
    def es_error(self) -> bool:
        """Retorna True si el estado es ERROR"""
        return self == EstadoRespuesta.ERROR
    
    def __str__(self) -> str:
        return self.value


class TipoRuta(Enum):
    """Tipo de ruta para el servicio"""
    DIURNO = "D"
    NOCTURNO = "N"
    
    @classmethod
    def from_string(cls, valor: str) -> 'TipoRuta':
        """Crea un TipoRuta desde un string"""
        valor_upper = valor.upper().strip()
        if valor_upper == "D":
            return cls.DIURNO
        elif valor_upper == "N":
            return cls.NOCTURNO
        else:
            raise ValueError(f"Tipo de ruta inválido: '{valor}'. Debe ser 'D' o 'N'")
    
    @property
    def descripcion(self) -> str:
        """Retorna la descripción legible"""
        return "DIURNO" if self == TipoRuta.DIURNO else "NOCTURNO"
    
    def __str__(self) -> str:
        return self.descripcion


class Prioridad(Enum):
    """Prioridad del servicio"""
    AM = "A"
    PM = "P"
    RESTRICCION = "R"
    DIA = "D"
    
    @classmethod
    def from_string(cls, valor: str) -> 'Prioridad':
        """Crea una Prioridad desde un string"""
        valor_upper = valor.upper().strip()
        mapping = {
            "A": cls.AM,
            "P": cls.PM,
            "R": cls.RESTRICCION,
            "D": cls.DIA
        }
        if valor_upper in mapping:
            return mapping[valor_upper]
        raise ValueError(f"Prioridad inválida: '{valor}'. Debe ser A, P, R o D")
    
    @property
    def descripcion(self) -> str:
        """Retorna la descripción legible"""
        mapping = {
            Prioridad.AM: "AM",
            Prioridad.PM: "PM",
            Prioridad.RESTRICCION: "RESTRICCIÓN",
            Prioridad.DIA: "DÍA"
        }
        return mapping[self]
    
    def __str__(self) -> str:
        return self.descripcion


class TipoPedido(Enum):
    """Tipo de pedido"""
    PROGRAMADO = "P"
    ESPECIAL = "N"
    
    @classmethod
    def from_string(cls, valor: str) -> 'TipoPedido':
        """Crea un TipoPedido desde un string"""
        valor_upper = valor.upper().strip()
        if valor_upper == "P":
            return cls.PROGRAMADO
        elif valor_upper == "N":
            return cls.ESPECIAL
        else:
            raise ValueError(f"Tipo de pedido inválido: '{valor}'. Debe ser 'P' o 'N'")
    
    @property
    def descripcion(self) -> str:
        """Retorna la descripción legible"""
        return "PROGRAMADO" if self == TipoPedido.PROGRAMADO else "ESPECIAL"
    
    def __str__(self) -> str:
        return self.descripcion