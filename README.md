# AetherCore - Procesamiento de Archivos

## Descripción General

Aplicación Python para el procesamiento automatizado de archivos (TXT/XML) con arquitectura limpia (Clean Architecture) y patrón de inyección de dependencias. Transforma archivos de entrada en formatos estructurados (Excel) y genera respuestas de estado.

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

* **Gestión de Datos**
  * Conexión a bases de datos SQL Server
  * Carga de datos de referencia desde archivos Excel
  * Caché de datos para mejorar el rendimiento

* **Manejo de Errores**
  * Sistema de logging centralizado
  * Manejo robusto de excepciones
  * Registro detallado de errores

* **Seguridad**
  * Gestión segura de credenciales mediante variables de entorno
  * Validación de datos de entrada
  * Control de acceso a archivos y recursos

## Estructura del Proyecto

```
AetherCore/
├── src/
│   ├── application/               # Capa de aplicación
│   │   ├── dto/                   # Objetos de transferencia de datos
│   │   ├── interfaces/            # Interfaces para casos de uso
│   │   ├── orchestrators/         # Orquestadores de flujos de trabajo
│   │   └── processors/            # Procesadores específicos (TXT/XML)
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
│   │   └── repositories/          # Implementaciones de repositorios
│   │
│   └── presentation/              # Capa de presentación
│       └── console/               # Interfaz de línea de comandos
│
├── tests/                         # Pruebas automatizadas
│   ├── unit/                      # Pruebas unitarias
│   └── integration/               # Pruebas de integración
│
├── .env.example                   # Plantilla de variables de entorno
├── .env                           # Variables de entorno (no versionado)
├── requirements.txt               # Dependencias del proyecto
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
# Configuración de Base de Datos
DB_HOST=servidor-sql
DB_NAME=nombre_base_datos
DB_USER=usuario
DB_PASSWORD=contraseña
DB_DRIVER=ODBC+Driver+17+for+SQL+Server

# Rutas de Carpetas (ajustar según necesidad)
INPUT_TXT_PATH=./input/txt
OUTPUT_TXT_PATH=./output/txt
INPUT_XML_PATH=./input/xml
OUTPUT_XML_PATH=./output/xml
PROCESSED_FILES_PATH=./processed

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

Asegúrese de tener configurado el controlador ODBC correspondiente a su sistema operativo.

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

3. Crear las carpetas necesarias:
   ```bash
   mkdir -p input/txt input/xml output/txt output/xml processed logs
   ```

## Uso

### Modo Consola

La aplicación se ejecuta a través de la línea de comandos con los siguientes parámetros:

```bash
# Procesar archivos una sola vez
python -m src.presentation.console.console_app --once

# Monitorear carpetas en tiempo real
python -m src.presentation.console.console_app --watch

# Procesar solo archivos TXT
python -m src.presentation.console.console_app --once --only txt

# Procesar solo archivos XML
python -m src.presentation.console.console_app --once --only xml
```

### Opciones de Línea de Comandos

| Opción      | Descripción                                      |
|-------------|--------------------------------------------------|
| `--once`    | Procesa los archivos una sola vez y termina      |
| `--watch`   | Monitorea las carpetas en tiempo real           |
| `--only`    | Filtra por tipo de archivo (txt/xml)            |
| `--help`    | Muestra la ayuda                                 |

### Ejecución en Producción

Para ejecutar como servicio en producción, puede usar un gestor de procesos como PM2 (Node.js) o Supervisor.

**Ejemplo con PM2:**

1. Instalar PM2 globalmente:
   ```bash
   npm install -g pm2
   ```

2. Crear un archivo `ecosystem.config.js`:
   ```javascript
   module.exports = {
     apps: [{
       name: 'aethercore',
       script: 'python',
       args: '-m src.presentation.console.console_app --watch',
       interpreter: './venv/Scripts/python',
       watch: false,
       autorestart: true,
       env: {
         PYTHONUNBUFFERED: '1',
       }
     }]
   };
   ```

3. Iniciar el servicio:
   ```bash
   pm2 start ecosystem.config.js
   ```

4. Configurar inicio automático:
   ```bash
   pm2 startup
   pm2 save
   ```

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