# AetherCore - Procesamiento de Archivos y API REST

## Descripción General

AetherCore es un sistema de procesamiento automatizado de archivos TXT/XML orientado a la integración con APIs externas. El sistema:

1. **Monitorea carpetas** en busca de archivos XML y TXT
2. **Pre-valida y notifica** mediante API REST con autenticación JWT
3. **Genera archivos Excel** con formato estructurado
4. **Envía datos a APIs externas** (CashOS) para crear órdenes de servicio
5. **Gestiona respuestas** de confirmación (archivos TR2)

## Características Principales

- **Procesamiento Dual:** Soporte simultáneo para archivos XML y TXT
- **API REST con JWT:** Backend FastAPI con autenticación segura y WebSockets
- **Integración CashOS:** Comunicación directa con API externa para creación de órdenes
- **Frontend React:** Dashboard interactivo para aprobación de archivos en tiempo real
- **Modo Local/Prueba:** Ejecución sin dependencia del frontend para testing
- **Arquitectura Modular:** Separación clara entre procesadores, orquestadores y clientes API

## Estructura del Proyecto

```
AetherCore/
├── src/
│   ├── application/
│   │   ├── orchestrators/     # Orquestador principal de procesamiento
│   │   └── processors/        # Procesadores XML y TXT
│   │       ├── xml/           # XML → Excel + API
│   │       └── txt/           # TXT → Excel + API
│   ├── domain/
│   │   ├── entities/          # Catálogos y entidades
│   │   └── value_objects/     # Objetos de valor
│   ├── infrastructure/
│   │   ├── api/               # Clientes API (External/Internal)
│   │   ├── config/            # Configuración Pydantic
│   │   ├── di/                # Contenedor de dependencias
│   │   ├── excel/             # Excel styler
│   │   └── file_system/       # Gestión de archivos
│   └── presentation/
│       ├── api/               # API REST (FastAPI)
│       ├── console/           # CLI (modo --watch)
│       └── frontend/          # React + Vite
├── logs/                      # Logs de la aplicación
├── .env                       # Variables de entorno
├── .env.example               # Plantilla de variables
└── requirements.txt           # Dependencias Python
```

## Configuración

### 1. Variables de Entorno (.env)

```env
# ============================================
# IDENTIFICADOR DEL SISTEMA
# ============================================
COMPANY_CODE=SYSTEM

# ============================================
# RUTAS DE PROCESAMIENTO
# ============================================
CARPETA_ENTRADA_TXT=C:\SFTP_VGL\AVAL\ENTRADAS\SOLICITUDES SERVICIOS ATM
CARPETA_SALIDA_TXT=C:\SFTP_VGL\AVAL\SALIDAS\ATH\Confirmacion_TR
CARPETA_RESPUESTA_TXT=C:\SFTP_VGL\AVAL\SALIDAS\ATH\Confirmacion_TR
CARPETA_ERRORES_TXT=C:\SFTP_VGL\AVAL\ENTRADAS\SOLICITUDES SERVICIOS ATM\ERRORES
CARPETA_GESTIONADOS_TXT=C:\SFTP_VGL\AVAL\ENTRADAS\SOLICITUDES SERVICIOS ATM\GESTIONADOS

CARPETA_ENTRADA_XML=C:\SFTP_VGL\AVAL\ENTRADAS\XML
CARPETA_SALIDA_XML=C:\SFTP_VGL\AVAL\SALIDAS\ATH\Confirmacion_TR
CARPETA_GESTIONADOS_XML=C:\SFTP_VGL\AVAL\ENTRADAS\XML\GESTIONADOS
CARPETA_ERRORES_XML=C:\SFTP_VGL\AVAL\ENTRADAS\XML\ERRORES

# ============================================
# API EXTERNA (CashOS)
# ============================================
EXTERNAL_API_URL=https://cashos-test.wbhpro.com/api/v1
EXTERNAL_API_USER=tu_usuario
EXTERNAL_API_PASSWORD=tu_password

# ============================================
# API INTERNA (Notificaciones propias)
# ============================================
INTERNAL_API_URL=http://localhost:8000
INTERNAL_API_USER=admin
INTERNAL_API_PASSWORD=admin123

# ============================================
# JWT (API REST)
# ============================================
JWT_SECRET_KEY=tu_clave_secreta_minimo_32_caracteres
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8

# ============================================
# APP
# ============================================
APP_ENV=DEV
TIEMPO_ESPERA_MONITOREO_GENERAL=10
```

### 2. Instalación

```bash
# Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Modos de Ejecución

### Modo 1: API REST + Frontend (Producción)

**Terminal 1 - API Backend:**
```bash
uvicorn src.presentation.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd src/presentation/frontend
npm install
npm run dev
```

**Terminal 3 - Procesador (modo watch):**
```bash
python -m src.presentation.console.console_app --watch
```

Flujo:
1. El procesador detecta archivos y notifica a la API
2. El frontend muestra archivos pendientes de aprobación
3. Al aprobar, el orquestador procesa y envía a CashOS

### Modo 2: Prueba Local (Sin Frontend)

```bash
python -m src.presentation.console.console_app --watch --local-test
```

- Procesa archivos inmediatamente sin notificar a la API
- Envía directamente a CashOS
- Ideal para testing y desarrollo

### Modo 3: Solo XML o Solo TXT

```bash
# Solo archivos XML
python -m src.presentation.console.console_app --watch --only xml

# Solo archivos TXT
python -m src.presentation.console.console_app --watch --only txt
```

## API REST Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login con usuario/contraseña |
| GET | `/api/auth/me` | Obtener usuario actual |

### Archivos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/archivos/pendientes` | Lista archivos pendientes |
| POST | `/api/archivos/nuevo` | Registrar archivo nuevo (interno) |
| POST | `/api/archivos/aprobar` | Aprobar/rechazar archivo |
| GET | `/api/archivos/{id}/excel` | Descargar Excel generado |

### WebSocket
| Endpoint | Descripción |
|----------|-------------|
| `/ws/notificaciones` | Notificaciones en tiempo real |

## Formato de Archivos Soportados

### XML
**Nombre:** `CC-SYSTEM_XXXX_YYYYMMDD_HHMMSS.xml`

Contiene órdenes y remesas con:
- Información de entrega (fecha, rango horario)
- Denominaciones y cantidades
- Valor total

**Salida:**
- Excel con hojas "Ordenes" y "Remesas"
- Archivo de respuesta `TR2_<COMPANY>_CCAAMMDDHHMM.txt`

### TXT (Solicitudes ATM)
**Nombre:** `VTAAVNAL...` o similar

Registros de tipo:
- **Tipo 1:** Encabezado (información general)
- **Tipo 2:** Detalle (denominaciones, cantidades, valor)

**Salida:**
- Excel formateado
- Archivo de respuesta `TR2_<COMPANY>_CCAAMMDDHHMM.txt`

## Dependencias Principales

```
pandas          # Manipulación de datos
openpyxl        # Generación de Excel
fastapi         # API REST
uvicorn         # Servidor ASGI
websockets      # WebSockets
requests        # Cliente HTTP para APIs
pydantic>=2     # Validación de datos
python-dotenv   # Variables de entorno
pywin32         # Servicio Windows (opcional)
```

## Arquitectura de Flujo

```
+-------------+     +--------------+     +-------------+
|   Archivo   |---->|  Pre-valida  |---->|   API REST  |
|  XML/TXT    |     |  (extracto)  |     |  (pendiente)|
+-------------+     +--------------+     +------+------+
                                                |
                      +-------------------------+
                      |
                      v
              +--------------+     +-------------+
              |   Usuario    |---->|  Procesar   |
              |  (aprobar)   |     |  (orquestar)|
              +--------------+     +------+------+
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
                    v                     v                     v
            +-------------+        +-------------+        +-------------+
            |    Excel    |        |   CashOS    |        |   Respuesta |
            |  (generado) |        |  (API ext)  |        |   (TR2.txt) |
            +-------------+        +-------------+        +-------------+
```

## Logs

Los logs se guardan en `logs/<COMPANY_CODE>-UNIFICADO-LOG.txt` (ej: `SYSTEM-UNIFICADO-LOG.txt`) con formato:
```
2026-04-22 10:30:15 [INFO] Archivo detectado: C4U-52...
2026-04-22 10:30:16 [INFO] Excel generado: Confirmacion_TR/...
2026-04-22 10:30:17 [INFO] Orden creada en CashOS: ID 12345
```

## Notas

- El sistema requiere conexión a internet para comunicación con CashOS
- Para modo desarrollo sin CashOS, usar `--local-test` (ignorará errores SSL)
- Las carpetas se crean automáticamente si no existen
- Los archivos procesados se mueven a carpetas "GESTIONADOS" o "ERRORES"

## Contacto

Para soporte: [Hxmirzzz](mailto:jamir08david@gmail.com)