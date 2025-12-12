"""
Data Transfer Objects para datos de servicio (CgsServicios).

Los DTOs son objetos inmutables que transportan datos entre capas,
sin lógica de negocio.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from decimal import Decimal


@dataclass
class ServicioDTO:
    """
    Data Transfer Object para datos de servicio (tabla CgsServicios).
    
    Representa los datos necesarios para insertar un servicio mediante
    el stored procedure AddServiceTransaction.
    
    Campos OBLIGATORIOS:
        - numero_pedido: ID único de la solicitud
        - cod_cliente: Código del cliente
        - cod_sucursal: Código de la sucursal
        - fecha_solicitud: Fecha de la solicitud
        - hora_solicitud: Hora de la solicitud
        - cod_concepto: Código del concepto de servicio
        - cod_estado: Estado del servicio (0-7)
        - cod_punto_origen: Código del punto origen
        - indicador_tipo_origen: Tipo de entidad origen (C/P/F)
        - cod_punto_destino: Código del punto destino
        - indicador_tipo_destino: Tipo de entidad destino (C/P/F)
        - fallido: Flag de fallido (siempre False al crear)
    """
    
    # ═══════════════════════════════════════════════════════════
    # CAMPOS OBLIGATORIOS
    # ═══════════════════════════════════════════════════════════
    
    # Identificación
    numero_pedido: str
    
    # Cliente y Ubicación
    cod_cliente: int
    cod_sucursal: int
    
    # Servicio
    cod_concepto: int
    tipo_traslado: str
    fecha_solicitud: date
    hora_solicitud: time
    
    # Estado
    cod_estado: int  # 0=Solicitado, 1=Confirmado, etc.
    
    # Puntos (Origen y Destino)
    cod_punto_origen: str
    indicador_tipo_origen: str  # 'C' Cliente, 'P' Punto, 'F' Fondo
    cod_punto_destino: str
    indicador_tipo_destino: str  # 'C' Cliente, 'P' Punto, 'F' Fondo
    
    # Control
    fallido: bool  # Siempre False al crear
    
    # ═══════════════════════════════════════════════════════════
    # CAMPOS OPCIONALES (con defaults)
    # ═══════════════════════════════════════════════════════════
    
    # Valores monetarios
    valor_billete: Decimal = Decimal('0')
    valor_moneda: Decimal = Decimal('0')
    valor_servicio: Decimal = Decimal('0')
    
    # Información adicional del cliente
    cod_os_cliente: Optional[str] = None
    
    # Cliente origen (para traslados)
    cod_cliente_origen: Optional[int] = None
    
    # Cliente destino (para traslados)
    cod_cliente_destino: Optional[int] = None
    
    # Fechas de aceptación
    fecha_aceptacion: Optional[date] = None
    hora_aceptacion: Optional[time] = None
    
    # Fechas de programación
    fecha_programacion: Optional[date] = None
    hora_programacion: Optional[time] = None
    
    # Fechas de atención
    fecha_atencion_inicial: Optional[date] = None
    hora_atencion_inicial: Optional[time] = None
    fecha_atencion_final: Optional[date] = None
    hora_atencion_final: Optional[time] = None
    
    # Fechas de cancelación
    fecha_cancelacion: Optional[date] = None
    hora_cancelacion: Optional[time] = None
    
    # Fechas de rechazo
    fecha_rechazo: Optional[date] = None
    hora_rechazo: Optional[time] = None
    
    # Datos de fallido (si aplica)
    responsable_fallido: Optional[str] = None
    razon_fallido: Optional[str] = None
    
    # Datos de cancelación (si aplica)
    persona_cancelacion: Optional[str] = None
    operador_cancelacion: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    
    # Modalidad de servicio
    modalidad_servicio: str = '2'  # Default: '2' = A PEDIDO
    
    # Observaciones
    observaciones: Optional[str] = None
    
    # Clave (si aplica)
    clave: Optional[int] = None
    
    # Datos del operador CGS
    operador_cgs_id: Optional[str] = None
    sucursal_cgs: Optional[str] = None
    ip_operador: Optional[str] = None
    
    # Kits y bolsas
    numero_kits_cambio: Optional[int] = None
    numero_bolsas_moneda: Optional[int] = None
    
    # Archivo de origen
    archivo_detalle: Optional[str] = None

    usuario_registro_id: str | None = None
    
    # ═══════════════════════════════════════════════════════════
    # VALIDACIONES POST-INIT
    # ═══════════════════════════════════════════════════════════
    
    def __post_init__(self):
        """Validaciones de integridad de datos"""
        # Validar campos obligatorios
        if not self.numero_pedido or not self.numero_pedido.strip():
            raise ValueError("numero_pedido no puede estar vacío")
        
        if self.cod_cliente <= 0:
            raise ValueError("cod_cliente debe ser mayor a 0")
        
        if self.cod_sucursal <= 0:
            raise ValueError("cod_sucursal debe ser mayor a 0")
        
        if self.cod_concepto <= 0:
            raise ValueError("cod_concepto debe ser mayor a 0")
        
        if not self.cod_punto_origen or not self.cod_punto_origen.strip():
            raise ValueError("cod_punto_origen no puede estar vacío")
        
        if not self.cod_punto_destino or not self.cod_punto_destino.strip():
            raise ValueError("cod_punto_destino no puede estar vacío")
        
        # Validar indicadores de tipo
        if self.indicador_tipo_origen not in ('C', 'P', 'F'):
            raise ValueError(f"indicador_tipo_origen inválido: {self.indicador_tipo_origen}")
        
        if self.indicador_tipo_destino not in ('C', 'P', 'F'):
            raise ValueError(f"indicador_tipo_destino inválido: {self.indicador_tipo_destino}")
        
        # Validar estado
        if not (0 <= self.cod_estado <= 7):
            raise ValueError(f"cod_estado debe estar entre 0 y 7, recibido: {self.cod_estado}")
        
        # Validar valores monetarios no negativos
        if self.valor_billete < 0:
            raise ValueError("valor_billete no puede ser negativo")
        
        if self.valor_moneda < 0:
            raise ValueError("valor_moneda no puede ser negativo")
        
        if self.valor_servicio < 0:
            raise ValueError("valor_servicio no puede ser negativo")
    
    # ═══════════════════════════════════════════════════════════
    # PROPIEDADES CALCULADAS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def valor_total(self) -> Decimal:
        """Calcula el valor total (billete + moneda)"""
        return self.valor_billete + self.valor_moneda
    
    @property
    def es_provision(self) -> bool:
        """Verifica si es un servicio de provisión"""
        # CodConcepto: 2=PROVISION OFICINAS, 3=PROVISION ATM
        return self.cod_concepto in (2, 3)
    
    @property
    def es_recoleccion(self) -> bool:
        """Verifica si es un servicio de recolección"""
        # CodConcepto: 1=RECOLECCION OFICINAS
        return self.cod_concepto == 1
    
    @property
    def tiene_programacion(self) -> bool:
        """Verifica si tiene fecha de programación"""
        return self.fecha_programacion is not None
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE CONSTRUCCIÓN (Factory Methods)
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def crear_provision(
        cls,
        numero_pedido: str,
        cod_cliente: int,
        cod_sucursal: int,
        cod_concepto: int,
        tipo_traslado: str,
        fecha_solicitud: date,
        hora_solicitud: time,
        cod_punto_origen: str,
        cod_punto_destino: str,
        valor_billete: Decimal,
        valor_moneda: Decimal,
        **kwargs
    ) -> ServicioDTO:
        """
        Factory method para crear un DTO de provisión.
        
        Args:
            numero_pedido: ID único del pedido
            cod_cliente: Código del cliente
            cod_sucursal: Código de sucursal
            cod_concepto: Código de concepto (2 o 3)
            fecha_solicitud: Fecha de solicitud
            hora_solicitud: Hora de solicitud
            cod_punto_origen: Punto origen (fondo)
            cod_punto_destino: Punto destino
            valor_billete: Valor de billetes
            valor_moneda: Valor de monedas
            **kwargs: Campos opcionales adicionales
            
        Returns:
            ServicioDTO configurado para provisión
        """
        return cls(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=cod_concepto,
            tipo_traslado='N',
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=0,  # Solicitado
            cod_punto_origen=cod_punto_origen,
            indicador_tipo_origen='F',  # Fondo
            cod_punto_destino=cod_punto_destino,
            indicador_tipo_destino='P',  # Punto
            fallido=False,
            valor_billete=valor_billete,
            valor_moneda=valor_moneda,
            valor_servicio=valor_billete + valor_moneda,
            **kwargs
        )
    
    @classmethod
    def crear_recoleccion(
        cls,
        numero_pedido: str,
        cod_cliente: int,
        cod_sucursal: int,
        fecha_solicitud: date,
        hora_solicitud: time,
        cod_punto_origen: str,
        cod_punto_destino: str,
        **kwargs
    ) -> ServicioDTO:
        """
        Factory method para crear un DTO de recolección.
        
        En recolecciones, los valores se desconocen hasta el conteo,
        por lo tanto se inicializan en 0.
        
        Args:
            numero_pedido: ID único del pedido
            cod_cliente: Código del cliente
            cod_sucursal: Código de sucursal
            fecha_solicitud: Fecha de solicitud
            hora_solicitud: Hora de solicitud
            cod_punto_origen: Punto origen
            cod_punto_destino: Punto destino (fondo)
            **kwargs: Campos opcionales adicionales
            
        Returns:
            ServicioDTO configurado para recolección
        """
        return cls(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=1,  # RECOLECCION OFICINAS
            tipo_traslado='N',
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=0,  # Solicitado
            cod_punto_origen=cod_punto_origen,
            indicador_tipo_origen='P',  # Punto
            cod_punto_destino=cod_punto_destino,
            indicador_tipo_destino='F',  # Fondo
            fallido=False,
            valor_billete=Decimal('0'),  # Desconocido hasta conteo
            valor_moneda=Decimal('0'),   # Desconocido hasta conteo
            valor_servicio=Decimal('0'), # Desconocido hasta conteo
            **kwargs
        )