"""
Data Transfer Objects para datos de transacción CEF (CefTransacciones).

Los DTOs son objetos inmutables que transportan datos entre capas,
sin lógica de negocio.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass(frozen=True)
class TransaccionDTO:
    """
    Data Transfer Object para datos de transacción CEF (tabla CefTransacciones).
    
    Representa los datos necesarios para insertar una transacción mediante
    el stored procedure AddServiceTransaction.
    
    Campos OBLIGATORIOS:
        - cod_sucursal: Código de la sucursal
        - fecha_registro: Fecha y hora de registro
        - usuario_registro_id: ID del usuario que registra
    """
    
    # ═══════════════════════════════════════════════════════════
    # CAMPOS OBLIGATORIOS
    # ═══════════════════════════════════════════════════════════
    
    # Ubicación
    cod_sucursal: int
    
    # Registro
    fecha_registro: datetime
    usuario_registro_id: str | None = None
        
    # ═══════════════════════════════════════════════════════════
    # CAMPOS OPCIONALES (con defaults)
    # ═══════════════════════════════════════════════════════════
    
    # Identificación de ruta y planilla
    cod_ruta: Optional[str] = None
    numero_planilla: int = 0
    
    # Divisa y tipo
    divisa: str = 'COP'
    tipo_transaccion: str = 'RC'
    
    # Mesa de conteo
    numero_mesa_conteo: Optional[int] = None
    
    # Cantidades declaradas
    cantidad_bolsas_declaradas: int = 0
    cantidad_sobres_declarados: int = 0
    cantidad_cheques_declarados: int = 0
    cantidad_documentos_declarados: int = 0
    
    # Valores declarados
    valor_billetes_declarado: Decimal = Decimal('0')
    valor_monedas_declarado: Decimal = Decimal('0')
    valor_documentos_declarado: Decimal = Decimal('0')
    valor_total_declarado: Decimal = Decimal('0')
    
    # Valores en letras
    valor_total_declarado_letras: Optional[str] = None
    valor_total_contado_letras: Optional[str] = None
    
    # Novedades
    novedad_informativa: Optional[str] = None
    
    # Flags
    es_custodia: bool = False
    es_punto_a_punto: bool = False
    
    # Estado
    estado_transaccion: str = 'RegistroTesoreria'  # Default estado inicial
    
    # IPs y responsables
    ip_registro: Optional[str] = None
    responsable_entrega_id: Optional[str] = None
    responsable_recibe_id: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════
    # VALIDACIONES POST-INIT
    # ═══════════════════════════════════════════════════════════
    
    def __post_init__(self):
        """Validaciones de integridad de datos"""
        # Validar cod_sucursal
        if self.cod_sucursal <= 0:
            raise ValueError("cod_sucursal debe ser mayor a 0")
        
        # Validar usuario_registro_id
        if not self.usuario_registro_id or not self.usuario_registro_id.strip():
            raise ValueError("usuario_registro_id no puede estar vacío")
        
        # Validar divisa (3 letras)
        if len(self.divisa) != 3 or not self.divisa.isalpha():
            raise ValueError(f"divisa debe ser 3 letras, recibido: '{self.divisa}'")
        
        # Validar tipo_transaccion
        tipos_validos = ('RC', 'PV')
        if self.tipo_transaccion not in tipos_validos:
            raise ValueError(
                f"tipo_transaccion inválido: '{self.tipo_transaccion}'. "
                f"Valores válidos: {tipos_validos}"
            )
        
        # Validar estado_transaccion
        estados_validos = (
            'RegistroTesoreria', 'EncoladoParaConteo', 'Conteo',
            'PendienteRevision', 'Aprobado', 'Rechazado', 'Cancelado',
            'ProvisionEnProceso', 'ListoParaEntrega', 'Entregado'
        )
        if self.estado_transaccion not in estados_validos:
            raise ValueError(
                f"estado_transaccion inválido: '{self.estado_transaccion}'. "
                f"Valores válidos: {estados_validos}"
            )
        
        # Validar valores no negativos
        if self.valor_billetes_declarado < 0:
            raise ValueError("valor_billetes_declarado no puede ser negativo")
        
        if self.valor_monedas_declarado < 0:
            raise ValueError("valor_monedas_declarado no puede ser negativo")
        
        if self.valor_documentos_declarado < 0:
            raise ValueError("valor_documentos_declarado no puede ser negativo")
        
        if self.valor_total_declarado < 0:
            raise ValueError("valor_total_declarado no puede ser negativo")
        
        # Validar cantidades no negativas
        if self.cantidad_bolsas_declaradas < 0:
            raise ValueError("cantidad_bolsas_declaradas no puede ser negativa")
        
        if self.cantidad_sobres_declarados < 0:
            raise ValueError("cantidad_sobres_declarados no puede ser negativa")
    
    # ═══════════════════════════════════════════════════════════
    # PROPIEDADES CALCULADAS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def valor_total_calculado(self) -> Decimal:
        """
        Calcula el valor total (billetes + monedas + documentos).
        
        Útil para validar coherencia con valor_total_declarado.
        """
        return (
            self.valor_billetes_declarado +
            self.valor_monedas_declarado +
            self.valor_documentos_declarado
        )
    
    @property
    def es_estado_inicial(self) -> bool:
        """Verifica si está en estado inicial (RegistroTesoreria)"""
        return self.estado_transaccion == 'RegistroTesoreria'
    
    @property
    def tiene_valores_declarados(self) -> bool:
        """Verifica si tiene valores declarados mayores a 0"""
        return self.valor_total_declarado > 0
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE CONSTRUCCIÓN (Factory Methods)
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def crear_para_provision(
        cls,
        cod_sucursal: int,
        valor_billetes: Decimal,
        valor_monedas: Decimal,
        divisa: str = 'COP',
        usuario_id: str = 'SYSTEM_TXT_PROCESSOR',
        **kwargs
    ) -> TransaccionDTO:
        """
        Factory method para crear un DTO de transacción para provisión.
        
        En provisiones, los valores SÍ se conocen de antemano.
        
        Args:
            cod_sucursal: Código de sucursal
            valor_billetes: Valor de billetes declarado
            valor_monedas: Valor de monedas declarado
            divisa: Divisa (default COP)
            usuario_id: ID del usuario que registra
            **kwargs: Campos opcionales adicionales
            
        Returns:
            TransaccionDTO configurado para provisión
        """
        valor_total = valor_billetes + valor_monedas
        
        return cls(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id=usuario_id,
            tipo_transaccion='PV',
            divisa=divisa,
            valor_billetes_declarado=valor_billetes,
            valor_monedas_declarado=valor_monedas,
            valor_total_declarado=valor_total,
            estado_transaccion='RegistroTesoreria',
            **kwargs
        )
    
    @classmethod
    def crear_para_recoleccion(
        cls,
        cod_sucursal: int,
        divisa: str = 'COP',
        usuario_id: str = 'SYSTEM_XML_PROCESSOR',
        **kwargs
    ) -> TransaccionDTO:
        """
        Factory method para crear un DTO de transacción para recolección.
        
        En recolecciones, los valores se desconocen hasta el conteo,
        por lo tanto se inicializan en 0.
        
        Args:
            cod_sucursal: Código de sucursal
            divisa: Divisa (default COP)
            usuario_id: ID del usuario que registra
            **kwargs: Campos opcionales adicionales
            
        Returns:
            TransaccionDTO configurado para recolección
        """
        return cls(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id=usuario_id,
            tipo_transaccion='RC',
            divisa=divisa,
            valor_billetes_declarado=Decimal('0'),  # Desconocido
            valor_monedas_declarado=Decimal('0'),   # Desconocido
            valor_total_declarado=Decimal('0'),     # Desconocido
            estado_transaccion='RegistroTesoreria',
            **kwargs
        )
    
    @classmethod
    def crear_desde_defaults(
        cls,
        cod_sucursal: int,
        usuario_id: str = 'SYSTEM',
        **kwargs
    ) -> TransaccionDTO:
        """
        Factory method para crear un DTO con valores por defecto.
        
        Args:
            cod_sucursal: Código de sucursal
            usuario_id: ID del usuario que registra
            **kwargs: Campos opcionales adicionales
            
        Returns:
            TransaccionDTO con defaults
        """
        return cls(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id=usuario_id,
            **kwargs
        )