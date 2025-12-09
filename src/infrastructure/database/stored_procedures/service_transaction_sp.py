"""
Ejecutor del Stored Procedure AddServiceTransaction.

Este módulo encapsula la lógica de invocación del SP,
mapeando DTOs a parámetros del SP y manejando el resultado.
"""
from typing import Optional, Any
from datetime import datetime, date, time
from decimal import Decimal
import logging
import pyodbc

from src.application.dto.servicio_dto import ServicioDTO
from src.application.dto.transaccion_dto import TransaccionDTO
from src.application.interfaces.i_database_writer import DatabaseWriteException
from src.infrastructure.database.connection import IDatabaseConnection


logger = logging.getLogger(__name__)


class ServiceTransactionSP:
    """
    Ejecutor del Stored Procedure AddServiceTransaction.
    
    Responsabilidades:
    - Mapear DTOs a parámetros del SP
    - Ejecutar el SP con manejo de errores
    - Extraer y retornar el resultado (OrdenServicio generada)
    """
    
    # Nombre del stored procedure
    SP_NAME = 'AddServiceTransaction'
    
    def __init__(self, connection: IDatabaseConnection):
        """
        Inicializa el ejecutor con una conexión.
        
        Args:
            connection: Conexión a la base de datos
        """
        self._connection = connection
    
    def ejecutar(
        self,
        servicio_dto: ServicioDTO,
        transaccion_dto: TransaccionDTO
    ) -> Optional[str]:
        """
        Ejecuta el SP AddServiceTransaction.
        
        Args:
            servicio_dto: DTO con datos del servicio
            transaccion_dto: DTO con datos de la transacción
            
        Returns:
            Orden de Servicio generada (ej: "S-000123")
            
        Raises:
            DatabaseWriteException: Si el SP falla
        """
        logger.info(f"Ejecutando SP {self.SP_NAME} para pedido {servicio_dto.numero_pedido}")
        
        try:
            # Construir el comando SQL para llamar al SP
            sql_command = self._construir_comando_sp(servicio_dto, transaccion_dto)
            
            # Construir la lista de parámetros
            parametros = self._construir_parametros(servicio_dto, transaccion_dto)
            
            # Ejecutar el SP
            orden_servicio = self._ejecutar_sp(sql_command, parametros)
            
            logger.info(f"SP ejecutado exitosamente. Orden generada: {orden_servicio}")
            return orden_servicio
            
        except pyodbc.Error as e:
            error_msg = f"Error ejecutando SP {self.SP_NAME} para pedido {servicio_dto.numero_pedido}: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseWriteException(error_msg, inner_exception=e)
        except Exception as e:
            error_msg = f"Error inesperado ejecutando SP {self.SP_NAME}: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseWriteException(error_msg, inner_exception=e)
    
    def _construir_comando_sp(
        self,
        servicio_dto: ServicioDTO,
        transaccion_dto: TransaccionDTO
    ) -> str:
        """
        Construye el comando SQL para llamar al SP.
        
        Returns:
            String con el EXEC statement y placeholders
        """
        # Lista de todos los parámetros en el orden correcto
        parametros_sp = [
            # CgsServicios
            '@NumeroPedido', '@CodCliente', '@CodOsCliente', '@CodSucursal',
            '@FechaSolicitud', '@HoraSolicitud', '@CodConcepto', '@TipoTraslado',
            '@CodEstado', '@CodFlujo', '@CodClienteOrigen', '@CodPuntoOrigen',
            '@IndicadorTipoOrigen', '@CodClienteDestino', '@CodPuntoDestino',
            '@IndicadorTipoDestino', '@FechaAceptacion', '@HoraAceptacion',
            '@FechaProgramacion', '@HoraProgramacion', '@FechaAtencionInicial',
            '@HoraAtencionInicial', '@FechaAtencionFinal', '@HoraAtencionFinal',
            '@FechaCancelacion', '@HoraCancelacion', '@FechaRechazo', '@HoraRechazo',
            '@Fallido', '@ResponsableFallido', '@RazonFallido', '@PersonaCancelacion',
            '@OperadorCancelacion', '@MotivoCancelacion', '@ModalidadServicio',
            '@Observaciones', '@Clave', '@OperadorCgsId', '@SucursalCgs',
            '@IpOperador', '@ValorBillete', '@ValorMoneda', '@ValorServicio',
            '@NumeroKitsCambio', '@NumeroBolsasMoneda', '@ArchivoDetalle',
            # CefTransacciones
            '@CefCodRuta', '@CefNumeroPlanilla', '@CefDivisa', '@CefTipoTransaccion',
            '@CefNumeroMesaConteo', '@CefCantidadBolsasDeclaradas',
            '@CefCantidadSobresDeclarados', '@CefCantidadChequesDeclarados',
            '@CefCantidadDocumentosDeclarados', '@CefValorBilletesDeclarado',
            '@CefValorMonedasDeclarado', '@CefValorDocumentosDeclarado',
            '@CefValorTotalDeclarado', '@CefValorTotalDeclaradoLetras',
            '@CefValorTotalContadoLetras', '@CefNovedadInformativa', '@CefEsCustodia',
            '@CefEsPuntoAPunto', '@CefEstadoTransaccion', '@CefFechaRegistro',
            '@CefUsuarioRegistroId', '@CefIPRegistro', '@CefReponsableEntregaId',
            '@CefResponsableRecibeId'
        ]
        
        # Crear placeholders (?) para cada parámetro
        placeholders = ', '.join(['?' for _ in parametros_sp])
        
        # EXEC statement
        command = f"EXEC {self.SP_NAME} {placeholders}"
        
        return command
    
    def _construir_parametros(
        self,
        servicio_dto: ServicioDTO,
        transaccion_dto: TransaccionDTO
    ) -> list:
        """
        Construye la lista ordenada de parámetros para el SP.
        
        Returns:
            Lista de valores en el orden exacto que espera el SP
        """
        # IMPORTANTE: El orden DEBE coincidir exactamente con el SP
        parametros = [
            # ═══════════════════════════════════════════════════════
            # CgsServicios (Servicio)
            # ═══════════════════════════════════════════════════════
            servicio_dto.numero_pedido,
            servicio_dto.cod_cliente,
            servicio_dto.cod_os_cliente,
            servicio_dto.cod_sucursal,
            servicio_dto.fecha_solicitud,
            servicio_dto.hora_solicitud,
            servicio_dto.cod_concepto,
            servicio_dto.tipo_traslado,
            servicio_dto.cod_estado,
            servicio_dto.cod_flujo,
            servicio_dto.cod_cliente_origen,
            servicio_dto.cod_punto_origen,
            servicio_dto.indicador_tipo_origen,
            servicio_dto.cod_cliente_destino,
            servicio_dto.cod_punto_destino,
            servicio_dto.indicador_tipo_destino,
            servicio_dto.fecha_aceptacion,
            servicio_dto.hora_aceptacion,
            servicio_dto.fecha_programacion,
            servicio_dto.hora_programacion,
            servicio_dto.fecha_atencion_inicial,
            servicio_dto.hora_atencion_inicial,
            servicio_dto.fecha_atencion_final,
            servicio_dto.hora_atencion_final,
            servicio_dto.fecha_cancelacion,
            servicio_dto.hora_cancelacion,
            servicio_dto.fecha_rechazo,
            servicio_dto.hora_rechazo,
            servicio_dto.fallido,
            servicio_dto.responsable_fallido,
            servicio_dto.razon_fallido,
            servicio_dto.persona_cancelacion,
            servicio_dto.operador_cancelacion,
            servicio_dto.motivo_cancelacion,
            servicio_dto.modalidad_servicio,
            servicio_dto.observaciones,
            servicio_dto.clave,
            servicio_dto.operador_cgs_id,
            servicio_dto.sucursal_cgs,
            servicio_dto.ip_operador,
            self._decimal_to_int(servicio_dto.valor_billete),
            self._decimal_to_int(servicio_dto.valor_moneda),
            self._decimal_to_int(servicio_dto.valor_servicio),
            servicio_dto.numero_kits_cambio,
            servicio_dto.numero_bolsas_moneda,
            servicio_dto.archivo_detalle,
            
            # ═══════════════════════════════════════════════════════
            # CefTransacciones (Transacción)
            # ═══════════════════════════════════════════════════════
            transaccion_dto.cod_ruta,
            transaccion_dto.numero_planilla,
            transaccion_dto.divisa,
            transaccion_dto.tipo_transaccion,
            transaccion_dto.numero_mesa_conteo,
            transaccion_dto.cantidad_bolsas_declaradas,
            transaccion_dto.cantidad_sobres_declarados,
            transaccion_dto.cantidad_cheques_declarados,
            transaccion_dto.cantidad_documentos_declarados,
            self._decimal_to_int(transaccion_dto.valor_billetes_declarado),
            self._decimal_to_int(transaccion_dto.valor_monedas_declarado),
            self._decimal_to_int(transaccion_dto.valor_documentos_declarado),
            self._decimal_to_int(transaccion_dto.valor_total_declarado),
            transaccion_dto.valor_total_declarado_letras,
            transaccion_dto.valor_total_contado_letras,
            transaccion_dto.novedad_informativa,
            transaccion_dto.es_custodia,
            transaccion_dto.es_punto_a_punto,
            transaccion_dto.estado_transaccion,
            transaccion_dto.fecha_registro,
            transaccion_dto.usuario_registro_id,
            transaccion_dto.ip_registro,
            transaccion_dto.responsable_entrega_id,
            transaccion_dto.responsable_recibe_id
        ]
        
        return parametros
    
    def _ejecutar_sp(self, sql_command: str, parametros: list) -> Optional[str]:
        """
        Ejecuta el SP y extrae la Orden de Servicio generada.
        
        Args:
            sql_command: Comando EXEC
            parametros: Lista de parámetros
            
        Returns:
            Orden de Servicio generada
        """
        cursor = None
        try:
            # Obtener cursor
            self._connection._ensure_connection()
            cursor = self._connection._connection.cursor()
            
            # Ejecutar SP
            cursor.execute(sql_command, parametros)
            
            # El SP retorna la OrdenServicio en un SELECT
            # SELECT @Orden AS OrdenServicioGenerada
            row = cursor.fetchone()
            
            if row:
                orden_servicio = str(row[0])
                logger.debug(f"OrdenServicio generada por SP: {orden_servicio}")
                
                # Hacer commit
                self._connection._connection.commit()
                
                return orden_servicio
            else:
                raise DatabaseWriteException("SP no retornó OrdenServicio")
                
        except Exception as e:
            # Rollback en caso de error
            if self._connection._connection:
                try:
                    self._connection._connection.rollback()
                except Exception:
                    pass
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    @staticmethod
    def _decimal_to_int(valor: Optional[Decimal]) -> Optional[int]:
        """
        Convierte Decimal a int para parámetros DECIMAL(18,0) del SP.
        
        Args:
            valor: Decimal o None
            
        Returns:
            int o None
        """
        if valor is None:
            return None
        return int(valor)