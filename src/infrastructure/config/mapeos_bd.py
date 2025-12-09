"""
Mapeos específicos entre archivos de entrada (TXT/XML) y base de datos.

Este módulo contiene la lógica de traducción entre:
- Códigos de servicio de archivos → Códigos de concepto de BD
- Códigos de divisa → Strings limpios para BD
- Indicadores de tipo de punto/cliente
- Estados de servicio y transacción

IMPORTANTE: Estos mapeos son configuración de infraestructura,
NO conceptos de dominio.
"""
from typing import Optional, Dict, Tuple
from enum import Enum
import logging


logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# MAPEO DE SERVICIOS → CONCEPTOS
# ══════════════════════════════════════════════════════════════

class MapeoConceptoServicio:
    """
    Mapeo entre códigos de servicio del archivo (TXT/XML) 
    y códigos de concepto de la base de datos.
    
    RELACIÓN:
    ─────────────────────────────────────────────────────────────
    Código     | Servicio Origen              | CodConcepto | Concepto BD
    Archivo    | (catalogos.py)               | (BD)        | (AdmConceptos)
    ─────────────────────────────────────────────────────────────
    1          | APROVISIONAMIENTO_OFICINAS    | 2           | PROVISION OFICINAS
    4          | APROVISIONAMIENTO_ATM_NIVEL_7 | 3           | PROVISION ATM
    5          | RECOLECCION_DE_VALORES        | 1           | RECOLECCION OFICINAS
    ─────────────────────────────────────────────────────────────
    """
    
    # Código archivo → CodConcepto BD
    SERVICIO_TO_CONCEPTO: Dict[int, int] = {
        1: 2,  # APROVISIONAMIENTO_OFICINAS → PROVISION OFICINAS (PV)
        4: 3,  # APROVISIONAMIENTO_ATM_NIVEL_7 → PROVISION ATM (PR)
        5: 1,  # RECOLECCION_DE_VALORES → RECOLECCION OFICINAS (RC)
    }
    
    # Tipos de concepto (para referencia)
    TIPOS_CONCEPTO: Dict[int, str] = {
        1: 'RC',  # Recolección
        2: 'PV',  # Provisión Oficinas
        3: 'PR',  # Provisión ATM
    }
    
    @classmethod
    def obtener_concepto_bd(cls, codigo_servicio_origen: int) -> Optional[int]:
        """
        Obtiene el CodConcepto de BD desde el código de servicio del archivo.
        
        Args:
            codigo_servicio_origen: Código que viene en TXT/XML (1, 4, 5, etc.)
            
        Returns:
            CodConcepto para la BD (1, 2, 3) o None si no se encuentra
            
        Example:
            >>> MapeoConceptoServicio.obtener_concepto_bd(4)
            3  # PROVISION ATM
        """
        concepto = cls.SERVICIO_TO_CONCEPTO.get(codigo_servicio_origen)
        
        if concepto is None:
            logger.warning(
                f"Código de servicio '{codigo_servicio_origen}' no tiene mapeo a CodConcepto. "
                f"Mapeos disponibles: {list(cls.SERVICIO_TO_CONCEPTO.keys())}"
            )
        
        return concepto
    
    @classmethod
    def es_provision(cls, codigo_servicio_origen: int) -> bool:
        """Verifica si el servicio es de tipo provisión"""
        concepto = cls.obtener_concepto_bd(codigo_servicio_origen)
        return concepto in (2, 3) if concepto else False
    
    @classmethod
    def es_recoleccion(cls, codigo_servicio_origen: int) -> bool:
        """Verifica si el servicio es de tipo recolección"""
        concepto = cls.obtener_concepto_bd(codigo_servicio_origen)
        return concepto == 1 if concepto else False


# ══════════════════════════════════════════════════════════════
# MAPEO DE DIVISAS
# ══════════════════════════════════════════════════════════════

class MapeoDivisa:
    """
    Mapeo y limpieza de códigos de divisa.
    
    Convierte códigos numéricos a strings limpios de 3 letras.
    
    Ejemplos:
        1 (COP_1) → "COP"
        3 (USD)   → "USD"
        5 (EUR)   → "EUR"
    """
    
    # Mapeo directo código → divisa limpia
    CODIGO_TO_DIVISA: Dict[int, str] = {
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
    
    @classmethod
    def limpiar_divisa(cls, codigo_divisa: int) -> str:
        """
        Convierte código de divisa a string limpio (3 letras).
        
        Args:
            codigo_divisa: Código numérico (1, 2, 3, etc.)
            
        Returns:
            String de 3 letras: "COP", "USD", "EUR", etc.
            Si no se encuentra, retorna "COP" por defecto.
            
        Example:
            >>> MapeoDivisa.limpiar_divisa(1)
            "COP"
            >>> MapeoDivisa.limpiar_divisa(3)
            "USD"
        """
        divisa = cls.CODIGO_TO_DIVISA.get(codigo_divisa)
        
        if divisa is None:
            logger.warning(
                f"Código de divisa '{codigo_divisa}' no encontrado. "
                f"Usando 'COP' por defecto."
            )
            return "COP"
        
        return divisa
    
    @classmethod
    def es_divisa_valida(cls, codigo_divisa: int) -> bool:
        """Verifica si el código de divisa es válido"""
        return codigo_divisa in cls.CODIGO_TO_DIVISA


# ══════════════════════════════════════════════════════════════
# INDICADORES DE TIPO (Origen/Destino)
# ══════════════════════════════════════════════════════════════

class IndicadorTipo(Enum):
    """
    Indicadores de tipo de entidad (Cliente, Punto, Fondo).
    
    Estos valores se usan en los campos:
    - @IndicadorTipoOrigen
    - @IndicadorTipoDestino
    """
    CLIENTE = 'C'
    PUNTO = 'P'
    FONDO = 'F'


class MapeoIndicadorTipo:
    """Lógica para determinar el indicador de tipo según el contexto"""
    
    @staticmethod
    def determinar_tipo_origen(cod_punto_origen: str, es_fondo: bool = False) -> str:
        """
        Determina el indicador de tipo para el origen.
        
        Args:
            cod_punto_origen: Código del punto origen
            es_fondo: True si el punto origen es un fondo
            
        Returns:
            'F' si es fondo, 'P' en otro caso
        """
        return IndicadorTipo.FONDO.value if es_fondo else IndicadorTipo.PUNTO.value
    
    @staticmethod
    def determinar_tipo_destino(cod_punto_destino: str) -> str:
        """
        Determina el indicador de tipo para el destino.
        
        Args:
            cod_punto_destino: Código del punto destino
            
        Returns:
            Siempre 'P' (punto)
        """
        return IndicadorTipo.PUNTO.value


# ══════════════════════════════════════════════════════════════
# ESTADOS DE SERVICIO Y TRANSACCIÓN
# ══════════════════════════════════════════════════════════════

class EstadoServicio(Enum):
    """
    Estados de servicio (CgsServicios.CodEstado).
    
    Valores: 0-7
    """
    SOLICITADO = 0
    CONFIRMADO = 1
    RECHAZADO = 2
    PROGRAMADO = 3
    ATENCION = 4
    FINALIZADO = 5
    CANCELADO = 6
    PENDIENTE = 7


class EstadoTransaccion(Enum):
    """
    Estados de transacción (CefTransacciones.EstadoTransaccion).
    
    Valores: strings
    """
    REGISTRO_TESORERIA = 'RegistroTesoreria'
    ENCOLADO_CONTEO = 'EncoladoParaConteo'
    CONTEO = 'Conteo'
    PENDIENTE_REVISION = 'PendienteRevision'
    APROBADO = 'Aprobado'
    RECHAZADO = 'Rechazado'
    CANCELADO = 'Cancelado'
    PROVISION_EN_PROCESO = 'ProvisionEnProceso'
    LISTO_ENTREGA = 'ListoParaEntrega'
    ENTREGADO = 'Entregado'


class MapeoEstadoInicial:
    """
    Mapeo de estados iniciales al insertar un nuevo servicio.
    
    REGLA DE NEGOCIO:
    - Si la transacción se crea en 'RegistroTesoreria' y el servicio
      viene con estado 0 (Solicitado), se promueve automáticamente a 1 (Confirmado).
    - Esto lo hace el SP, pero debemos enviar el estado correcto.
    """
    
    @staticmethod
    def obtener_estado_inicial_servicio() -> int:
        """
        Retorna el estado inicial para un nuevo servicio.
        
        Returns:
            0 (Solicitado) - El SP lo promoverá a 1 si aplica
        """
        return EstadoServicio.SOLICITADO.value
    
    @staticmethod
    def obtener_estado_inicial_transaccion() -> str:
        """
        Retorna el estado inicial para una nueva transacción.
        
        Returns:
            'RegistroTesoreria'
        """
        return EstadoTransaccion.REGISTRO_TESORERIA.value


# ══════════════════════════════════════════════════════════════
# MODALIDAD DE SERVICIO
# ══════════════════════════════════════════════════════════════

class ModalidadServicio:
    """
    Modalidades de servicio.
    
    Para TXT/XML, por defecto usamos '2' (A PEDIDO).
    """
    
    PROGRAMADO = '1'
    A_PEDIDO = '2'
    EMERGENCIA = '3'
    
    @staticmethod
    def obtener_modalidad_default() -> str:
        """Retorna la modalidad por defecto: A PEDIDO"""
        return ModalidadServicio.A_PEDIDO


# ══════════════════════════════════════════════════════════════
# TIPO DE TRANSACCIÓN
# ══════════════════════════════════════════════════════════════

class TipoTransaccion:
    """
    Tipos de transacción para CefTransacciones.
    
    Por defecto: 'Checkin'
    """
    
    CHECKIN = 'Checkin'
    CHECKOUT = 'Checkout'
    
    @staticmethod
    def obtener_tipo_default() -> str:
        """Retorna el tipo por defecto: Checkin"""
        return TipoTransaccion.CHECKIN


# ══════════════════════════════════════════════════════════════
# UTILIDADES DE CONVERSIÓN
# ══════════════════════════════════════════════════════════════

class ConversionHelper:
    """
    Utilidades para conversión de datos específicos de BD.
    """
    
    @staticmethod
    def determinar_tipo_denominacion(denominacion: int) -> str:
        """
        Determina si una denominación es billete o moneda.
        
        Args:
            denominacion: Valor de la denominación
            
        Returns:
            'BILLETE' si >= 1000, 'MONEDA' en otro caso
        """
        return 'BILLETE' if denominacion >= 1000 else 'MONEDA'
    
    @staticmethod
    def calcular_valor_servicio_provision(
        es_provision: bool,
        valor_calculado: float
    ) -> float:
        """
        Calcula el valor del servicio según el tipo.
        
        Args:
            es_provision: True si es provisión, False si es recolección
            valor_calculado: Valor calculado de las denominaciones
            
        Returns:
            valor_calculado si es provisión, 0 si es recolección
            
        Nota:
            En recolecciones, el valor se desconoce hasta el conteo,
            por lo tanto se envía 0.
        """
        return valor_calculado if es_provision else 0.0


# ══════════════════════════════════════════════════════════════
# VALIDACIONES
# ══════════════════════════════════════════════════════════════

class ValidacionMapeos:
    """
    Validaciones de integridad de mapeos.
    """
    
    @staticmethod
    def validar_servicio_soportado(codigo_servicio: int) -> bool:
        """
        Valida que el servicio tenga mapeo a concepto de BD.
        
        Args:
            codigo_servicio: Código del servicio del archivo
            
        Returns:
            True si tiene mapeo, False en caso contrario
        """
        return MapeoConceptoServicio.obtener_concepto_bd(codigo_servicio) is not None
    
    @staticmethod
    def validar_divisa_soportada(codigo_divisa: int) -> bool:
        """
        Valida que la divisa esté soportada.
        
        Args:
            codigo_divisa: Código de divisa
            
        Returns:
            True si está soportada, False en caso contrario
        """
        return MapeoDivisa.es_divisa_valida(codigo_divisa)
    
    @staticmethod
    def validar_mapeos_criticos() -> Dict[str, bool]:
        """
        Valida que todos los mapeos críticos estén completos.
        
        Returns:
            Diccionario con resultados de validación
        """
        return {
            'servicios_mapeados': len(MapeoConceptoServicio.SERVICIO_TO_CONCEPTO) > 0,
            'divisas_mapeadas': len(MapeoDivisa.CODIGO_TO_DIVISA) > 0,
            'estados_definidos': len(EstadoServicio) > 0,
        }