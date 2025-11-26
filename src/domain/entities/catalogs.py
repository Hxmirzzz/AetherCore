"""
Enums y catálogos del dominio.

Estos enums representan conceptos de negocio y deben estar en el dominio,
NO en infraestructura.
"""
from enum import Enum
from typing import Dict, Optional


# ══════════════════════════════════════════════════════════════
# CATEGORÍAS
# ══════════════════════════════════════════════════════════════

class CodigoCategoria(Enum):
    """Códigos de categorías de gavetas"""
    ATM = 1
    BUEN_ESTADO = 2
    CIRCULANTE = 85
    DETERIORADO = 23
    FUERA_DE_CIRCULACION = 86
    NF_BUEN_ESTADO = 112
    NF_DETERIORADO = 113
    NF_ATM = 114
    NUEVO_CONO = 21
    VIEJO_CONO = 22
    NUEVA_FAMILIA = 24


class CategoriaCatalogo:
    """
    Catálogo de categorías de gavetas.
    
    Proporciona mapeos entre códigos y descripciones.
    """
    
    _DESCRIPCIONES: Dict[int, str] = {
        1: "ATM",
        2: "BUEN ESTADO",
        85: "CIRCULANTE",
        23: "DETERIORADO",
        86: "FUERA DE CIRCULACIÓN",
        112: "NF BUEN ESTADO",
        113: "NF DETERIORADO",
        114: "NF ATM",
        21: "NUEVO CONO",
        22: "VIEJO CONO",
        24: "NUEVA FAMILIA",
    }
    
    _CODIGOS: Dict[str, int] = {
        v.upper(): k for k, v in _DESCRIPCIONES.items()
    }
    
    @classmethod
    def obtener_descripcion(cls, codigo: int) -> Optional[str]:
        """Obtiene la descripción de una categoría por su código"""
        return cls._DESCRIPCIONES.get(codigo)
    
    @classmethod
    def obtener_codigo(cls, descripcion: str) -> Optional[int]:
        """Obtiene el código de una categoría por su descripción"""
        return cls._CODIGOS.get(descripcion.strip().upper())
    
    @classmethod
    def todas_descripciones(cls) -> Dict[int, str]:
        """Retorna todas las descripciones"""
        return cls._DESCRIPCIONES.copy()


# ══════════════════════════════════════════════════════════════
# SERVICIOS (migrado desde mapeos.py)
# ══════════════════════════════════════════════════════════════

class CodigoServicio(Enum):
    """Códigos de tipos de servicio"""
    APROVISIONAMIENTO_DE_OFICINAS = 1
    TRASLADO_DE_FONDOS = 3
    APROVISIONAMIENTO_DE_ATM_NIVEL_7 = 4
    RECOLECCION_DE_VALORES = 5
    SERVICIO_DE_REFAJADO = 8
    SOLICITUD_DE_ELEMENTOS_DE_REMESA = 12
    SERVICIO_FLM_MANTENIMIENTO = 14
    CONSIGNACION_BANCO_REPUBLICA = 26


class ServicioCatalogo:
    """
    Catálogo de servicios.
    
    Proporciona mapeos entre códigos y descripciones.
    """
    
    _DESCRIPCIONES: Dict[int, str] = {
        1: "APROVISIONAMIENTO DE OFICINAS",
        3: "TRASLADO DE FONDOS",
        4: "APROVISIONAMIENTO DE ATM NIVEL 7",
        5: "RECOLECCIÓN DE VALORES",
        8: "SERVICIO DE REFAJADO",
        12: "SOLICITUD DE ELEMENTOS DE REMESA",
        14: "SERVICIO FLM (MANTENIMIENTO DE PRIMERA LINEA)",
        26: "CONSIGANCIÓN BANCO DE LA REPÚBLICA",
    }
    
    _CODIGOS: Dict[str, int] = {
        v.upper(): k for k, v in _DESCRIPCIONES.items()
    }
    
    @classmethod
    def obtener_descripcion(cls, codigo: int) -> Optional[str]:
        """Obtiene la descripción de un servicio por su código"""
        return cls._DESCRIPCIONES.get(codigo)
    
    @classmethod
    def obtener_codigo(cls, descripcion: str) -> Optional[int]:
        """Obtiene el código de un servicio por su descripción"""
        return cls._CODIGOS.get(descripcion.strip().upper())
    
    @classmethod
    def todas_descripciones(cls) -> Dict[int, str]:
        """Retorna todas las descripciones"""
        return cls._DESCRIPCIONES.copy()


# ══════════════════════════════════════════════════════════════
# DIVISAS
# ══════════════════════════════════════════════════════════════

class CodigoDivisa(Enum):
    """Códigos de divisas/monedas"""
    COP_1 = 1
    COP_2 = 2
    USD = 3
    CAD = 4
    EUR = 5
    EUR_6 = 6
    CHF = 7
    JPY = 8
    GBP = 9
    EUR_24 = 24


class DivisaCatalogo:
    """
    Catálogo de divisas.
    
    Proporciona mapeos entre códigos y nombres de divisa.
    """
    
    _DESCRIPCIONES: Dict[int, str] = {
        1: "COP",
        2: "COP",
        3: "USD",
        4: "CAD",
        5: "EUR",
        6: "EUR",
        7: "CHF",
        8: "JPY",
        9: "GBP",
        24: "EUR",
    }
    
    # Construcción del diccionario inverso
    @classmethod
    def _construir_codigos(cls) -> Dict[str, int]:
        """Construye el diccionario inverso divisa -> código"""
        codigos = {}
        for v in set(cls._DESCRIPCIONES.values()):
            # Encontrar el primer código que tenga esta divisa
            for k, vv in cls._DESCRIPCIONES.items():
                if vv == v:
                    codigos[v.upper()] = k
                    break
        return codigos
    
    _CODIGOS: Dict[str, int] = None  # Se inicializa en el primer acceso
    
    @classmethod
    def obtener_divisa(cls, codigo: int) -> Optional[str]:
        """Obtiene el nombre de la divisa por su código"""
        return cls._DESCRIPCIONES.get(codigo)
    
    @classmethod
    def obtener_codigo(cls, divisa: str) -> Optional[int]:
        """Obtiene el código de una divisa por su nombre"""
        # Inicializar _CODIGOS si no existe
        if cls._CODIGOS is None:
            cls._CODIGOS = cls._construir_codigos()
        return cls._CODIGOS.get(divisa.strip().upper())
    
    @classmethod
    def resolver_divisa(cls, codigo_o_desc: str) -> tuple[Optional[str], Optional[str]]:
        """
        Resuelve una divisa desde código o descripción.
        
        Args:
            codigo_o_desc: Código numérico ('3') o nombre ('USD')
            
        Returns:
            Tupla (codigo, divisa) o (None, None) si no se encuentra
        """
        s = str(codigo_o_desc).strip()
        if not s:
            return (None, None)
        
        # ¿Es numérico?
        try:
            n = int(s)
            desc = cls._DESCRIPCIONES.get(n)
            if desc:
                return (str(n), desc)
        except ValueError:
            pass
        
        # ¿Es texto?
        if cls._CODIGOS is None:
            cls._CODIGOS = cls._construir_codigos()
        code = cls._CODIGOS.get(s.upper())
        if code is not None:
            return (str(code), s.upper())
        
        return (None, None)