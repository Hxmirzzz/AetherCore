"""
Mapeos y constantes del sistema.
"""
from __future__ import annotations
from typing import Dict, List, Optional

class ClienteMapeos:
    """Mapeos relacionados con códigos de clientes"""
    
    CLIENTE_TO_CC: Dict[str, str] = {
        '45': '52',
        '46': '01',
        '47': '02',
        '48': '23'
    }
    
    PRIORIDAD_CLIENTES: List[str] = ['47', '46', '48', '45']
    
    @classmethod
    def get_cc_code(cls, codigo_cliente: str) -> str:
        """
        Obtiene el CC Code para un código de cliente.
        
        Args:
            codigo_cliente: Código del cliente (ej. "47")
            
        Returns:
            CC Code correspondiente (ej. "02"), o "00" si no se encuentra
        """
        return cls.CLIENTE_TO_CC.get(codigo_cliente, '00')
    
    @classmethod
    def es_cliente_permitido(cls, codigo_cliente: str) -> bool:
        """Verifica si un código de cliente está permitido"""
        return codigo_cliente in cls.CLIENTE_TO_CC
    
    @classmethod
    def get_clientes_permitidos(cls) -> List[str]:
        """Retorna la lista de códigos de clientes permitidos"""
        return list(cls.CLIENTE_TO_CC.keys())

    @classmethod
    def get_prioridad(cls, codigo_cliente: str) -> int:
        """
        Obtiene la prioridad de un cliente (1 es más alta).
        
        Returns:
            Índice de prioridad (0-3), o 99 si no está en la lista
        """
        try:
            return cls.PRIORIDAD_CLIENTES.index(codigo_cliente)
        except ValueError:
            return 99

# ══════════════════════════════════════════════════════════════
# MAPEOS DE TIPOS DE RUTA, PRIORIDAD, PEDIDO
# ══════════════════════════════════════════════════════════════

class TipoRutaMapeos:
    """Mapeos para tipos de ruta"""
    
    CODIGO_TO_DESCRIPCION: Dict[str, str] = {
        'D': 'DIURNO',
        'N': 'NOCTURNO'
    }
    
    @classmethod
    def get_descripcion(cls, codigo: str) -> str:
        """Obtiene la descripción de un tipo de ruta"""
        return cls.CODIGO_TO_DESCRIPCION.get(codigo.upper(), codigo)


class PrioridadMapeos:
    """Mapeos para prioridades"""
    
    CODIGO_TO_DESCRIPCION: Dict[str, str] = {
        'A': 'AM',
        'P': 'PM',
        'R': 'RESTRICCIÓN',
        'D': 'DÍA'
    }
    
    @classmethod
    def get_descripcion(cls, codigo: str) -> str:
        """Obtiene la descripción de una prioridad"""
        return cls.CODIGO_TO_DESCRIPCION.get(codigo.upper(), codigo)


class TipoPedidoMapeos:
    """Mapeos para tipos de pedido"""
    
    CODIGO_TO_DESCRIPCION: Dict[str, str] = {
        'P': 'PROGRAMADO',
        'N': 'ESPECIAL'
    }
    
    @classmethod
    def get_descripcion(cls, codigo: str) -> str:
        """Obtiene la descripción de un tipo de pedido"""
        return cls.CODIGO_TO_DESCRIPCION.get(codigo.upper(), codigo)

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE DENOMINACIONES
# ══════════════════════════════════════════════════════════════

class DenominacionesConfig:
    """Configuración de denominaciones de billetes"""
    
    DENOMINACIONES: List[str] = [
        '100000', '50000AD', '50000NF', '20000AD', '20000NF', 
        '10000AD', '10000NF', '5000AD', '5000NF', '2000AD', '2000NF',
        '1000AD', '1000NF', '500AD', '500NF', '200AD', '200NF',
        '100AD', '100NF', '50AD', '50NF'
    ]
    
    @classmethod
    def es_denominacion_valida(cls, denominacion: str) -> bool:
        """Verifica si una denominación es válida"""
        return denominacion in cls.DENOMINACIONES
    
    @classmethod
    def get_denominaciones_ordenadas(cls) -> List[str]:
        """Retorna las denominaciones ordenadas"""
        return cls.DENOMINACIONES.copy()


class TextosConstantes:
    """Textos constantes utilizados en la aplicación"""
    
    # Textos para valores no encontrados
    CIUDAD_NO_ENCONTRADA = "Ciudad no encontrada"
    CATEGORIA_NO_ENCONTRADA = "Categoría no encontrada"
    SUCURSAL_NO_ENCONTRADA = "Sucursal no encontrada"
    CLIENTE_NO_ENCONTRADO = "Cliente no encontrado"
    TIPO_NO_ENCONTRADO = "Tipo no encontrado"
    PUNTO_NO_ENCONTRADO_XML = "No encontrado"
    
    # Nombres de hojas Excel (XML)
    HOJA_PROVISION_XML = "PROVISION"
    HOJA_RECOLECCION_XML = "RECOLECCION"
    
    # Encabezados de grupo (XML)
    ENCABEZADO_INFO_ENTREGA_XML = "INFORMACIÓN DE ENTREGA"
    ENCABEZADO_DENOMINACIONES_XML = "DENOMINACIONES"
    ENCABEZADO_TOTAL_XML = "VALORES"
    
    # Tipos de servicio (XML)
    SERVICIO_PROVISION_XML = "PROVISIÓN"
    SERVICIO_RECOLECCION_XML = "RECOLECCIÓN"
    
    # Tipos de orden (XML)
    TIPO_ORDEN_NORMAL_XML = "NORMAL"
    TIPO_ORDEN_EMERGENCIA_XML = "EMERGENCIA"


class FormatosFecha:
    """Formatos de fecha utilizados en la aplicación"""
    
    # Formatos de entrada
    FORMATO_ENTRADA_DDMMYYYY = '%d%m%Y'
    FORMATO_ENTRADA_YYYYMMDD = '%Y-%m-%d'
    FORMATO_ENTRADA_YYYYMMDDHHMMSS = '%Y%m%d%H%M%S'
    FORMATO_ENTRADA_YYMMDDHHMMSS = '%y%m%d%H%M%S'
    
    # Formatos de salida
    FORMATO_SALIDA_DISPLAY = '%d/%m/%Y'  # DD/MM/YYYY
    FORMATO_SALIDA_TIMESTAMP = '%y%m%d%H%M%S'  # YYMMDDHHMMSS
    
    @classmethod
    def get_formato_entrada_por_longitud(cls, fecha_str: str) -> str:
        """
        Determina el formato de entrada basado en la longitud del string.
        
        Args:
            fecha_str: String de fecha
            
        Returns:
            Formato de fecha correspondiente
        """
        longitud = len(fecha_str.strip())
        
        if longitud == 8:
            # Podría ser DDMMYYYY o YYYYMMDD
            if fecha_str[:2] in ('19', '20'):  # Empieza con año
                return cls.FORMATO_ENTRADA_YYYYMMDD.replace('-', '')
            else:
                return cls.FORMATO_ENTRADA_DDMMYYYY
        elif longitud == 10 and '-' in fecha_str:
            return cls.FORMATO_ENTRADA_YYYYMMDD
        elif longitud == 12:
            return cls.FORMATO_ENTRADA_YYMMDDHHMMSS
        elif longitud == 14:
            return cls.FORMATO_ENTRADA_YYYYMMDDHHMMSS
        else:
            # Por defecto, asumir DDMMYYYY
            return cls.FORMATO_ENTRADA_DDMMYYYY