"""
Implementación del repositorio de escritura de servicios.

Implementa la interfaz IDatabaseWriter usando el SP AddServiceTransaction.
"""
from typing import Optional
import logging

from src.application.interfaces.i_database_writer import IDatabaseWriter, DatabaseWriteException
from src.application.dto.servicio_dto import ServicioDTO
from src.application.dto.transaccion_dto import TransaccionDTO
from src.infrastructure.database.connection import IDatabaseConnection
from src.infrastructure.database.stored_procedures.service_transaction_sp import ServiceTransactionSP


logger = logging.getLogger(__name__)


class ServiceWriterRepository(IDatabaseWriter):
    """
    Repositorio para escribir servicios y transacciones en la base de datos.
    
    Implementa IDatabaseWriter usando el stored procedure AddServiceTransaction.
    """
    
    def __init__(self, connection: IDatabaseConnection):
        """
        Inicializa el repositorio con una conexión.
        
        Args:
            connection: Conexión a la base de datos
        """
        self._connection = connection
        self._sp_executor = ServiceTransactionSP(connection)
    
    def insertar_servicio_con_transaccion(
        self,
        servicio_dto: ServicioDTO,
        transaccion_dto: TransaccionDTO
    ) -> Optional[str]:
        """
        Inserta un servicio junto con su transacción CEF.
        
        Args:
            servicio_dto: DTO con datos del servicio
            transaccion_dto: DTO con datos de la transacción
            
        Returns:
            Orden de Servicio generada (ej: "S-000123")
            
        Raises:
            DatabaseWriteException: Si falla la inserción
        """
        logger.info(f"Insertando servicio con número de pedido: {servicio_dto.numero_pedido}")
        
        try:
            # Validar que los DTOs tengan la misma sucursal
            if servicio_dto.cod_sucursal != transaccion_dto.cod_sucursal:
                raise DatabaseWriteException(
                    f"Inconsistencia: Servicio tiene sucursal {servicio_dto.cod_sucursal}, "
                    f"Transacción tiene sucursal {transaccion_dto.cod_sucursal}"
                )
            
            # Verificar si el servicio ya existe (evitar duplicados)
            if self.verificar_servicio_existe(servicio_dto.numero_pedido):
                logger.warning(
                    f"Servicio con número de pedido {servicio_dto.numero_pedido} "
                    f"ya existe en la BD. Se omite la inserción."
                )
                return None
            
            # Ejecutar el SP
            orden_servicio = self._sp_executor.ejecutar(servicio_dto, transaccion_dto)
            
            if orden_servicio:
                logger.info(
                    f"Servicio insertado exitosamente. "
                    f"NumeroPedido: {servicio_dto.numero_pedido}, "
                    f"OrdenServicio: {orden_servicio}"
                )
            else:
                logger.error(f"SP no retornó OrdenServicio para pedido {servicio_dto.numero_pedido}")
            
            return orden_servicio
            
        except DatabaseWriteException:
            # Re-lanzar excepciones de BD sin modificar
            raise
        except Exception as e:
            error_msg = f"Error insertando servicio {servicio_dto.numero_pedido}: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseWriteException(error_msg, inner_exception=e)
    
    def verificar_servicio_existe(self, numero_pedido: str) -> bool:
        """
        Verifica si un servicio ya existe en la base de datos.
        
        Args:
            numero_pedido: Número de pedido a verificar
            
        Returns:
            True si existe, False en caso contrario
        """
        query = """
            SELECT COUNT(*) 
            FROM CgsServicios 
            WHERE NumeroPedido = ?
        """
        
        try:
            count = self._connection.execute_scalar(query, [numero_pedido])
            existe = (count is not None and int(count) > 0)
            
            if existe:
                logger.debug(f"Servicio con NumeroPedido {numero_pedido} ya existe en BD")
            
            return existe
            
        except Exception as e:
            logger.error(
                f"Error verificando existencia del servicio {numero_pedido}: {e}",
                exc_info=True
            )
            # En caso de error, asumir que NO existe (para no bloquear inserción)
            return False