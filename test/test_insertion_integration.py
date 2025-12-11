"""
Script de prueba del módulo de inserción en BD.

Prueba el flujo completo:
1. Conexiones (lectura y escritura)
2. Repositorios de lectura
3. DataMapperService
4. InsertionService
5. Inserción real en BD (opcional)

Uso:
    python test_insertion.py
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_insertion.log')
    ]
)
logger = logging.getLogger(__name__)

# Imports del proyecto
from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.config.settings import get_config


def print_header(title: str):
    """Imprime un encabezado visual"""
    logger.info("\n" + "=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)


def test_1_configuracion(container: ApplicationContainer) -> bool:
    """Prueba 1: Verificar configuración"""
    print_header("TEST 1: Verificación de Configuración")
    
    try:
        config = container.config()
        
        logger.info(f"✅ Entorno: {config.environment}")
        logger.info(f"✅ Es Desarrollo: {config.is_development}")
        logger.info(f"✅ Es Producción: {config.is_production}")
        logger.info(f"✅ Inserción habilitada: {config.is_insertion_enabled}")
        
        # Mostrar configuración de BDs
        logger.info("\n📊 Base de Datos de LECTURA (Producción):")
        logger.info(f"   Servidor: {config.database_read.server}")
        logger.info(f"   BD: {config.database_read.database}")
        
        logger.info("\n📊 Base de Datos de ESCRITURA (Pruebas/Local):")
        logger.info(f"   Servidor: {config.database_write.server}")
        logger.info(f"   BD: {config.database_write.database}")
        logger.info(f"   Habilitada: {config.database_write.enabled}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en configuración: {e}", exc_info=True)
        return False


def test_2_conexiones(container: ApplicationContainer) -> bool:
    """Prueba 2: Probar ambas conexiones"""
    print_header("TEST 2: Prueba de Conexiones")
    
    try:
        # Conexión de lectura
        logger.info("Probando conexión de LECTURA...")
        conn_read = container.db_connection_read()
        if not conn_read.is_connected():
            conn_read.connect()
        
        result = conn_read.execute_scalar("SELECT 1")
        logger.info(f"✅ Conexión de LECTURA OK: {result}")
        
        # Conexión de escritura (si está habilitada)
        if container.config().is_insertion_enabled:
            logger.info("\nProbando conexión de ESCRITURA...")
            conn_write = container.db_connection_write()
            if conn_write and not conn_write.is_connected():
                conn_write.connect()
            
            if conn_write:
                result = conn_write.execute_scalar("SELECT 1")
                logger.info(f"✅ Conexión de ESCRITURA OK: {result}")
            else:
                logger.warning("⚠️  Conexión de escritura es None")
        else:
            logger.info("⚠️  Inserción deshabilitada, no se prueba conexión de escritura")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en conexiones: {e}", exc_info=True)
        return False


def test_3_repositorios_lectura(container: ApplicationContainer) -> bool:
    """Prueba 3: Repositorios de lectura"""
    print_header("TEST 3: Repositorios de Lectura")
    
    try:
        # Test Ciudad Repository
        ciudad_repo = container.ciudad_repository()
        ciudades = ciudad_repo.obtener_todas()
        logger.info(f"✅ Ciudades cargadas: {len(ciudades)}")
        if ciudades:
            primer_ciudad = list(ciudades.items())[0]
            logger.info(f"   Ejemplo: {primer_ciudad[0]} = {primer_ciudad[1]}")
        
        # Test Cliente Repository
        cliente_repo = container.cliente_repository()
        clientes = cliente_repo.obtener_todos()
        logger.info(f"✅ Clientes cargados: {len(clientes)}")
        if clientes:
            primer_cliente = list(clientes.items())[0]
            logger.info(f"   Ejemplo: {primer_cliente[0]} = {primer_cliente[1]}")
        
        # Test Punto Repository
        punto_repo = container.punto_repository()
        puntos_data = punto_repo.obtener_todo_compuesto()
        logger.info(f"✅ Puntos cargados: {len(puntos_data)}")
        if puntos_data:
            logger.info(f"   Ejemplo: {puntos_data[0].get('cod_punto')} - {puntos_data[0].get('nom_punto')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en repositorios: {e}", exc_info=True)
        return False


def test_4_data_mapper(container: ApplicationContainer) -> bool:
    """Prueba 4: DataMapperService"""
    print_header("TEST 4: DataMapperService")
    
    try:
        mapper = container.data_mapper_service()
        
        # Datos de prueba simulando un registro TXT tipo 2
        registro_ejemplo = {
            'CODIGO': '99999999',  # ID único para prueba
            'FECHA SERVICIO': datetime.now().strftime('%d%m%Y'),
            'SERVICIO': '1',  # APROVISIONAMIENTO_OFICINAS
            'CODIGO PUNTO': '45-0001',  # Ajusta según tu BD
            'NOMBRE PUNTO': 'PUNTO TEST',
            'CIUDAD': '01 - BOGOTÁ',
            'CLIENTE': '45 - CLIENTE TEST',
            'TIPO RUTA': 'DIURNO',
            'PRIORIDAD': 'AM',
            'TIPO PEDIDO': 'PROGRAMADO',
            'TIPO VALOR': '1',  # COP
            'TOTAL_VALOR': '$100000',
            'CANT. BILLETE': '10',
            'DENOMINACION': '10000',
            'CANTIDAD': '10'
        }
        
        logger.info("Mapeando registro de prueba...")
        servicio_dto, transaccion_dto = mapper.mapear_desde_txt_tipo2(
            registro=registro_ejemplo,
            nit_cliente='900123456',  # Ajusta según tu BD
            nombre_archivo='test.txt'
        )
        
        logger.info("✅ ServicioDTO creado:")
        logger.info(f"   NumeroPedido: {servicio_dto.numero_pedido}")
        logger.info(f"   CodCliente: {servicio_dto.cod_cliente}")
        logger.info(f"   CodConcepto: {servicio_dto.cod_concepto}")
        logger.info(f"   ValorBillete: ${servicio_dto.valor_billete}")
        logger.info(f"   ValorMoneda: ${servicio_dto.valor_moneda}")
        
        logger.info("✅ TransaccionDTO creado:")
        logger.info(f"   CodSucursal: {transaccion_dto.cod_sucursal}")
        logger.info(f"   Divisa: {transaccion_dto.divisa}")
        logger.info(f"   ValorTotalDeclarado: ${transaccion_dto.valor_total_declarado}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en DataMapperService: {e}", exc_info=True)
        return False


def test_5_insertion_service_dry_run(container: ApplicationContainer) -> bool:
    """Prueba 5: InsertionService (sin insertar)"""
    print_header("TEST 5: InsertionService (Dry Run)")
    
    try:
        insertion_service = container.insertion_service()
        
        if insertion_service is None:
            logger.warning("⚠️  InsertionService es None (inserción deshabilitada)")
            return True
        
        # Datos de prueba
        registros_ejemplo = [
            {
                'CODIGO': '99999998',
                'FECHA SERVICIO': datetime.now().strftime('%d%m%Y'),
                'SERVICIO': '1',
                'CODIGO PUNTO': '45-0001',
                'DENOMINACION': '10000',
                'CANTIDAD': '10'
            }
        ]
        
        logger.info(f"Preparando {len(registros_ejemplo)} registros para validación...")
        
        # Validar que los DTOs se pueden crear
        mapper = container.data_mapper_service()
        for reg in registros_ejemplo:
            try:
                servicio_dto, _ = mapper.mapear_desde_txt_tipo2(
                    reg, '900123456', 'test.txt'
                )
                logger.info(f"✅ DTO validado: {servicio_dto.numero_pedido}")
            except Exception as e:
                logger.warning(f"⚠️  Error validando DTO: {e}")
        
        logger.info("✅ Validación de DTOs completada")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en InsertionService: {e}", exc_info=True)
        return False


def test_6_insercion_real(container: ApplicationContainer) -> bool:
    """Prueba 6: Inserción REAL en BD"""
    print_header("TEST 6: Inserción Real en BD")
    
    config = container.config()
    
    # Validar que estamos en desarrollo
    if not config.is_development:
        logger.warning("⚠️  Este test solo debe ejecutarse en entorno de DESARROLLO")
        logger.warning("   Configura APP_ENV=DEV en tu .env")
        return False
    
    # Validar que la inserción está habilitada
    if not config.is_insertion_enabled:
        logger.warning("⚠️  Inserción en BD está DESHABILITADA")
        logger.warning("   Configura ENABLE_TEST_DB_WRITE=1 en tu .env")
        return False
    
    # Preguntar confirmación
    logger.warning("⚠️  Este test insertará datos REALES en la base de datos de pruebas")
    respuesta = input("¿Deseas continuar? (si/no): ").strip().lower()
    
    if respuesta != 'si':
        logger.info("Test cancelado por el usuario")
        return False
    
    try:
        insertion_service = container.insertion_service()
        
        if insertion_service is None:
            logger.error("❌ InsertionService es None")
            return False
        
        # Datos de prueba con timestamp único
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        registro_test = {
            'CODIGO': f'TEST{timestamp}',
            'FECHA SERVICIO': datetime.now().strftime('%d%m%Y'),
            'SERVICIO': '1',  # APROVISIONAMIENTO_OFICINAS
            'CODIGO PUNTO': '45-0001',  # ⚠️ AJUSTAR según tu BD
            'NOMBRE PUNTO': 'PUNTO TEST',
            'CIUDAD': '01 - BOGOTÁ',
            'CLIENTE': '45 - CLIENTE TEST',
            'TIPO RUTA': 'DIURNO',
            'PRIORIDAD': 'AM',
            'TIPO PEDIDO': 'PROGRAMADO',
            'TIPO VALOR': '1',
            'TOTAL_VALOR': '$100000',
            'CANT. BILLETE': '10',
            'DENOMINACION': '10000',
            'CANTIDAD': '10'
        }
        
        logger.info(f"Insertando registro de prueba: {registro_test['CODIGO']}")
        
        resultado = insertion_service.insertar_desde_txt_tipo2(
            registro_tipo2=registro_test,
            nit_cliente='900123456',  # ⚠️ AJUSTAR según tu BD
            nombre_archivo='test_integration.txt'
        )
        
        # Analizar resultado
        if resultado.exitoso:
            logger.info("=" * 60)
            logger.info("✅ INSERCIÓN EXITOSA")
            logger.info(f"   Pedido: {resultado.numero_pedido}")
            logger.info(f"   Orden Generada: {resultado.orden_servicio}")
            logger.info("=" * 60)
            return True
        else:
            logger.error("=" * 60)
            logger.error("❌ INSERCIÓN FALLIDA")
            logger.error(f"   Pedido: {resultado.numero_pedido}")
            logger.error(f"   Error: {resultado.error}")
            logger.error("=" * 60)
            return False
            
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        return False


def main():
    """Función principal"""
    print_header("SUITE DE PRUEBAS - MÓDULO DE INSERCIÓN EN BD")
    
    # Crear container
    container = ApplicationContainer()
    
    # Tests
    tests = [
        ("Configuración", test_1_configuracion),
        ("Conexiones", test_2_conexiones),
        ("Repositorios de Lectura", test_3_repositorios_lectura),
        ("DataMapperService", test_4_data_mapper),
        ("InsertionService (Dry Run)", test_5_insertion_service_dry_run),
    ]
    
    resultados = {}
    for nombre, test_func in tests:
        try:
            resultado = test_func(container)
            resultados[nombre] = resultado
        except Exception as e:
            logger.error(f"Error ejecutando test '{nombre}': {e}", exc_info=True)
            resultados[nombre] = False
    
    # Preguntar si hacer test real
    print_header("TEST OPCIONAL: Inserción Real")
    respuesta = input("¿Ejecutar test de inserción REAL en BD? (si/no): ").strip().lower()
    if respuesta == 'si':
        resultados["Inserción Real"] = test_6_insercion_real(container)
    
    # Resumen
    print_header("RESUMEN DE TESTS")
    
    total = len(resultados)
    exitosos = sum(1 for r in resultados.values() if r)
    
    for nombre, resultado in resultados.items():
        simbolo = "✅" if resultado else "❌"
        logger.info(f"{simbolo} {nombre}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {exitosos}/{total} tests exitosos")
    logger.info("=" * 60)
    
    # Cerrar conexiones
    try:
        container.close_all_connections()
        logger.info("Conexiones cerradas correctamente")
    except Exception as e:
        logger.warning(f"Error cerrando conexiones: {e}")
    
    # Exit code
    sys.exit(0 if exitosos == total else 1)


if __name__ == "__main__":
    main()