"""
Servicio de inserción de servicios en base de datos (Orquestador).

Este servicio coordina el proceso completo:
1. Mapeo de datos (DataMapperService)
2. Inserción en BD (IDatabaseWriter)
3. Manejo de errores y logging
"""
from typing import List, Dict, Any, Optional
from datetime import date
import logging

from .data_mapper_service import DataMapperService
from ..interfaces.i_database_writer import IDatabaseWriter, DatabaseWriteException
from ..dto.servicio_dto import ServicioDTO
from ..dto.transaccion_dto import TransaccionDTO
from src.infrastructure.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

class ResultadoInsercion:
    """
    Clase para encapsular el resultado de una inserción.
    
    Attributes:
        exitoso: True si la inserción fue exitosa
        orden_servicio: Orden de servicio generada (si exitoso)
        numero_pedido: Número de pedido procesado
        error: Mensaje de error (si falló)
    """
    
    def __init__(
        self,
        exitoso: bool,
        numero_pedido: str,
        orden_servicio: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.exitoso = exitoso
        self.numero_pedido = numero_pedido
        self.orden_servicio = orden_servicio
        self.error = error
    
    def __str__(self) -> str:
        if self.exitoso:
            return f"✅ Pedido {self.numero_pedido} → Orden {self.orden_servicio}"
        else:
            return f"❌ Pedido {self.numero_pedido} → Error: {self.error}"


class InsertionService:
    """
    Servicio de inserción de servicios en base de datos.
    
    Responsabilidades:
    - Coordinar el mapeo de datos (TXT/XML → DTOs)
    - Coordinar la inserción en BD
    - Manejar errores y logging
    - Retornar resultados estructurados
    """
    
    def __init__(
        self,
        mapper_service: DataMapperService,
        writer: IDatabaseWriter
    ):
        """
        Inicializa el servicio con sus dependencias.
        
        Args:
            mapper_service: Servicio de mapeo de datos
            writer: Repositorio de escritura en BD
        """
        self._mapper = mapper_service
        self._writer = writer
    
    # ═══════════════════════════════════════════════════════════
    # INSERCIÓN DESDE TXT
    # ═══════════════════════════════════════════════════════════
    
    def insertar_desde_txt_tipo2(
        self,
        registro_tipo2: Dict[str, Any],
        nit_cliente: str,
        nombre_archivo: str,
        fecha_generacion_txt: date
    ) -> ResultadoInsercion:
        """
        Procesa e inserta un registro de TIPO 2 (TXT) en la BD.
        
        Args:
            registro_tipo2: Diccionario con datos del registro
            nit_cliente: NIT del cliente (del TIPO 1)
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            ResultadoInsercion con el resultado de la operación
            
        Example:
            resultado = service.insertar_desde_txt_tipo2(
                registro={'CODIGO': '12345', ...},
                nit_cliente='900123456',
                nombre_archivo='archivo.txt'
            )
            if resultado.exitoso:
                print(f"Orden generada: {resultado.orden_servicio}")
        """
        numero_pedido = str(registro_tipo2.get('CODIGO', 'DESCONOCIDO'))
        
        try:
            logger.info(f"Procesando inserción TXT para pedido: {numero_pedido}")
            
            # 1. Mapear datos a DTOs
            servicio_dto, transaccion_dto = self._mapper.mapear_desde_txt_tipo2(
                registro_tipo2,
                nit_cliente,
                nombre_archivo,
                fecha_generacion_txt
            )
            
            # 2. Insertar en BD
            orden_servicio = self._writer.insertar_servicio_con_transaccion(
                servicio_dto,
                transaccion_dto
            )
            
            if orden_servicio:
                return ResultadoInsercion(
                    exitoso=True,
                    numero_pedido=numero_pedido,
                    orden_servicio=orden_servicio
                )
            else:
                # Si retorna None, probablemente ya existía
                return ResultadoInsercion(
                    exitoso=False,
                    numero_pedido=numero_pedido,
                    error="Servicio ya existe (duplicado)"
                )
                
        except DatabaseWriteException as e:
            error_msg = f"Error de BD: {e.message}"
            logger.error(f"Error insertando pedido TXT {numero_pedido}: {error_msg}")
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
        except ValueError as e:
            error_msg = f"Error de validación: {e}"
            logger.error(f"Error validando datos TXT {numero_pedido}: {error_msg}")
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            logger.error(f"Error inesperado insertando TXT {numero_pedido}: {error_msg}", exc_info=True)
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
    
    def insertar_multiples_desde_txt(
        self,
        registros_tipo2: List[Dict[str, Any]],
        nit_cliente: str,
        nombre_archivo: str,
        fecha_generacion_txt: date
    ) -> List[ResultadoInsercion]:
        """
        Procesa e inserta múltiples registros de TIPO 2 (TXT).
        
        Args:
            registros_tipo2: Lista de registros a insertar
            nit_cliente: NIT del cliente
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            Lista de ResultadoInsercion
            
        Example:
            resultados = service.insertar_multiples_desde_txt(
                registros=[reg1, reg2, reg3],
                nit_cliente='900123456',
                nombre_archivo='archivo.txt'
            )
            exitosos = [r for r in resultados if r.exitoso]
            print(f"{len(exitosos)} de {len(resultados)} insertados")
        """
        logger.info(f"Procesando {len(registros_tipo2)} registros TXT del archivo {nombre_archivo}")
        
        resultados = []
        for registro in registros_tipo2:
            resultado = self.insertar_desde_txt_tipo2(
                registro,
                nit_cliente,
                nombre_archivo,
                fecha_generacion_txt
            )
            resultados.append(resultado)
        
        exitosos = sum(1 for r in resultados if r.exitoso)
        fallidos = len(resultados) - exitosos
        
        logger.info(
            f"Inserción TXT completada: {exitosos} exitosos, {fallidos} fallidos "
            f"de {len(resultados)} totales"
        )
        
        return resultados
    
    # ═══════════════════════════════════════════════════════════
    # INSERCIÓN DESDE XML
    # ═══════════════════════════════════════════════════════════
    
    def insertar_desde_xml_order(
        self,
        order_data: Dict[str, Any],
        nombre_archivo: str
    ) -> ResultadoInsercion:
        """
        Procesa e inserta un 'order' (XML) en la BD.
        
        Args:
            order_data: Diccionario con datos del order
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            ResultadoInsercion
        """
        numero_pedido = str(order_data.get('id', 'DESCONOCIDO'))
        
        try:
            logger.info(f"Procesando inserción XML order para pedido: {numero_pedido}")
            
            # 1. Mapear datos a DTOs
            servicio_dto, transaccion_dto = self._mapper.mapear_desde_xml_order(
                order_data,
                nombre_archivo
            )
            
            # 2. Insertar en BD
            orden_servicio = self._writer.insertar_servicio_con_transaccion(
                servicio_dto,
                transaccion_dto
            )
            
            if orden_servicio:
                return ResultadoInsercion(
                    exitoso=True,
                    numero_pedido=numero_pedido,
                    orden_servicio=orden_servicio
                )
            else:
                return ResultadoInsercion(
                    exitoso=False,
                    numero_pedido=numero_pedido,
                    error="Servicio ya existe (duplicado)"
                )
                
        except DatabaseWriteException as e:
            error_msg = f"Error de BD: {e.message}"
            logger.error(f"Error insertando order XML {numero_pedido}: {error_msg}")
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            logger.error(f"Error inesperado insertando order XML {numero_pedido}: {error_msg}", exc_info=True)
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
    
    def insertar_desde_xml_remit(
        self,
        remit_data: Dict[str, Any],
        nombre_archivo: str
    ) -> ResultadoInsercion:
        """
        Procesa e inserta un 'remit' (XML) en la BD.
        
        Args:
            remit_data: Diccionario con datos del remit
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            ResultadoInsercion
        """
        numero_pedido = str(remit_data.get('id', 'DESCONOCIDO'))
        
        try:
            logger.info(f"Procesando inserción XML remit para pedido: {numero_pedido}")
            
            # 1. Mapear datos a DTOs
            servicio_dto, transaccion_dto = self._mapper.mapear_desde_xml_remit(
                remit_data,
                nombre_archivo
            )
            
            # 2. Insertar en BD
            orden_servicio = self._writer.insertar_servicio_con_transaccion(
                servicio_dto,
                transaccion_dto
            )
            
            if orden_servicio:
                return ResultadoInsercion(
                    exitoso=True,
                    numero_pedido=numero_pedido,
                    orden_servicio=orden_servicio
                )
            else:
                return ResultadoInsercion(
                    exitoso=False,
                    numero_pedido=numero_pedido,
                    error="Servicio ya existe (duplicado)"
                )
                
        except DatabaseWriteException as e:
            error_msg = f"Error de BD: {e.message}"
            logger.error(f"Error insertando remit XML {numero_pedido}: {error_msg}")
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            logger.error(f"Error inesperado insertando remit XML {numero_pedido}: {error_msg}", exc_info=True)
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=error_msg
            )
    
    def insertar_multiples_desde_xml(
        self,
        orders: List[Dict[str, Any]],
        remits: List[Dict[str, Any]],
        nombre_archivo: str
    ) -> List[ResultadoInsercion]:
        """
        Procesa e inserta múltiples orders y remits (XML).
        
        Args:
            orders: Lista de orders
            remits: Lista de remits
            nombre_archivo: Nombre del archivo origen
            
        Returns:
            Lista de ResultadoInsercion
        """
        logger.info(
            f"Procesando XML: {len(orders)} orders y {len(remits)} remits "
            f"del archivo {nombre_archivo}"
        )
        
        resultados = []
        
        # Procesar orders
        for order in orders:
            resultado = self.insertar_desde_xml_order(order, nombre_archivo)
            resultados.append(resultado)
        
        # Procesar remits
        for remit in remits:
            resultado = self.insertar_desde_xml_remit(remit, nombre_archivo)
            resultados.append(resultado)
        
        exitosos = sum(1 for r in resultados if r.exitoso)
        fallidos = len(resultados) - exitosos
        
        logger.info(
            f"Inserción XML completada: {exitosos} exitosos, {fallidos} fallidos "
            f"de {len(resultados)} totales"
        )
        
        return resultados
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE UTILIDAD
    # ═══════════════════════════════════════════════════════════
    
    def obtener_resumen_resultados(
        self,
        resultados: List[ResultadoInsercion]
    ) -> Dict[str, Any]:
        """
        Genera un resumen de los resultados de inserción.
        
        Args:
            resultados: Lista de resultados
            
        Returns:
            Diccionario con estadísticas
        """
        total = len(resultados)
        exitosos = sum(1 for r in resultados if r.exitoso)
        fallidos = total - exitosos
        
        ordenes_generadas = [r.orden_servicio for r in resultados if r.exitoso]
        errores = [r.error for r in resultados if not r.exitoso]
        
        return {
            'total': total,
            'exitosos': exitosos,
            'fallidos': fallidos,
            'porcentaje_exito': (exitosos / total * 100) if total > 0 else 0,
            'ordenes_generadas': ordenes_generadas,
            'errores': errores
        }

    # ═══════════════════════════════════════════════════════════
    # TEST CONTROLADO (no toca BD real)
    # ═══════════════════════════════════════════════════════════
    def insert_test_transaction(self) -> ResultadoInsercion:
        """
        Ejecuta el flujo completo:
        - Mapeo usando DataMapperService
        - Inserción usando IDatabaseWriter
        - Retorna ResultadoInsercion
        
        Este test NO toca la BD real porque usa datos
        controlados y puede ser interceptado por el writer.
        """

        fake_record = {
            "CODIGO": "TEST-12345",
            "SERVICIO": 1,
            "CODIGO PUNTO": "1-1085",
            "FECHA SERVICIO": "01122025",
            "DENOMINACION": 50000,
            "CANTIDAD": 2,
            "TIPO VALOR": "1"
        }

        numero_pedido = fake_record["CODIGO"]

        try:
            # 1. Mapear a DTOs
            servicio_dto, transaccion_dto = self._mapper.mapear_desde_txt_tipo2(
                fake_record,
                nit_cliente="890903938",
                nombre_archivo="TEST.txt"
            )

            # 2. Llamar al "writer"
            orden_servicio = self._writer.insertar_servicio_con_transaccion(
                servicio_dto,
                transaccion_dto
            )

            return ResultadoInsercion(
                exitoso=True,
                numero_pedido=numero_pedido,
                orden_servicio=orden_servicio
            )

        except Exception as e:
            return ResultadoInsercion(
                exitoso=False,
                numero_pedido=numero_pedido,
                error=str(e)
            )   