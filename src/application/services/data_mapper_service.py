"""
Servicio de mapeo de datos (TXT/XML → DTOs para BD).

Este servicio es responsable de:
- Transformar datos crudos de archivos a DTOs estructurados
- Resolver códigos de BD (clientes, sucursales, puntos)
- Aplicar mapeos de dominio a infraestructura
- Calcular valores derivados (billetes, monedas, totales)
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date, time
from decimal import Decimal
import logging
import pandas as pd

from ..dto.servicio_dto import ServicioDTO
from ..dto.transaccion_dto import TransaccionDTO
from src.domain.value_objects.codigo_punto import CodigoPunto, CodigoCliente
from src.infrastructure.config.mapeos_bd import (
    MapeoConceptoServicio,
    MapeoDivisa,
    MapeoIndicadorTipo,
    MapeoEstadoInicial,
    ModalidadServicio,
    TipoTransaccion,
    ConversionHelper
)
from src.infrastructure.database.unit_of_work import UnitOfWork


logger = logging.getLogger(__name__)


class DataMapperService:
    """
    Servicio de mapeo de datos de archivos a DTOs de base de datos.
    
    Este servicio coordina:
    1. Resolución de códigos (clientes, sucursales, fondos)
    2. Aplicación de mapeos (servicios, divisas)
    3. Cálculo de valores (billetes, monedas)
    4. Construcción de DTOs válidos
    """
    
    def __init__(self, uow: UnitOfWork):
        """
        Inicializa el servicio con un Unit of Work.
        
        Args:
            uow: Unit of Work para acceso a repositorios
        """
        self._uow = uow
    
    # ═══════════════════════════════════════════════════════════
    # MAPEO DESDE TXT
    # ═══════════════════════════════════════════════════════════
    
    def mapear_desde_txt_tipo2(
        self,
        registro_tipo2: Dict[str, Any],
        nit_cliente: str,
        nombre_archivo: str
    ) -> Tuple[ServicioDTO, TransaccionDTO]:
        """
        Mapea un registro de TIPO 2 (TXT) a DTOs de servicio y transacción.
        
        Args:
            registro_tipo2: Diccionario con datos del registro TIPO 2
            nit_cliente: NIT del cliente (del TIPO 1)
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            Tupla (ServicioDTO, TransaccionDTO)
            
        Raises:
            ValueError: Si faltan datos críticos o no se pueden resolver
            
        Example:
            registro = {
                'CODIGO': '12345',
                'SERVICIO': '4',  # APROVISIONAMIENTO_DE_ATM_NIVEL_7
                'CODIGO PUNTO': '0033',
                'FECHA SERVICIO': '15052025',
                'DENOMINACION': 50000,
                'CANTIDAD': 100,
                'TIPO VALOR': '1',  # COP
                # ... más campos
            }
            servicio_dto, transaccion_dto = mapper.mapear_desde_txt_tipo2(
                registro, '900123456', 'archivo.txt'
            )
        """
        logger.info(f"Mapeando registro TXT TIPO 2: {registro_tipo2.get('CODIGO')}")
        
        # ────────────────────────────────────────────────────────
        # 1. RESOLVER CÓDIGO DE CLIENTE
        # ────────────────────────────────────────────────────────
        cod_cliente = self._obtener_cod_cliente_por_nit(nit_cliente)
        if not cod_cliente:
            raise ValueError(
                f"No se pudo resolver CodCliente para NIT: {nit_cliente}. "
                f"Verifique que el cliente existe en la BD."
            )
        
        logger.debug(f"Cliente resuelto: NIT {nit_cliente} → CodCliente {cod_cliente}")
        
        # ────────────────────────────────────────────────────────
        # 2. MAPEAR SERVICIO A CONCEPTO DE BD
        # ────────────────────────────────────────────────────────
        codigo_servicio_origen = int(registro_tipo2.get('SERVICIO', 0))
        cod_concepto = MapeoConceptoServicio.obtener_concepto_bd(codigo_servicio_origen)
        
        if not cod_concepto:
            raise ValueError(
                f"Servicio no mapeado: {codigo_servicio_origen}. "
                f"Servicios soportados: {list(MapeoConceptoServicio.SERVICIO_TO_CONCEPTO.keys())}"
            )
        
        es_provision = MapeoConceptoServicio.es_provision(codigo_servicio_origen)
        logger.debug(f"Servicio mapeado: {codigo_servicio_origen} → CodConcepto {cod_concepto} (Provisión: {es_provision})")
        
        # ────────────────────────────────────────────────────────
        # 3. OBTENER INFORMACIÓN DEL PUNTO DESTINO
        # ────────────────────────────────────────────────────────
        codigo_punto_destino = str(registro_tipo2.get('CODIGO PUNTO', '')).strip()
        if not codigo_punto_destino:
            raise ValueError("CODIGO PUNTO no puede estar vacío")
        
        punto_info = self._obtener_info_completa_punto(codigo_punto_destino, cod_cliente)
        if not punto_info:
            raise ValueError(
                f"Punto no encontrado: {codigo_punto_destino} (Cliente: {cod_cliente}). "
                f"Verifique que el punto existe y pertenece al cliente."
            )
        
        cod_sucursal = punto_info['cod_sucursal']
        cod_punto_origen = punto_info['cod_fondo'] or codigo_punto_destino  # Fallback
        
        logger.debug(f"Punto resuelto: {codigo_punto_destino} → Sucursal {cod_sucursal}, Fondo {cod_punto_origen}")
        
        # ────────────────────────────────────────────────────────
        # 4. PARSEAR FECHA Y HORA
        # ────────────────────────────────────────────────────────
        fecha_servicio_str = str(registro_tipo2.get('FECHA SERVICIO', '')).strip()
        if not fecha_servicio_str or len(fecha_servicio_str) != 8:
            raise ValueError(f"FECHA SERVICIO inválida: '{fecha_servicio_str}'. Debe ser DDMMYYYY (8 dígitos).")
        
        try:
            fecha_solicitud = datetime.strptime(fecha_servicio_str, '%d%m%Y').date()
        except ValueError as e:
            raise ValueError(f"Error parseando FECHA SERVICIO '{fecha_servicio_str}': {e}")
        
        # Hora por defecto: 00:00:00 (no viene en TXT)
        hora_solicitud = time(0, 0, 0)
        
        logger.debug(f"Fecha parseada: {fecha_solicitud} {hora_solicitud}")
        
        # ────────────────────────────────────────────────────────
        # 5. CALCULAR VALORES (BILLETES Y MONEDAS)
        # ────────────────────────────────────────────────────────
        valor_billete, valor_moneda = self._calcular_valores_desde_registro_txt(registro_tipo2)
        
        # Si es recolección, valores en 0 (se desconocen hasta conteo)
        if not es_provision:
            valor_billete = Decimal('0')
            valor_moneda = Decimal('0')
            logger.debug("Recolección detectada: valores establecidos en 0")
        else:
            logger.debug(f"Valores calculados: Billetes ${valor_billete}, Monedas ${valor_moneda}")
        
        # ────────────────────────────────────────────────────────
        # 6. LIMPIAR DIVISA
        # ────────────────────────────────────────────────────────
        codigo_divisa_str = str(registro_tipo2.get('TIPO VALOR', '1')).strip()
        try:
            codigo_divisa = int(codigo_divisa_str)
        except ValueError:
            logger.warning(f"TIPO VALOR inválido '{codigo_divisa_str}', usando COP por defecto")
            codigo_divisa = 1
        
        divisa_limpia = MapeoDivisa.limpiar_divisa(codigo_divisa)
        logger.debug(f"Divisa mapeada: {codigo_divisa} → {divisa_limpia}")
        
        # ────────────────────────────────────────────────────────
        # 7. DETERMINAR INDICADORES DE TIPO
        # ────────────────────────────────────────────────────────
        # Origen: Fondo (F) si es provisión, Punto (P) si es recolección
        es_fondo_origen = es_provision
        indicador_tipo_origen = MapeoIndicadorTipo.determinar_tipo_origen(
            cod_punto_origen, 
            es_fondo=es_fondo_origen
        )
        
        # Destino: siempre Punto (P)
        indicador_tipo_destino = MapeoIndicadorTipo.determinar_tipo_destino(codigo_punto_destino)
        
        # ────────────────────────────────────────────────────────
        # 8. CONSTRUIR SERVICIO DTO
        # ────────────────────────────────────────────────────────
        numero_pedido = str(registro_tipo2.get('CODIGO', '')).strip()
        if not numero_pedido:
            raise ValueError("CODIGO (número de pedido) no puede estar vacío")
        
        servicio_dto = ServicioDTO(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=cod_concepto,
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_punto_origen=cod_punto_origen,
            indicador_tipo_origen=indicador_tipo_origen,
            cod_punto_destino=codigo_punto_destino,
            indicador_tipo_destino=indicador_tipo_destino,
            fallido=False,
            valor_billete=valor_billete,
            valor_moneda=valor_moneda,
            valor_servicio=valor_billete + valor_moneda,
            modalidad_servicio=ModalidadServicio.obtener_modalidad_default(),
            archivo_detalle=nombre_archivo
        )
        
        # ────────────────────────────────────────────────────────
        # 9. CONSTRUIR TRANSACCIÓN DTO
        # ────────────────────────────────────────────────────────
        transaccion_dto = TransaccionDTO(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id='SYSTEM_TXT_PROCESSOR',
            tipo_transaccion=TipoTransaccion.obtener_tipo_default(),
            divisa=divisa_limpia,
            valor_billetes_declarado=valor_billete,
            valor_monedas_declarado=valor_moneda,
            valor_total_declarado=valor_billete + valor_moneda,
            estado_transaccion=MapeoEstadoInicial.obtener_estado_inicial_transaccion()
        )
        
        logger.info(f"Mapeo TXT completado exitosamente para pedido {numero_pedido}")
        return (servicio_dto, transaccion_dto)
    
    # ═══════════════════════════════════════════════════════════
    # MAPEO DESDE XML
    # ═══════════════════════════════════════════════════════════
    
    def mapear_desde_xml_order(
        self,
        order_data: Dict[str, Any],
        nombre_archivo: str
    ) -> Tuple[ServicioDTO, TransaccionDTO]:
        """
        Mapea un elemento 'order' (XML) a DTOs de servicio y transacción.
        
        Args:
            order_data: Diccionario con datos del order
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            Tupla (ServicioDTO, TransaccionDTO)
            
        Raises:
            ValueError: Si faltan datos críticos
            
        Example:
            order_data = {
                'id': 'ORD-12345',
                'deliveryDate': '2025-05-15T10:30:00',
                'orderDate': '2025-05-14T15:00:00',
                'entityReferenceID': 'SUC-0033',
                'primaryTransport': 'VATCO',
                'denominaciones': [
                    {'code': '50000AD', 'amount': 5000000},
                    # ...
                ]
            }
        """
        logger.info(f"Mapeando order XML: {order_data.get('id')}")
        
        # ────────────────────────────────────────────────────────
        # 1. EXTRAER Y LIMPIAR CÓDIGO DE PUNTO
        # ────────────────────────────────────────────────────────
        entity_ref = str(order_data.get('entityReferenceID', '')).strip()
        if not entity_ref:
            raise ValueError("entityReferenceID no puede estar vacío")
        
        # Limpiar formato "SUC-0033" → "0033"
        codigo_punto_destino = self._limpiar_codigo_punto_xml(entity_ref)
        
        # ────────────────────────────────────────────────────────
        # 2. RESOLVER CLIENTE DESDE PUNTO
        # ────────────────────────────────────────────────────────
        # En XML no viene NIT, debemos buscar por punto
        punto_info = self._obtener_info_completa_punto_sin_cliente(codigo_punto_destino)
        if not punto_info:
            raise ValueError(f"Punto no encontrado: {codigo_punto_destino}")
        
        cod_cliente = punto_info['cod_cliente']
        cod_sucursal = punto_info['cod_sucursal']
        cod_punto_origen = punto_info['cod_fondo'] or codigo_punto_destino
        
        logger.debug(f"Punto XML resuelto: {codigo_punto_destino} → Cliente {cod_cliente}, Sucursal {cod_sucursal}")
        
        # ────────────────────────────────────────────────────────
        # 3. PARSEAR FECHAS
        # ────────────────────────────────────────────────────────
        # deliveryDate: fecha de programación
        delivery_date_str = str(order_data.get('deliveryDate', '')).strip()
        fecha_programacion, hora_programacion = self._parsear_fecha_xml(delivery_date_str)
        
        # orderDate: fecha de solicitud
        order_date_str = str(order_data.get('orderDate', '')).strip()
        fecha_solicitud, hora_solicitud = self._parsear_fecha_xml(order_date_str)
        
        if not fecha_solicitud:
            raise ValueError("orderDate no puede estar vacío")
        
        logger.debug(f"Fechas XML: Solicitud {fecha_solicitud} {hora_solicitud}, Programación {fecha_programacion} {hora_programacion}")
        
        # ────────────────────────────────────────────────────────
        # 4. DETERMINAR CONCEPTO (PROVISION)
        # ────────────────────────────────────────────────────────
        # En XML, 'order' siempre es provisión
        # Determinar si es ATM o Oficinas según contexto (simplificado: usar ATM por defecto)
        cod_concepto = 3  # PROVISION ATM (puede refinarse con más lógica)
        
        # ────────────────────────────────────────────────────────
        # 5. CALCULAR VALORES DESDE DENOMINACIONES
        # ────────────────────────────────────────────────────────
        denominaciones = order_data.get('denominaciones', [])
        valor_billete, valor_moneda = self._calcular_valores_desde_denominaciones_xml(denominaciones)
        
        logger.debug(f"Valores XML calculados: Billetes ${valor_billete}, Monedas ${valor_moneda}")
        
        # ────────────────────────────────────────────────────────
        # 6. EXTRAER DIVISA (default COP)
        # ────────────────────────────────────────────────────────
        divisa = order_data.get('divisa', 'COP')
        if len(divisa) != 3:
            logger.warning(f"Divisa XML inválida '{divisa}', usando COP")
            divisa = 'COP'
        
        # ────────────────────────────────────────────────────────
        # 7. CONSTRUIR DTOs
        # ────────────────────────────────────────────────────────
        numero_pedido = str(order_data.get('id', '')).strip()
        if not numero_pedido:
            raise ValueError("ID del order no puede estar vacío")
        
        primary_transport = order_data.get('primaryTransport', '')
        observaciones = f"Transportadora: {primary_transport}" if primary_transport else None
        
        servicio_dto = ServicioDTO(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=cod_concepto,
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_punto_origen=cod_punto_origen,
            indicador_tipo_origen='F',  # Fondo
            cod_punto_destino=codigo_punto_destino,
            indicador_tipo_destino='P',  # Punto
            fallido=False,
            valor_billete=valor_billete,
            valor_moneda=valor_moneda,
            valor_servicio=valor_billete + valor_moneda,
            fecha_programacion=fecha_programacion,
            hora_programacion=hora_programacion,
            modalidad_servicio=ModalidadServicio.obtener_modalidad_default(),
            observaciones=observaciones,
            archivo_detalle=nombre_archivo
        )
        
        transaccion_dto = TransaccionDTO(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id='SYSTEM_XML_PROCESSOR',
            tipo_transaccion=TipoTransaccion.obtener_tipo_default(),
            divisa=divisa,
            valor_billetes_declarado=valor_billete,
            valor_monedas_declarado=valor_moneda,
            valor_total_declarado=valor_billete + valor_moneda,
            estado_transaccion=MapeoEstadoInicial.obtener_estado_inicial_transaccion()
        )
        
        logger.info(f"Mapeo XML order completado para pedido {numero_pedido}")
        return (servicio_dto, transaccion_dto)
    
    def mapear_desde_xml_remit(
        self,
        remit_data: Dict[str, Any],
        nombre_archivo: str
    ) -> Tuple[ServicioDTO, TransaccionDTO]:
        """
        Mapea un elemento 'remit' (XML) a DTOs de servicio y transacción.
        
        Remit = RECOLECCIÓN, valores en 0 (desconocidos hasta conteo).
        """
        logger.info(f"Mapeando remit XML: {remit_data.get('id')}")
        
        # Similar a order pero con CodConcepto = 1 (RECOLECCION)
        # y valores en 0
        
        entity_ref = str(remit_data.get('entityReferenceID', '')).strip()
        codigo_punto_origen = self._limpiar_codigo_punto_xml(entity_ref)
        
        punto_info = self._obtener_info_completa_punto_sin_cliente(codigo_punto_origen)
        if not punto_info:
            raise ValueError(f"Punto no encontrado: {codigo_punto_origen}")
        
        cod_cliente = punto_info['cod_cliente']
        cod_sucursal = punto_info['cod_sucursal']
        cod_punto_destino = punto_info['cod_fondo'] or codigo_punto_origen
        
        pickup_date_str = str(remit_data.get('pickupDate', '')).strip()
        fecha_solicitud, hora_solicitud = self._parsear_fecha_xml(pickup_date_str)
        
        if not fecha_solicitud:
            raise ValueError("pickupDate no puede estar vacío")
        
        numero_pedido = str(remit_data.get('id', '')).strip()
        if not numero_pedido:
            raise ValueError("ID del remit no puede estar vacío")
        
        divisa = remit_data.get('divisa', 'COP')
        
        servicio_dto = ServicioDTO(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=1,  # RECOLECCION OFICINAS
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_punto_origen=codigo_punto_origen,
            indicador_tipo_origen='P',  # Punto
            cod_punto_destino=cod_punto_destino,
            indicador_tipo_destino='F',  # Fondo
            fallido=False,
            valor_billete=Decimal('0'),  # Desconocido
            valor_moneda=Decimal('0'),  # Desconocido
            valor_servicio=Decimal('0'),  # Desconocido
            modalidad_servicio=ModalidadServicio.obtener_modalidad_default(),
            archivo_detalle=nombre_archivo
        )
        
        transaccion_dto = TransaccionDTO(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id='SYSTEM_XML_PROCESSOR',
            tipo_transaccion=TipoTransaccion.obtener_tipo_default(),
            divisa=divisa,
            valor_billetes_declarado=Decimal('0'),
            valor_monedas_declarado=Decimal('0'),
            valor_total_declarado=Decimal('0'),
            estado_transaccion=MapeoEstadoInicial.obtener_estado_inicial_transaccion()
        )
        
        logger.info(f"Mapeo XML remit completado para pedido {numero_pedido}")
        return (servicio_dto, transaccion_dto)
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES PRIVADOS
    # ═══════════════════════════════════════════════════════════
    
    def _obtener_cod_cliente_por_nit(self, nit: str) -> Optional[int]:
        """Obtiene el CodCliente desde el NIT usando el repositorio"""
        try:
            cliente = self._uow.clientes.obtener_por_nit(nit)
            return int(cliente.codigo) if cliente else None
        except Exception as e:
            logger.error(f"Error obteniendo cliente por NIT '{nit}': {e}", exc_info=True)
            return None
    
    def _obtener_info_completa_punto(
        self,
        codigo_punto: str,
        cod_cliente: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene información completa del punto (sucursal, fondo).
        
        Returns:
            Dict con: cod_sucursal, cod_fondo, nombre_punto
        """
        try:
            codigo_punto_vo = CodigoPunto(valor=codigo_punto)
            punto = self._uow.puntos.obtener_por_codigo(codigo_punto_vo)
            
            if not punto:
                return None
            
            cod_fondo = self._obtener_fondo_de_punto(codigo_punto, cod_cliente)
            
            return {
                'cod_sucursal': int(punto.sucursal.codigo),
                'cod_fondo': cod_fondo,
                'nombre_punto': punto.nombre
            }
        except Exception as e:
            logger.error(f"Error obteniendo info del punto '{codigo_punto}': {e}", exc_info=True)
            return None
    
    def _obtener_info_completa_punto_sin_cliente(
        self,
        codigo_punto: str
    ) -> Optional[Dict[str, Any]]:
        """Obtiene info del punto sin saber el cliente de antemano"""
        try:
            codigo_punto_vo = CodigoPunto(valor=codigo_punto)
            punto = self._uow.puntos.obtener_por_codigo(codigo_punto_vo)
            
            if not punto:
                return None
            
            cod_cliente = int(punto.cliente.codigo)
            cod_fondo = self._obtener_fondo_de_punto(codigo_punto, cod_cliente)
            
            return {
                'cod_cliente': cod_cliente,
                'cod_sucursal': int(punto.sucursal.codigo),
                'cod_fondo': cod_fondo,
                'nombre_punto': punto.nombre
            }
        except Exception as e:
            logger.error(f"Error obteniendo info del punto '{codigo_punto}': {e}", exc_info=True)
            return None
    
    def _obtener_fondo_de_punto(
        self,
        codigo_punto: str,
        cod_cliente: int
    ) -> Optional[str]:
        """Obtiene el código de fondo del punto mediante query SQL"""
        query = """
            SELECT CodigoFondo 
            FROM AdmPuntos 
            WHERE CodigoPunto = ? AND CodigoCliente = ?
        """
        
        try:
            result = self._uow._connection.execute_scalar(query, [codigo_punto, cod_cliente])
            return str(result) if result else None
        except Exception as e:
            logger.error(f"Error obteniendo fondo del punto '{codigo_punto}': {e}", exc_info=True)
            return None
    
    def _calcular_valores_desde_registro_txt(
        self,
        registro: Dict[str, Any]
    ) -> Tuple[Decimal, Decimal]:
        """
        Calcula billetes y monedas desde un registro TXT.
        
        Returns:
            Tupla (valor_billete, valor_moneda)
        """
        try:
            denominacion = Decimal(str(registro.get('DENOMINACION', 0)))
            cantidad = Decimal(str(registro.get('CANTIDAD', 0)))
            
            valor_total = denominacion * cantidad
            
            # Si denominación >= 1000, es billete
            tipo = ConversionHelper.determinar_tipo_denominacion(int(denominacion))
            
            if tipo == 'BILLETE':
                return (valor_total, Decimal('0'))
            else:
                return (Decimal('0'), valor_total)
        except Exception as e:
            logger.error(f"Error calculando valores TXT: {e}", exc_info=True)
            return (Decimal('0'), Decimal('0'))
    
    def _calcular_valores_desde_denominaciones_xml(
        self,
        denominaciones: list
    ) -> Tuple[Decimal, Decimal]:
        """Calcula billetes y monedas desde lista de denominaciones XML"""
        valor_billetes = Decimal('0')
        valor_monedas = Decimal('0')
        
        for denom in denominaciones:
            try:
                code = str(denom.get('code', ''))
                amount = Decimal(str(denom.get('amount', 0)))
                
                # Extraer valor numérico del code (ej: "50000AD" → 50000)
                valor_denom = int(''.join(filter(str.isdigit, code)))
                
                if valor_denom >= 1000:
                    valor_billetes += amount
                else:
                    valor_monedas += amount
            except Exception as e:
                logger.warning(f"Error procesando denominación XML {denom}: {e}")
                continue
        
        return (valor_billetes, valor_monedas)
    
    def _limpiar_codigo_punto_xml(self, entity_ref: str) -> str:
        """
        Limpia el código de punto del formato XML.
        
        "SUC-0033" → "0033"
        "47-SUC-0033" → "0033"
        """
        if '-SUC-' in entity_ref:
            return entity_ref.split('-SUC-')[-1]
        elif entity_ref.startswith('SUC-'):
            return entity_ref[4:]
        else:
            return entity_ref
    
    def _parsear_fecha_xml(
        self,
        fecha_str: str
    ) -> Tuple[Optional[date], Optional[time]]:
        """
        Parsea fecha XML en formato ISO.
        
        "2025-05-15T10:30:00" → (date(2025,5,15), time(10,30,0))
        "2025-05-15" → (date(2025,5,15), time(0,0,0))
        """
        if not fecha_str:
            return (None, None)
        
        try:
            # Intentar con timestamp completo
            if 'T' in fecha_str:
                dt = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                return (dt.date(), dt.time())
            else:
                # Solo fecha
                dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                return (dt.date(), time(0, 0, 0))
        except Exception as e:
            logger.warning(f"Error parseando fecha XML '{fecha_str}': {e}")