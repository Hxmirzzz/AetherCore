# AetherCore - Procesamiento de Archivos

## Descripción General

Aplicación Python para el procesamiento automatizado de archivos (TXT/XML) con arquitectura limpia (Clean Architecture) y patrón de inyección de dependencias. Transforma archivos de entrada en formatos estructurados (Excel), genera respuestas de estado e inserta los datos procesados en SQL Server mediante stored procedures.

## Características

* **Arquitectura Limpia**
  * Separación clara de responsabilidades en capas (dominio, aplicación, infraestructura, presentación)
  * Bajo acoplamiento y alta cohesión
  * Fácil de mantener y extender

* **Procesamiento de Archivos**
  * Soporte para archivos TXT y XML
  * Mapeo de códigos a descripciones usando datos de referencia
  * Generación de reportes en Excel con formato profesional
  * Generación de archivos de respuesta con estado de procesamiento

* **Integración con Base de Datos**
  * Los servicios procesados se insertan automáticamente en las tablas `CgsServicios` y `CefTransacciones` mediante el stored procedure `AddServiceTransaction`
  * Conexión de lectura (producción) para consultar datos de referencia y conexión de escritura (pruebas/local) para insertar servicios
  * Verifica que los servicios no existan antes de insertarlos
  * Commit automático en caso de éxito, rollback en caso de error
  * Carga de datos de referencia desde base de datos (ciudades, clientes, puntos, sucursales)
  * Caché de datos para mejorar el rendimiento

* **Mapeo de Datos**
  * Mapea registros TIPO 2 de archivos TXT a objetos `ServicioDTO` y `TransaccionDTO`
  * Mapea elementos `<order>` y `<remit>` de archivos XML a DTOs
  * Convierte códigos de archivo a códigos de base de datos (servicios → conceptos, divisas, etc.)
  * Determina valores de billetes y monedas según denominaciones

* **Manejo de Errores**
  * Sistema de logging centralizado con rotación automática
  * Manejo robusto de excepciones en todos los niveles
  * Registro detallado de errores con trazabilidad completa
  * Archivos fallidos se mueven a carpetas de errores con respuestas de rechazo

* **Seguridad**
  * Gestión segura de credenciales mediante variables de entorno
  * Validación de datos de entrada en múltiples capas
  * Control de acceso a archivos y recursos

* **Instalación como Servicio de Windows**
  * Script automatizado para instalación mediante NSSM (Non-Sucking Service Manager)
  * Configuración de inicio automático con el sistema
  * Monitoreo continuo de carpetas de entrada
  * Logs dedicados del servicio con rotación automática
  * Reinicio automático en caso de fallos

## Estructura del Proyecto

```
AetherCore/
├── src/
│   ├── application/               # Capa de aplicación
│   │   ├── dto/                   # Objetos de transferencia de datos
│   │   ├── interfaces/            # Interfaces para casos de uso
│   │   ├── orchestrators/         # Orquestadores de flujos de trabajo
│   │   ├── processors/            # Procesadores específicos (TXT/XML)
│   │   └── services/              # Servocios de aplicacion
│   │
│   ├── domain/                    # Capa de dominio
│   │   ├── entities/              # Entidades del dominio
│   │   ├── exceptions/            # Excepciones del dominio
│   │   ├── repositories/          # Interfaces de repositorios
│   │   └── value_objects/         # Objetos de valor
│   │
│   ├── infrastructure/            # Capa de infraestructura
│   │   ├── config/                # Configuración
│   │   ├── database/              # Acceso a base de datos
│   │   ├── di/                    # Inyección de dependencias
│   │   ├── excel/                 # Manejo de archivos Excel
│   │   ├── file_system/           # Operaciones de sistema de archivos
│   │   ├── logging/               # Ajustes para logs
│   │   └── repositories/          # Implementaciones de repositorios
│   │
│   └── presentation/              # Capa de presentación
│       ├── api/                   # API
│       └── console/               # Interfaz de línea de comandos
│
├── config/                        # Archivos de configuración YAML
├── data/                          # Carpeta de datos (local/pruebas)
├── logs/                          # Logs del sistema
├── tests/                         # Pruebas automatizadas
├── .env.example                   # Plantilla de variables de entorno
├── .env                           # Variables de entorno (no versionado)
├── requirements.txt               # Dependencias del proyecto
├── install_windows_service.bat    # Instalador del servicio de Windows
└── README.md                      # Documentación
```

## Requisitos del Sistema

* **Sistema Operativo:** Windows, Linux, o macOS
* **Python:** 3.8 o superior
* **Dependencias:**
  * pandas
  * pyodbc
  * openpyxl
  * python-dotenv
  * pydantic>=2
  * pyyaml>=6
  * pydantic-settings
* **Controlador ODBC para SQL Server:** 
  * Windows: [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver17)
  * Linux/macOS: [Instrucciones de instalación](https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)

## Configuración

### 1. Variables de Entorno

Cree un archivo `.env` en la raíz del proyecto basado en `.env.example`:

```ini
# Ambiente
APP_ENV=DEV #DEV o PRD

# ═══════════════════════════════════════════════════════════
# BASE DE DATOS DE LECTURA (PRODUCCIÓN)
# ═══════════════════════════════════════════════════════════
# Esta conexión se usa para:
# - Consultar datos de referencia (ciudades, clientes, puntos, sucursales)
# - Obtener catálogos (servicios, categorías, divisas)
# - Operaciones de solo lectura

SQL_SERVER_PROD=servidor-produccion
SQL_DATABASE_PROD=base-datos-produccion
SQL_USERNAME_PROD=usuario-lectura
SQL_PASSWORD_PROD=password-lectura

# ═══════════════════════════════════════════════════════════
# BASE DE DATOS DE ESCRITURA (PRUEBAS/LOCAL)
# ═══════════════════════════════════════════════════════════
# Esta conexión se usa para:
# - Insertar servicios mediante AddServiceTransaction
# - Escribir en CgsServicios y CefTransacciones
# - Operaciones de escritura

TEST_SQL_DRIVER=ODBC Driver 17 for SQL Server
TEST_SQL_SERVER=servidor-pruebas
TEST_SQL_DATABASE=base-datos-pruebas
TEST_SQL_USERNAME=usuario-escritura
TEST_SQL_PASSWORD=password-escritura
TEST_SQL_TRUSTED=0

# Habilitar/deshabilitar inserción en BD (1=habilitado, 0=deshabilitado)
ENABLE_TEST_DB_WRITE=1

# ═══════════════════════════════════════════════════════════
# RUTAS DE CARPETAS
# ═══════════════════════════════════════════════════════════

# Carpetas TXT
CARPETA_ENTRADA_TXT=C:\RUTAS\ENTRADAS_TXT
CARPETA_SALIDA_TXT=C:\RUTAS\SALIDA_TXT
CARPETA_RESPUESTA_TXT=C:\RUTAS\SALIDAS_RESPUESTA_TXT
CARPETA_GESTIONADOS_TXT=C:\RUTAS\ENTRADAS_TXT\GESTIONADOS
CARPETA_ERRORES_TXT=C:\RUTAS\ENTRADAS_TXT\ERRORES

# Carpetas XML
CARPETA_ENTRADA_XML=C:\RUTAS\ENTRADAS_XML
CARPETA_SALIDA_XML=C:\RUTAS\SALIDA_XML
CARPETA_GESTIONADOS_XML=C:\RUTAS\ENTRADAS_XML\GESTIONADOS
CARPETA_ERRORES_XML=C:\RUTAS\ENTRADAS_XML\ERRORES

# Configuración de Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/aethercore.log
```

### 2. Estructura de Carpetas

La aplicación espera la siguiente estructura de carpetas:

```
.
├── input/
│   ├── txt/         # Archivos TXT de entrada
│   └── xml/         # Archivos XML de entrada
├── output/
│   ├── txt/         # Archivos de salida TXT
│   └── xml/         # Archivos de salida XML
├── processed/       # Archivos procesados (backup)
└── logs/            # Archivos de registro
```

### 3. Configuración de Base de Datos

#### a) Stored Procedure Requerido

El sistema requiere el stored procedure `AddServiceTransaction` instalado en la base de datos de escritura. Este procedimiento realiza las siguientes operaciones:

- Inserta un registro en `CgsServicios`
- Inserta un registro en `CefTransacciones` 
- Relaciona ambos registros mediante claves foráneas
- Retorna la Orden de Servicio generada (ej: "S-000123")

**Estructura de parámetros principales:**

```sql
EXEC AddServiceTransaction
    -- CgsServicios (Servicio)
    @NumeroPedido,           -- ID único del pedido
    @CodCliente,             -- Código del cliente
    @CodSucursal,            -- Código de sucursal
    @CodConcepto,            -- Tipo de servicio (1=Recolección, 2=Provisión Oficinas, 3=Provisión ATM)
    @ValorBillete,           -- Valor en billetes
    @ValorMoneda,            -- Valor en monedas
    @ValorServicio,          -- Valor total del servicio
    -- ... (más de 40 parámetros)
    
    -- CefTransacciones (Transacción)
    @CefDivisa,              -- Divisa (COP, USD, etc.)
    @CefTipoTransaccion,     -- Tipo (RC=Recolección, PV=Provisión)
    @CefValorBilletesDeclarado,
    @CefValorMonedasDeclarado,
    @CefValorTotalDeclarado,
    -- ... (más parámetros)
```

#### b) Verificar Driver ODBC

Asegúrese de tener configurado el controlador ODBC correspondiente a su sistema operativo:

**Windows:**
```bash
# Verificar drivers disponibles
odbcad32.exe
```

**Linux/macOS:**
```bash
# Verificar instalación
odbcinst -q -d
```

## Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Hxmirzzz/AetherCore.git
cd AetherCore
```

### 2. Configurar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
.\venv\Scripts\activate

# Activar entorno (Linux/macOS)
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configuración Inicial

1. Copiar el archivo de ejemplo de configuración:
   ```bash
   copy .env.example .env
   ```

2. Editar el archivo `.env` con sus configuraciones.

3. Verificar conectividad a ambas bases de datos:
   ```bash
   python test/test_connections.py
   ```

### 5. Instalación como Servicio de Windows (Opcional)

Para ejecutar AetherCore como un servicio de Windows que inicia automáticamente con el sistema:

#### Requisitos Previos

1. **NSSM (Non-Sucking Service Manager):**
   - Descarga: https://nssm.cc/download
   - Extrae `nssm.exe` a `C:\Windows\System32` o agrégalo al PATH del sistema

2. **Privilegios de Administrador:**
   - El script `install_windows_service.bat` debe ejecutarse como administrador

#### Instalación Automática

1. **Ejecutar como Administrador:**
  ```
    Click derecho en install_windows_service.bat → "Ejecutar como administrador"
  ```

2. **El script realizará automáticamente:**
   - ✅ Verificación de privilegios de administrador
   - ✅ Detección automática de Python (probando `python`, `py` y ubicaciones comunes)
   - ✅ Creación del entorno virtual si no existe
   - ✅ Instalación de dependencias desde `requirements.txt`
   - ✅ Creación de carpetas necesarias (`data/in`, `data/out`, `logs`, etc.)
   - ✅ Copia de `.env.example` a `.env` (si no existe)
   - ✅ Instalación del servicio con NSSM
   - ✅ Configuración de logs con rotación automática (10MB máximo)
   - ✅ Configuración de reinicio automático en caso de fallos

3. **Configuración Post-Instalación:**
   
  Si es la primera instalación, edita el archivo `.env` con tus credenciales y rutas:
```
   notepad .env
```
   
  Luego inicia el servicio:
```
  nssm start AetherCoreService
```

#### Gestión del Servicio

Comandos útiles
```
# Iniciar servicio
nssm start AetherCoreService

# Detener servicio
nssm stop AetherCoreService

# Reiniciar servicio
nssm restart AetherCoreService

# Ver estado del servicio
nssm status AetherCoreService

# Editar configuración del servicio
nssm edit AetherCoreService

# Eliminar servicio
nssm stop AetherCoreService
nssm remove AetherCoreService confirm
```

**Gestión desde Windows:**
```
services.msc → Buscar "AetherCore File Processor"
```

#### Logs del Servicio

El servicio genera logs en múltiples ubicaciones:
```
logs/
├── service_stdout.log      # Salida estándar del servicio
├── service_stderr.log      # Errores del servicio
└── aethercore_*.log        # Logs de la aplicación
```

**Ver logs en tiempo real:**
```
# Logs del servicio
type logs\service_stdout.log

# Logs de la aplicación
type logs\aethercore_*.log
```

## Uso

### Modo Consola (Ejecución Manual)

La aplicación se ejecuta a través de la línea de comandos con los siguientes parámetros:

```bash
# Procesar archivos una sola vez (TXT y XML)
python -m src.presentation.console.console_app --once

# Monitorear carpetas en tiempo real (TXT y XML)
python -m src.presentation.console.console_app --watch

# Procesar solo archivos TXT
python -m src.presentation.console.console_app --once --only txt

# Procesar solo archivos XML
python -m src.presentation.console.console_app --once --only xml

# Monitorear solo carpetas TXT
python -m src.presentation.console.console_app --watch --only txt

# Monitorear solo carpetas XML
python -m src.presentation.console.console_app --watch --only xml
```

### Opciones de Línea de Comandos

| Opción      | Descripción                                      |
|-------------|--------------------------------------------------|
| `--once`    | Procesa los archivos una sola vez y termina      |
| `--watch`   | Monitorea las carpetas en tiempo real           |
| `--only`    | Filtra por tipo de archivo (txt/xml)            |
| `--help`    | Muestra la ayuda                                 |

## Monitoreo y Registros

### Estructura de Logs

La aplicación genera registros en la carpeta `logs/` con el siguiente formato de nombre:
```
aethercore_YYYY-MM-DD.log
```

### Niveles de Log

- **DEBUG**: Información detallada para depuración
- **INFO**: Eventos normales de la aplicación
- **WARNING**: Situaciones inusuales que no impiden la ejecución
- **ERROR**: Errores que afectan la funcionalidad
- **CRITICAL**: Errores graves que detienen la aplicación

### Configuración de Logs

Puede ajustar el nivel de log en el archivo `.env`:
```
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=./logs/aethercore.log
```

## Mantenimiento

### Actualización de Datos de Referencia

Los archivos de referencia se cargan al iniciar la aplicación. Para forzar una recarga:

1. Detener la aplicación
2. Actualizar los archivos en `input/reference/`
3. Reiniciar la aplicación

### Limpieza de Archivos Procesados

Se recomienda configurar una tarea programada para limpiar o archivar archivos antiguos en las carpetas de salida y procesados.

## Solución de Problemas

### Problemas Comunes

1. **Error de conexión a la base de datos**
   - Verificar credenciales en `.env`
   - Comprobar que el servidor esté accesible
   - Verificar que el controlador ODBC esté instalado

2. **Archivos no se procesan**
   - Verificar permisos de las carpetas
   - Comprobar que los archivos tengan la extensión correcta
   - Revisar los logs en busca de errores

3. **Problemas de memoria**
   - Reducir el tamaño de los lotes de procesamiento
   - Aumentar la memoria asignada a Python
   - Procesar archivos más pequeños

## Contribución

1. Hacer fork del repositorio
2. Crear una rama para la nueva característica (`git checkout -b feature/nueva-funcionalidad`)
3. Hacer commit de los cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Hacer push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## Contacto / Soporte
Para obtener ayuda o reportar problemas, por favor contacte con [Hxmirzzz](jamir08david@gmail.com)