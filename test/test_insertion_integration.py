"""
Script de prueba de integración del módulo de inserción.

Este script prueba el flujo completo:
1. Conexión a BD
2. Mapeo de datos de prueba
3. Inserción en BD
4. Verificación de resultados

Uso:
    python test_insertion_integration.py
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, date, time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports del proyecto
from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.config.settings import get_config
from src.application.dto.servicio_dto import ServicioDTO
from src.application.dto.transaccion_dto import TransaccionDTO

def test_conexion_bd(container: ApplicationContainer) -> bool:
    """Prueba la conexión a la base de datos."""
    logger.info("=" * 60)
    logger.info("TEST 1: Conexión a Base de Datos")
    logger.info("=" * 60)
    
    try:
        conn = container.db_connection()
        if not conn.is_connected():
            conn.connect()
        
        logger.info("✅ Conexión establecida correctamente")
        
        # Probar query simple
        result = conn.execute_scalar("SELECT 1")
        logger.info(f"✅ Query de prueba ejecutada: {result}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error en conexión: {e}", exc_info=True)
        return False

def test_repositorios(container: ApplicationContainer) -> bool:
    """Prueba los repositorios básicos."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Repositorios")
    logger.info("=" * 60)
    
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

def test_data_mapper_service(container: ApplicationContainer) -> bool:
    """Prueba el DataMapperService con datos de ejemplo."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: DataMapperService")
    logger.info("=" * 60)
    
    try:
        mapper = container.data_mapper_service()
        
        # Datos de prueba simulando un registro TXT tipo 2
        registro_ejemplo = {
            'CODIGO': '12345678',
            'FECHA SERVICIO': '15/05/2025',
            'SERVICIO': '1 - APROVISIONAMIENTO DE OFICINAS',
            'CODIGO PUNTO': '45-0001',
            'NOMBRE PUNTO': 'ATM PRINCIPAL',
            'CIUDAD': '01 - BOGOTÁ',
            'CLIENTE': '45 - BANCO EJEMPLO',
            'TIPO RUTA': 'DIURNO',
            'PRIORIDAD': 'AM',
            'TIPO PEDIDO': 'PROGRAMADO',
            'TIPO VALOR': '1 - COP',
            'TOTAL_VALOR': '$1000000',
            'CANT. BILLETE': '100',
            'GAV 1 - ATM DENOMINACION': '$50000',
            'GAV 1 - ATM CANTIDAD': '20'
        }
        
        logger.info("Mapeando registro de prueba...")
        servicio_dto = mapper.mapear_desde_txt_tipo2(
            registro=registro_ejemplo,
            nit_cliente='900123456',
            nombre_archivo='prueba.txt'
        )
        
        logger.info("✅ ServicioDTO creado:")
        logger.info(f"   Código Solicitud: {servicio_dto.codigo_solicitud}")
        logger.info(f"   Cliente: {servicio_dto.cod_cliente}")
        logger.info(f"   Punto: {servicio_dto.cod_punto_cliente}")
        logger.info(f"   Servicio: {servicio_dto.cod_servicio}")
        logger.info(f"   Fecha: {servicio_dto.fecha_servicio}")
        logger.info(f"   Valor Total: ${servicio_dto.valor_total}")
        
        if servicio_dto.transacciones:
            logger.info(f"✅ Transacciones creadas: {len(servicio_dto.transacciones)}")
            trans1 = servicio_dto.transacciones[0]
            logger.info(f"   Transacción 1: Valor=${trans1.valor_transaccion}, Cantidad={trans1.cantidad}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error en DataMapperService: {e}", exc_info=True)
        return False

def test_insertion_service_dry_run(container: ApplicationContainer) -> bool:
    """Prueba el InsertionService en modo 'dry-run' (sin insertar)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: InsertionService (Dry Run)")
    logger.info("=" * 60)
    
    try:
        insertion_service = container.insertion_service()
        
        # Datos de prueba
        registros_ejemplo = [
            {
                'CODIGO': '12345678',
                'FECHA SERVICIO': '15/05/2025',
                'SERVICIO': '1 - APROVISIONAMIENTO DE OFICINAS',
                'CODIGO PUNTO': '45-0001',
                'TOTAL_VALOR': '$1000000',
                'CANT. BILLETE': '100'
            },
            {
                'CODIGO': '12345679',
                'FECHA SERVICIO': '16/05/2025',
                'SERVICIO': '5 - RECOLECCIÓN DE VALORES',
                'CODIGO PUNTO': '45-0002',
                'TOTAL_VALOR': '$2000000',
                'CANT. BILLETE': '200'
            }
        ]
        
        logger.info(f"Preparando {len(registros_ejemplo)} registros para inserción...")
        
        # Validar que los DTOs se pueden crear
        mapper = container.data_mapper_service()
        dtos_creados = 0
        for reg in registros_ejemplo:
            try:
                dto = mapper.mapear_desde_txt_tipo2(reg, '900123456', 'prueba.txt')
                dtos_creados += 1
                logger.info(f"   ✅ DTO {dtos_creados} creado: {dto.codigo_solicitud}")
            except Exception as e:
                logger.warning(f"   ⚠️  Error creando DTO: {e}")
        
        logger.info(f"✅ {dtos_creados}/{len(registros_ejemplo)} DTOs validados")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error en InsertionService: {e}", exc_info=True)
        return False

def test_insertion_service_real(container: ApplicationContainer) -> bool:
    """
    Prueba el InsertionService con inserción REAL en BD.
    
    ⚠️ ADVERTENCIA: Este test inserta datos reales en la base de datos.
    Solo ejecutar si estás seguro y tienes permisos.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: InsertionService (Inserción Real)")
    logger.info("=" * 60)
    
    config = get_config()
    if not config.is_development:
        logger.warning("⚠️  Este test solo debe ejecutarse en entorno de desarrollo")
        logger.warning("   Configura APP_ENV=DEV en tu .env")
        return False
    
    # Preguntar confirmación
    logger.warning("⚠️  Este test insertará datos REALES en la base de datos")
    respuesta = input("¿Deseas continuar? (si/no): ").strip().lower()
    
    if respuesta != 'si':
        logger.info("Test cancelado por el usuario")
        return False
    
    try:
        insertion_service = container.insertion_service()
        
        # Datos de prueba con timestamp único
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        registro_test = {
            'CODIGO': f'TEST{timestamp}',
            'FECHA SERVICIO': datetime.now().strftime('%d/%m/%Y'),
            'SERVICIO': '1 - APROVISIONAMIENTO DE OFICINAS',
            'CODIGO PUNTO': '45-0001',  # Ajustar a un punto válido
            'NOMBRE PUNTO': 'PUNTO TEST',
            'CIUDAD': '01 - BOGOTÁ',
            'CLIENTE': '45 - CLIENTE TEST',
            'TIPO RUTA': 'DIURNO',
            'PRIORIDAD': 'AM',
            'TIPO PEDIDO': 'PROGRAMADO',
            'TIPO VALOR': '1 - COP',
            'TOTAL_VALOR': '$100000',
            'CANT. BILLETE': '10',
            'GAV 1 - ATM DENOMINACION': '$10000',
            'GAV 1 - ATM CANTIDAD': '10'
        }
        
        logger.info(f"Insertando registro de prueba: {registro_test['CODIGO']}")
        
        resultados = insertion_service.insertar_multiples_desde_txt(
            registros_tipo2=[registro_test],
            nit_cliente='900123456',
            nombre_archivo='test_integration.txt'
        )
        
        # Analizar resultados
        resumen = insertion_service.obtener_resumen_resultados(resultados)
        logger.info("=" * 60)
        logger.info("RESULTADOS DE INSERCIÓN:")
        logger.info(f"   Total: {resumen['total']}")
        logger.info(f"   ✅ Exitosos: {resumen['exitosos']}")
        logger.info(f"   ❌ Fallidos: {resumen['fallidos']}")
        logger.info("=" * 60)
        
        for resultado in resultados:
            if resultado.exitoso:
                logger.info(f"✅ {resultado.codigo_solicitud}: ID={resultado.id_servicio}")
            else:
                logger.error(f"❌ {resultado.codigo_solicitud}: {resultado.mensaje_error}")
        
        return resumen['exitosos'] > 0
        
    except Exception as e:
        logger.error(f"❌ Error en inserción real: {e}", exc_info=True)
        return False

def main():
    """Función principal que ejecuta todos los tests."""
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " SUITE DE PRUEBAS DE INTEGRACIÓN - MÓDULO INSERCIÓN ".center(58) + "║")
    logger.info("╚" + "═" * 58 + "╝")
    
    # Crear container
    container = ApplicationContainer()
    
    # Ejecutar tests
    tests = [
        ("Conexión BD", test_conexion_bd),
        ("Repositorios", test_repositorios),
        ("DataMapperService", test_data_mapper_service),
        ("InsertionService (Dry Run)", test_insertion_service_dry_run),
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
    logger.info("\n" + "=" * 60)
    respuesta = input("¿Ejecutar test de inserción REAL? (si/no): ").strip().lower()
    if respuesta == 'si':
        resultados["Inserción Real"] = test_insertion_service_real(container)
    
    # Resumen final
    logger.info("\n╔" + "═" * 58 + "╗")
    logger.info("║" + " RESUMEN DE TESTS ".center(58) + "║")
    logger.info("╠" + "═" * 58 + "╣")
    
    total = len(resultados)
    exitosos = sum(1 for r in resultados.values() if r)
    
    for nombre, resultado in resultados.items():
        simbolo = "✅" if resultado else "❌"
        logger.info(f"║ {simbolo} {nombre.ljust(50)} ║")
    
    logger.info("╠" + "═" * 58 + "╣")
    logger.info(f"║ Total: {exitosos}/{total} tests exitosos".ljust(59) + "║")
    logger.info("╚" + "═" * 58 + "╝")
    
    # Cerrar conexión
    try:
        container.db_connection().close()
        logger.info("Conexión cerrada correctamente")
    except:
        pass
    
    # Exit code
    sys.exit(0 if exitosos == total else 1)

if __name__ == "__main__":
    main()