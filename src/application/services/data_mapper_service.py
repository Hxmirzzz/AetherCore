"""
Servicio de mapeo de datos (TXT/XML → DTOs para BD).

CORRECCIÓN: Ahora usa ConnectionManager para acceder a AMBAS BDs.
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date, time
from decimal import Decimal
import logging

from ..dto.servicio_dto import ServicioDTO
from ..dto.transaccion_dto import TransaccionDTO
from src.domain.value_objects.codigo_punto import CodigoPunto
from src.infrastructure.config.mapeos_bd import (
    MapeoConceptoServicio,
    MapeoDivisa,
    MapeoIndicadorTipo,
    MapeoEstadoInicial,
    ModalidadServicio,
    TipoTransaccion,
    ConversionHelper
)
from src.infrastructure.database.connection_manager import ConnectionManager


logger = logging.getLogger(__name__)


class DataMapperService:
    """
    Servicio de mapeo de datos de archivos a DTOs de base de datos.
    
    CORRECCIÓN: Ahora recibe ConnectionManager en lugar de UnitOfWork.
    Esto le permite consultar la BD de prod y preparar DTOs para insertar en test.
    """
    
    def __init__(self, conn_manager: ConnectionManager):
        """
        Inicializa el servicio con un ConnectionManager.
        
        Args:
            conn_manager: Gestor de conexiones (lectura + escritura)
        """
        self._conn_manager = conn_manager
        self._conn_read = conn_manager.get_read_connection()
    
    # ═══════════════════════════════════════════════════════════
    # MAPEO DESDE TXT
    # ═══════════════════════════════════════════════════════════
    
    def mapear_desde_txt_tipo2(
        self,
        registro_tipo2: Dict[str, Any],
        nit_cliente: str,
        nombre_archivo: str,
        fecha_generacion_txt: date
    ) -> Tuple[ServicioDTO, TransaccionDTO]:
        """
        Mapea un registro de TIPO 2 (TXT) a DTOs de servicio y transacción.
        
        PROCESO:
        1. Consultar cliente por NIT (BD prod)
        2. Mapear servicio a concepto
        3. Obtener info del punto (BD prod)
        4. Parsear fecha y hora
        5. Calcular valores
        6. Construir DTOs
        """
        logger.info(f"Mapeando registro TXT TIPO 2: {registro_tipo2.get('CODIGO')}")
        # logger.info(f"Data: {registro_tipo2}")
        
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
        servicio_raw = str(registro_tipo2.get('SERVICIO', '0')).strip()

        try:
            if ' - ' in servicio_raw:
                codigo_servicio_origen = int(servicio_raw.split(' - ')[0])
            else:
                codigo_servicio_origen = int(servicio_raw)
        except:
            raise ValueError(f"Error en columna SERVICIO. No se pudo obtener el código numérico de '{servicio_raw}'. Error: {e}")

        cod_concepto = 3

        es_provision = MapeoConceptoServicio.es_provision(codigo_servicio_origen)
        logger.debug(f"Servicio mapeado: {codigo_servicio_origen} → CodConcepto {cod_concepto} (Provisión: {es_provision})")
        
        # ────────────────────────────────────────────────────────
        # 3. OBTENER INFORMACIÓN DEL PUNTO DESTINO
        # ────────────────────────────────────────────────────────
        codigo_punto_cliente_destino = str(registro_tipo2.get('CODIGO PUNTO', '')).strip() # Nombre más claro
        if not codigo_punto_cliente_destino:
            raise ValueError("CODIGO PUNTO no puede estar vacío")
        
        punto_info = self._obtener_info_completa_punto(codigo_punto_cliente_destino, cod_cliente)        
        if not punto_info:
            raise ValueError(
                f"Punto no encontrado: {codigo_punto_destino} (Cliente: {cod_cliente}). "
                f"Verifique que el punto existe y pertenece al cliente."
            )
        
        cod_sucursal = punto_info['cod_sucursal']
        cod_punto_pk_destino = punto_info['cod_punto_pk']
        cod_fondo_origen = punto_info['cod_fondo']
        cod_punto_pk_origen = punto_info['cod_fondo'] or cod_punto_pk_destino

        logger.debug(
            f"Punto resuelto: Cliente Punto {codigo_punto_cliente_destino} "
            f"→ Sucursal {cod_sucursal}, PK Destino {cod_punto_pk_destino}, "
            f"PK Origen {cod_punto_pk_origen}"
        )
        
        # ────────────────────────────────────────────────────────
        # 4. PARSEAR FECHA Y HORA
        # ────────────────────────────────────────────────────────
        fecha_solicitud = fecha_generacion_txt
        hora_solicitud = time(0, 0, 0)
        
        # B) FECHA DE PROGRAMACIÓN (Viene del registro Tipo 2 - 'FECHA SERVICIO')
        fecha_programacion_str = str(registro_tipo2.get('FECHA SERVICIO', '')).strip()
        
        if not fecha_programacion_str:
            # Esto puede ser una advertencia, pero por ahora lo dejamos como error
            # para asegurar la integridad de los datos
            raise ValueError(f"FECHA SERVICIO inválida: '{fecha_programacion_str}'.") 

        formato_con_barras = '%d/%m/%Y'
        if len(fecha_programacion_str) == 8:
            formato_a_usar = '%d%m%Y'
        elif len(fecha_programacion_str) == 10:
            formato_a_usar = formato_con_barras
        else:
            raise ValueError(f"FECHA SERVICIO inválida: '{fecha_programacion_str}'. Formato inesperado.")

        try:
            fecha_programacion: Optional[date] = datetime.strptime(fecha_programacion_str, formato_a_usar).date()
        except ValueError as e:
            raise ValueError(f"Error parseando FECHA SERVICIO '{fecha_programacion_str}': {e}")
        
        hora_programacion = time(0, 0, 0)
        
        # ────────────────────────────────────────────────────────
        # 5. CALCULAR VALORES (BILLETES Y MONEDAS)
        # ────────────────────────────────────────────────────────
        valor_billete, valor_moneda = self._calcular_valores_desde_registro_txt(registro_tipo2)

        logger.info(f"Billete: {valor_billete} Moneda: {valor_moneda}")
        
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
        es_fondo_origen = cod_fondo_origen is not None
        indicador_tipo_origen = MapeoIndicadorTipo.determinar_tipo_origen(
            cod_punto_pk_origen,
            es_fondo=es_fondo_origen
        )
        indicador_tipo_destino = MapeoIndicadorTipo.determinar_tipo_destino(cod_punto_pk_destino)
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
            tipo_traslado='N',
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            fecha_programacion=fecha_programacion,
            hora_programacion=hora_programacion,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_cliente_origen=cod_cliente,
            cod_punto_origen=cod_punto_pk_origen,
            indicador_tipo_origen=indicador_tipo_origen,
            cod_cliente_destino=cod_cliente,
            cod_punto_destino=cod_punto_pk_destino,
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
            usuario_registro_id='e5926e18-33b1-468c-a979-e4e839a86f30',
            tipo_transaccion=TipoTransaccion.PROVISION_OFICINA,
            divisa=divisa_limpia,
            valor_billetes_declarado=valor_billete,
            valor_monedas_declarado=valor_moneda,
            valor_total_declarado=valor_billete + valor_moneda,
            estado_transaccion=MapeoEstadoInicial.obtener_estado_inicial_transaccion()
        )
        
        logger.info(f"Mapeo TXT completado exitosamente para pedido {numero_pedido}")
        return (servicio_dto, transaccion_dto)
    
    def mapear_desde_xml_order(
        self,
        order_data: Dict[str, Any],
        nombre_archivo: str,
        codigo_cliente_xml: Optional[str] = None
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
        # 1. EXTRAER CÓDIGOS DEL XML
        # ────────────────────────────────────────────────────────
        entity_ref = str(order_data.get('entityReferenceID', '')).strip()
        if not entity_ref:
            raise ValueError("entityReferenceID no puede estar vacío")
        
        if codigo_cliente_xml is None:
            partes = entity_ref.replace('-SUC-', '-').split('-')
            if len(partes) >= 2:
                codigo_cliente_xml = partes[0]
                logger.debug(f"Extraído CC Code del XML: '{codigo_cliente_xml}'")
        
        codigo_punto_destino = self._limpiar_codigo_punto_xml(entity_ref)
        
        # ────────────────────────────────────────────────────────
        # 2. RESOLVER CLIENTE DESDE PUNTO (CON VERSIÓN CORREGIDA)
        # ────────────────────────────────────────────────────────
        punto_info = self._obtener_info_completa_punto_sin_cliente(
            codigo_punto_destino, 
            codigo_cliente_xml
        )
        
        if not punto_info:
            raise ValueError(
                f"Punto no encontrado: XML='{entity_ref}', "
                f"CC Code='{codigo_cliente_xml}', "
                f"Punto limpio='{codigo_punto_destino}'"
            )
        
        cod_cliente = punto_info['cod_cliente']
        cod_sucursal = punto_info['cod_sucursal']
        codigo_punto_pk = punto_info.get('cod_punto_bd', codigo_punto_destino)
        cod_punto_origen = punto_info['cod_fondo'] or codigo_punto_pk
        
        logger.info(
            f"✅ Punto resuelto correctamente: "
            f"XML '{entity_ref}' -> BD Cliente '{cod_cliente}', Sucursal '{cod_sucursal}'"
        )
        
        # ────────────────────────────────────────────────────────
        # 3. PARSEAR FECHAS
        # ────────────────────────────────────────────────────────
        delivery_date_str = str(order_data.get('deliveryDate', '')).strip()
        fecha_programacion, hora_programacion = self._parsear_fecha_xml(delivery_date_str)
        
        order_date_str = str(order_data.get('orderDate', '')).strip()
        fecha_solicitud, hora_solicitud = self._parsear_fecha_xml(order_date_str)
        
        if not fecha_solicitud:
            raise ValueError("orderDate no puede estar vacío")
        
        logger.debug(f"Fechas XML: Solicitud {fecha_solicitud} {hora_solicitud}, Programación {fecha_programacion} {hora_programacion}")
        
        # ────────────────────────────────────────────────────────
        # 4. DETERMINAR CONCEPTO (PROVISION)
        # ────────────────────────────────────────────────────────
        cod_concepto = 2
        
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
            tipo_traslado='N',
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_cliente_origen=cod_cliente,
            cod_punto_origen=cod_punto_origen,
            indicador_tipo_origen='F',  # Fondo
            cod_cliente_destino=cod_cliente,
            cod_punto_destino=codigo_punto_pk,
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
            usuario_registro_id='e5926e18-33b1-468c-a979-e4e839a86f30',
            tipo_transaccion=TipoTransaccion.PROVISION_OFICINA,
            divisa=divisa,
            valor_billetes_declarado=valor_billete,
            valor_monedas_declarado=valor_moneda,
            valor_total_declarado=valor_billete + valor_moneda,
            estado_transaccion=MapeoEstadoInicial.PROVISION_EN_PROCESO
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
        
        # ────────────────────────────────────────────────────────
        # 1. EXTRAER CÓDIGOS DEL XML (igual que en order)
        # ────────────────────────────────────────────────────────
        entity_ref = str(remit_data.get('entityReferenceID', '')).strip()
        if not entity_ref:
            raise ValueError("entityReferenceID no puede estar vacío")
        
        # Extraer código de cliente del entity_ref (igual que en order)
        codigo_cliente_xml = None
        partes = entity_ref.replace('-SUC-', '-').split('-')
        if len(partes) >= 2:
            codigo_cliente_xml = partes[0]  # Primera parte es el CC Code
            logger.debug(f"Extraído CC Code del XML: '{codigo_cliente_xml}'")
        
        codigo_punto_origen = self._limpiar_codigo_punto_xml(entity_ref)
        
        # ────────────────────────────────────────────────────────
        # 2. RESOLVER PUNTO (AHORA CON codigo_cliente_xml)
        # ────────────────────────────────────────────────────────
        punto_info = self._obtener_info_completa_punto_sin_cliente(
            codigo_punto_origen,
            codigo_cliente_xml
        )
        
        if not punto_info:
            raise ValueError(
                f"Punto no encontrado: XML='{entity_ref}', "
                f"CC Code='{codigo_cliente_xml}', "
                f"Punto limpio='{codigo_punto_origen}'"
            )
        
        cod_cliente = punto_info['cod_cliente']
        cod_sucursal = punto_info['cod_sucursal']
        codigo_punto_pk = punto_info.get('cod_punto_bd', codigo_punto_origen)
        cod_punto_destino = punto_info['cod_fondo'] or codigo_punto_pk
        
        logger.info(
            f"✅ Punto remit resuelto: "
            f"XML '{entity_ref}' -> BD Cliente '{cod_cliente}', Sucursal '{cod_sucursal}'"
        )
        
        # ────────────────────────────────────────────────────────
        # 3. PARSEAR FECHA
        # ────────────────────────────────────────────────────────
        pickup_date_str = str(remit_data.get('pickupDate', '')).strip()
        fecha_solicitud, hora_solicitud = self._parsear_fecha_xml(pickup_date_str)
        
        # AGREGAR ESTO: Para que la programación no sea NULL
        delivery_date_str = str(remit_data.get('deliveryDate', '')).strip()
        fecha_programacion, hora_programacion = self._parsear_fecha_xml(delivery_date_str)
        
        if not fecha_solicitud:
            raise ValueError("pickupDate no puede estar vacío")
        
        # ────────────────────────────────────────────────────────
        # 4. CONSTRUIR DTOs
        # ────────────────────────────────────────────────────────
        numero_pedido = str(remit_data.get('id', '')).strip()
        if not numero_pedido:
            raise ValueError("ID del remit no puede estar vacío")
        
        divisa = remit_data.get('divisa', 'COP')
        primary_transport = remit_data.get('primaryTransport', '')
        observaciones = f"Transportadora: {primary_transport}" if primary_transport else None
        
        servicio_dto = ServicioDTO(
            numero_pedido=numero_pedido,
            cod_cliente=cod_cliente,
            cod_sucursal=cod_sucursal,
            cod_concepto=1,  # RECOLECCION OFICINAS
            tipo_traslado='N',
            fecha_solicitud=fecha_solicitud,
            hora_solicitud=hora_solicitud,
            fecha_programacion=fecha_programacion,
            hora_programacion=hora_programacion,
            cod_estado=MapeoEstadoInicial.obtener_estado_inicial_servicio(),
            cod_cliente_origen=cod_cliente,
            cod_punto_origen=codigo_punto_pk,
            indicador_tipo_origen='P',  # Punto
            cod_cliente_destino=cod_cliente,
            cod_punto_destino=cod_punto_destino,
            indicador_tipo_destino='F',  # Fondo
            fallido=False,
            valor_billete=Decimal('0'),
            valor_moneda=Decimal('0'),
            valor_servicio=Decimal('0'),
            modalidad_servicio=ModalidadServicio.obtener_modalidad_default(),
            observaciones=observaciones,
            archivo_detalle=nombre_archivo
        )
        
        transaccion_dto = TransaccionDTO(
            cod_sucursal=cod_sucursal,
            fecha_registro=datetime.now(),
            usuario_registro_id='e5926e18-33b1-468c-a979-e4e839a86f30',
            tipo_transaccion=TipoTransaccion.RECOLECCION_OFICINA,
            divisa=divisa,
            valor_billetes_declarado=Decimal('0'),
            valor_monedas_declarado=Decimal('0'),
            valor_total_declarado=Decimal('0'),
            estado_transaccion=MapeoEstadoInicial.REGISTRO_TESORERIA
        )
        
        logger.info(f"Mapeo XML remit completado para pedido {numero_pedido}")
        return (servicio_dto, transaccion_dto)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES PRIVADOS
    # ═══════════════════════════════════════════════════════════
    
    def _obtener_cod_cliente_por_nit(self, nit: str) -> Optional[int]:
        """Obtiene el CodCliente desde el NIT usando query directa"""
        query = """
            SELECT cod_cliente 
            FROM adm_clientes 
            WHERE nro_doc = ?
        """
        try:
            result = self._conn_read.execute_scalar(query, [nit])
            return int(result) if result else None
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
        query = """
            SELECT 
                p.cod_suc as cod_sucursal,
                p.cod_fondo,
                p.nom_punto,
                p.cod_punto as cod_punto_pk
            FROM adm_puntos p
            WHERE p.cod_p_cliente = ? AND p.cod_cliente = ?
        """
        try:
            rows = self._conn_read.execute_query(query, [codigo_punto, cod_cliente])
            if not rows:
                return None
            
            row = rows[0]
            return {
                'cod_sucursal': int(row[0]) if row[0] else None,
                'cod_fondo': str(row[1]).strip() if row[1] else None,
                'nombre_punto': str(row[2]).strip() if row[2] else '',
                'cod_punto_pk': str(row[3]).strip() if row[3] else codigo_punto
            }
        except Exception as e:
            logger.error(f"Error obteniendo info del punto '{codigo_punto}': {e}", exc_info=True)
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
        total_billete = Decimal('0')
        total_moneda = Decimal('0')
        try:
            for i in range(1, 9):
                key_denom = next((k for k in registro if f'GAV {i}' in k and 'DENOMINACION' in k), None)
                key_cant = next((k for k in registro if f'GAV {i}' in k and 'CANTIDAD' in k), None)

                if key_denom and key_cant:
                    raw_denom = str(registro.get(key_denom, '0'))
                    raw_cant = str(registro.get(key_cant, '0'))

                    # Limpieza de strings: quitar '$', '.' (miles) y espacios
                    clean_denom = raw_denom.replace('$', '').replace('.', '').strip()
                    clean_cant = raw_cant.replace('.', '').replace(',', '').strip()

                    if clean_denom and clean_cant:
                        denom_val = Decimal(clean_denom)
                        cant_val = Decimal(clean_cant)
                        valor_gaveta = denom_val * cant_val

                        # Clasificar mediante el helper
                        tipo = ConversionHelper.determinar_tipo_denominacion(int(denom_val))
                        
                        if tipo == 'BILLETE':
                            total_billete += valor_gaveta
                        else:
                            total_moneda += valor_gaveta

            return (total_billete, total_moneda)

        except Exception as e:
            logger.error(f"Error calculando valores multigavera TXT: {e}", exc_info=True)
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

    def _obtener_info_completa_punto_sin_cliente(
        self,
        codigo_punto_xml: str,
        codigo_cliente_xml: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene info del punto usando la misma lógica que xml_mappers.
        
        IMPORTANTE: Busca por cod_cliente + cod_p_cliente (concatenado)
        
        Args:
            codigo_punto_xml: Código del punto como viene del XML (ej: "52-SUC-0075", "47-0033")
            codigo_cliente_xml: Código de cliente del XML (si está disponible, ej: "52", "47")
            
        Returns:
            Dict con info del punto o None si no se encuentra
        
        Lógica:
        1. Extraer código de cliente del XML (si viene)
        2. Convertir CC Code → cod_cliente usando CLIENTE_TO_CC
        3. Buscar en BD por cod_p_cliente = cod_cliente_bd + "-" + numero_punto
        """
        from src.infrastructure.config.mapeos import ClienteMapeos
        
        logger.debug(f"Buscando punto: XML cliente='{codigo_cliente_xml}', punto='{codigo_punto_xml}'")
        
        # ────────────────────────────────────────────────────────
        # PASO 1: PROCESAR CÓDIGO DEL XML
        # ────────────────────────────────────────────────────────
        # El XML puede venir en formatos:
        # 1. "52-SUC-0075" → codigo_cliente_xml="52", numero_punto="0075"
        # 2. "52-0075" → codigo_cliente_xml="52", numero_punto="0075"
        # 3. "SUC-0075" → solo numero_punto="0075"
        
        numero_punto = codigo_punto_xml
        if codigo_cliente_xml is None and '-' in codigo_punto_xml:
            # Intentar extraer del formato completo
            partes = codigo_punto_xml.replace('-SUC-', '-').split('-')
            if len(partes) == 2:
                # Formato "52-0075"
                posible_cc, num = partes[0], partes[1]
                if posible_cc.isdigit() and num.isdigit():
                    codigo_cliente_xml = posible_cc
                    numero_punto = num
                    logger.debug(f"Extraído del formato: CC='{codigo_cliente_xml}', Punto='{numero_punto}'")
        
        # Si no tenemos código de cliente del XML, no podemos buscar
        if not codigo_cliente_xml:
            logger.error(f"No se puede buscar punto sin código de cliente. XML: '{codigo_punto_xml}'")
            return None
        
        # ────────────────────────────────────────────────────────
        # PASO 2: CONVERTIR CC CODE → COD_CLIENTE BD
        # ────────────────────────────────────────────────────────
        # El XML usa CC Codes ("52", "01", "02", "23")
        # La BD usa cod_cliente ("45", "46", "47", "48")
        
        cc_to_cliente = {v: k for k, v in ClienteMapeos.CLIENTE_TO_CC.items()}
        
        if codigo_cliente_xml not in cc_to_cliente:
            logger.error(
                f"CC Code '{codigo_cliente_xml}' no está mapeado. "
                f"CC Codes válidos: {list(cc_to_cliente.keys())}"
            )
            return None
        
        cod_cliente_bd = cc_to_cliente[codigo_cliente_xml]
        logger.debug(f"CC Code '{codigo_cliente_xml}' → Cliente BD '{cod_cliente_bd}'")
        
        # ────────────────────────────────────────────────────────
        # PASO 3: BUSCAR EN BD CON FORMATO CORRECTO
        # ────────────────────────────────────────────────────────
        # En la BD, el código completo del punto es: cod_cliente + "-" + cod_p_cliente
        # Ejemplo: "46-0033" (cliente 46, punto 0033)
        
        # Primero intentar buscar por el código completo
        codigo_punto_bd = f"{cod_cliente_bd}-{numero_punto}"
        
        query = """
            SELECT 
                p.cod_cliente,
                p.cod_suc as cod_sucursal,
                p.cod_fondo,
                p.nom_punto
            FROM adm_puntos p
            WHERE p.cod_punto = ? AND p.cod_cliente = ?
        """
        
        try:
            rows = self._conn_read.execute_query(query, [numero_punto, cod_cliente_bd])
            if rows:
                row = rows[0]
                logger.info(f"✅ Punto encontrado: BD '{codigo_punto_bd}', XML '{codigo_punto_xml}'")
                return {
                    'cod_cliente': int(row[0]) if row[0] else None,
                    'cod_sucursal': int(row[1]) if row[1] else None,
                    'cod_fondo': str(row[2]).strip() if row[2] else None,
                    'nombre_punto': str(row[3]).strip() if row[3] else '',
                    'cod_punto_bd': codigo_punto_bd
                }
        except Exception as e:
            logger.error(f"Error buscando punto '{codigo_punto_bd}': {e}", exc_info=True)
        
        # ────────────────────────────────────────────────────────
        # FALLBACK: Buscar solo por número de punto y cliente
        # ────────────────────────────────────────────────────────
        query_fallback = """
            SELECT 
                p.cod_cliente,
                p.cod_suc as cod_sucursal,
                p.cod_fondo,
                p.nom_punto,
                p.cod_p_cliente
            FROM adm_puntos p
            WHERE p.cod_cliente = ? AND p.cod_p_cliente = ?
        """
        
        try:
            rows = self._conn_read.execute_query(query_fallback, [cod_cliente_bd, numero_punto])
            if rows:
                row = rows[0]
                cod_p_cliente_real = str(row[4]).strip() if row[4] else None
                logger.info(
                    f"✅ Punto encontrado (fallback): "
                    f"Cliente '{cod_cliente_bd}', Punto '{numero_punto}' -> '{cod_p_cliente_real}'"
                )
                return {
                    'cod_cliente': int(row[0]) if row[0] else None,
                    'cod_sucursal': int(row[1]) if row[1] else None,
                    'cod_fondo': str(row[2]).strip() if row[2] else None,
                    'nombre_punto': str(row[3]).strip() if row[3] else '',
                    'cod_punto_bd': f"{cod_cliente_bd}-{numero_punto}"
                }
        except Exception as e:
            logger.error(f"Error en fallback para cliente '{cod_cliente_bd}', punto '{numero_punto}': {e}")
        
        logger.error(f"❌ Punto NO encontrado: XML '{codigo_punto_xml}', Cliente BD '{cod_cliente_bd}'")
        return None

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