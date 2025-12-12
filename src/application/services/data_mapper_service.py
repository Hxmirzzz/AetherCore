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
        nombre_archivo: str
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
        es_fondo_origen = es_provision
        indicador_tipo_origen = MapeoIndicadorTipo.determinar_tipo_origen(
            cod_punto_origen, 
            es_fondo=es_fondo_origen
        )
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
            usuario_registro_id='ID_USER',
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
                p.nom_punto
            FROM adm_puntos p
            WHERE p.cod_punto = ? AND p.cod_cliente = ?
        """
        try:
            rows = self._conn_read.execute_query(query, [codigo_punto, cod_cliente])
            if not rows:
                return None
            
            row = rows[0]
            return {
                'cod_sucursal': int(row[0]) if row[0] else None,
                'cod_fondo': str(row[1]).strip() if row[1] else None,
                'nombre_punto': str(row[2]).strip() if row[2] else ''
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