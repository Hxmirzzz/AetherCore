# domain/value_objects/fecha.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class FechaProcesamiento:
    """
    Value Object para fechas de procesamiento.
    
    Encapsula la lógica de parsing de diferentes formatos.
    """
    valor: datetime
    
    @classmethod
    def from_string(cls, fecha_str: str, formato: str = '%d%m%Y') -> 'FechaProcesamiento':
        """
        Crea una fecha desde un string con formato específico.
        
        Args:
            fecha_str: String de fecha (ej. "15052025")
            formato: Formato de la fecha (default: DDMMYYYY)
        """
        try:
            dt = datetime.strptime(fecha_str.strip(), formato)
            return cls(valor=dt)
        except ValueError as e:
            raise ValueError(f"Formato de fecha inválido '{fecha_str}' con formato '{formato}': {e}")
    
    @classmethod
    def from_yyyymmdd(cls, fecha_str: str) -> 'FechaProcesamiento':
        """Crea desde formato YYYY-MM-DD"""
        return cls.from_string(fecha_str, '%Y-%m-%d')
    
    @classmethod
    def from_ddmmyyyy(cls, fecha_str: str) -> 'FechaProcesamiento':
        """Crea desde formato DDMMYYYY"""
        return cls.from_string(fecha_str, '%d%m%Y')
    
    @property
    def formato_display(self) -> str:
        """Retorna en formato DD/MM/YYYY"""
        return self.valor.strftime('%d/%m/%Y')
    
    @property
    def formato_timestamp(self) -> str:
        """Retorna en formato YYMMDDHHMMSS"""
        return self.valor.strftime('%y%m%d%H%M%S')
    
    def __str__(self) -> str:
        return self.formato_display