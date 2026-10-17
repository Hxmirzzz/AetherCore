# AetherCore

AetherCore es una aplicación orientada a automatizar la recepción, validación, aprobación y envío de archivos TXT/XML hacia una API externa para la creación de órdenes de servicio. Está diseñada para trabajar con carpetas de entrada monitorizadas, generar archivos Excel con información estructurada y enviar datos a un sistema externo (CashOS) de forma ordenada y trazable.

## Finalidad

La finalidad principal de AetherCore es digitalizar y ordenar el flujo de trabajo de archivos de negocio que llegan desde distintos canales, especialmente archivos de servicio ATM o remesas XML. La solución permite:

- detectar nuevos archivos en directorios configurados,
- validar el formato básico antes de procesarlos,
- notificar la información a una API interna para revisión o aprobación,
- generar informes y archivos Excel,
- enviar la información a una API externa para crear órdenes,
- dejar registro de eventos y errores para trazabilidad.

## Objetivo

El objetivo del proyecto es reducir la intervención manual en el tratamiento de archivos, acelerar la incorporación de información en sistemas externos y mejorar la visibilidad del estado de cada archivo mediante una API REST y un frontend de supervisión.

## ¿Cómo funciona?

El flujo básico del sistema es el siguiente:

1. El sistema revisa periódicamente carpetas de entrada para detectar archivos `.xml` y `.txt`.
2. Cada archivo es prevalidado para comprobar que tiene un formato mínimo aceptable.
3. Si la validación es correcta, el archivo se notifica a la API interna para quedar pendiente de aprobación.
4. Un usuario revisa la información desde la interfaz web o la API.
5. Si el archivo es aprobado, se ejecuta el proceso de transformación y generación del payload.
6. El sistema envía los datos a la API externa y registra el resultado.
7. El archivo se gestiona en carpetas de salida, gestionados o errores según el resultado.

## Arquitectura del proyecto

```text
AetherCore/
├── src/
│   ├── application/
│   │   ├── orchestrators/
│   │   │   └── processing_orchestrator.py
│   │   └── processors/
│   │       ├── txt/
│   │       └── xml/
│   ├── domain/
│   │   ├── entities/
│   │   └── value_objects/
│   ├── infrastructure/
│   │   ├── api/
│   │   ├── config/
│   │   ├── di/
│   │   ├── excel/
│   │   ├── file_system/
│   │   └── monitoring/
│   └── presentation/
│       ├── api/
│       ├── console/
│       └── frontend/
├── data/
│   ├── in/
│   ├── out/
│   └── handled/
├── logs/
├── config/
├── .env
├── .env.example
├── requirements.txt
├── install_windows_service.bat
├── README.md
└── test/
```

## Componentes principales

### 1. API REST
La API se encuentra en `src/presentation/api/main.py` y expone endpoints para autenticación, notificación de archivos pendientes y aprobación de archivos. Implementa seguridad JWT y WebSockets para llevar notificaciones en tiempo real.

### 2. Frontend React
La app web está en `src/presentation/frontend` y permite consultar archivos pendientes y aprobarlos o rechazarlos desde una interfaz visual.

### 3. Watcher / monitor de carpetas
El sistema revisa las carpetas de entrada de forma periódica mediante `DirectoryWatcher` para detectar nuevos archivos sin intervención manual.

### 4. Orquestador de procesamiento
`ProcessingOrchestrator` es el corazón del proceso. Coordina:

- prevalidación,
- lectura del archivo,
- transformación de datos,
- generación del Excel,
- preparación del payload,
- envío a API externa,
- gestión del estado del archivo.

### 5. Processors XML y TXT
Hay dos rutas de procesamiento:

- `xml`: procesa archivos XML y genera payloads con información como remesas y órdenes.
- `txt`: procesa archivos de texto con estructuras específicas para solicitudes de ATM.

## Requisitos previos

- Python 3.9 o superior
- Node.js y npm para el frontend
- Acceso a la red para comunicarse con la API externa
- Archivo `.env` con variables correctas
- En Windows, posibilidad de instalar NSSM para crear un servicio

## Configuración del entorno

Se usa `.env` para definir rutas y credenciales. La plantilla base está en `.env.example`.

Ejemplo mínimo:

```env
APP_ENV=DEV
COMPANY_CODE=SYSTEM

CARPETA_ENTRADA_TXT=C:\ruta\in\txt
CARPETA_SALIDA_TXT=C:\ruta\out\txt
CARPETA_GESTIONADOS_TXT=C:\ruta\handled\txt
CARPETA_ERRORES_TXT=C:\ruta\errores\txt

CARPETA_ENTRADA_XML=C:\ruta\in\xml
CARPETA_SALIDA_XML=C:\ruta\out\xml
CARPETA_GESTIONADOS_XML=C:\ruta\handled\xml
CARPETA_ERRORES_XML=C:\ruta\errores\xml
CARPETA_RESPUESTA_TXT=C:\ruta\respuesta

EXTERNAL_API_URL=http://api-externa.example/api/
EXTERNAL_API_USER=usuario
EXTERNAL_API_PASSWORD=password

INTERNAL_API_URL=http://localhost:8000
INTERNAL_API_USER=admin
INTERNAL_API_PASSWORD=admin123

JWT_SECRET_KEY=clave_secreta_muy_larga_y_segura
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8
TIEMPO_ESPERA_MONITOREO_GENERAL=10
```

## Instalación

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Arranque de la aplicación

### 1. Backend API

Desde la raíz del proyecto:

```bash
uvicorn src.presentation.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Qué hace este comando:

- levanta FastAPI,
- expone la API en el puerto 8000,
- habilita recarga automática en desarrollo,
- permite consumir endpoints como autenticación, aprobación y estado de archivos.

### 2. Frontend React

```bash
cd src/presentation/frontend
npm install
npm run dev
```

Qué hace cada comando:

- `npm install`: instala dependencias del proyecto frontend.
- `npm run dev`: inicia Vite en modo desarrollo y sirve la UI en el puerto por defecto.
- `npm run build`: genera una build de producción.
- `npm run preview`: sirve la build generada para comprobarla.
- `npm run serve`: levanta una vista previa en el puerto 3000.

### 3. Monitor de archivos (watcher)

```bash
python -m src.presentation.console.console_app --watch
```

Este comando activa el escaneo periódico de carpetas de entrada. Si detecta un archivo nuevo, lo prevalida y lo notifica a la API. Si la opción `--local-test` se usa, lo procesa directamente sin depender del frontend.

## Comandos disponibles del watcher

| Comando | Descripción |
|---|---|
| `python -m src.presentation.console.console_app --watch` | actúa sobre XML y TXT a la vez |
| `python -m src.presentation.console.console_app --watch --only xml` | solo supervisa archivos XML |
| `python -m src.presentation.console.console_app --watch --only txt` | solo supervisa archivos TXT |
| `python -m src.presentation.console.console_app --watch --local-test` | procesa automáticamente archivos sin notificar a la API |
| `python -m src.presentation.console.console_app --watch --api-url http://localhost:8000` | cambia la URL de la API a la que notifica |
| `python -m src.presentation.console.console_app --watch --in-xml C:\ruta\entrada --out-xml C:\ruta\salida` | sobreescribe la carpeta de entrada/salida XML |
| `python -m src.presentation.console.console_app --watch --in-txt C:\ruta\entrada --out-txt C:\ruta\salida` | sobreescribe la carpeta de entrada/salida TXT |

## Cómo se procesa un archivo

El proceso real de un archivo es:

1. llega a la carpeta de entrada,
2. el watcher lo detecta,
3. el orquestador lo prevalida,
4. se genera un `archivo_id` y un preview del contenido,
5. se envía a la API REST para quedar pendiente,
6. el usuario aprueba o rechaza,
7. se ejecuta el transformador del tipo correspondiente,
8. se genera el Excel o el payload final,
9. se envía a la API externa,
10. se mueve o registra el estado del archivo.

## API REST y endpoints clave

### Autenticación

- `POST /api/auth/login`: inicia sesión con usuario y contraseña.
- `GET /api/auth/me`: devuelve información del usuario autenticado.

### Archivos

- `GET /api/archivos/pendientes`: lista los archivos que esperan aprobación.
- `POST /api/archivos/nuevo`: registra un archivo detectado en el sistema.
- `POST /api/archivos/aprobar`: aprueba o rechaza un archivo pendiente.
- `GET /api/archivos/{id}/excel`: descarga el Excel generado.

### WebSocket

- `/ws/notificaciones`: canal para avisos y cambios de estado en tiempo real.

## Carpetas de trabajo

El sistema crea y usa estas carpetas:

- `data/in/txt` y `data/in/xml`: archivos recibidos.
- `data/out/txt` y `data/out/xml`: archivos procesados o exportados.
- `data/handled/txt` y `data/handled/xml`: archivos ya gestionados.
- `logs`: trazabilidad y logs del sistema.

## Servicio de Windows

En la raíz del proyecto existe el archivo `install_windows_service.bat`. Sirve para prepararlo todo en Windows:

- verifica Python,
- crea un entorno virtual si no existe,
- instala dependencias,
- genera carpetas necesarias,
- crea `.env` si falta,
- verifica NSSM para instalar un servicio Windows.

Uso recomendado:

```bat
install_windows_service.bat
```

Importante: este script se debe ejecutar como administrador.

## Logs

La aplicación integra registros de operación y trazabilidad. Los archivos principales se guardan en la carpeta `logs` con nombres como:

- `SYSTEM-UNIFICADO-LOG.txt`
- `SYSTEM-TXT2XLS-LOG.txt`
- `SYSTEM-XML2XLS-LOG.txt`

## Recomendación de uso

Para un entorno de producción o prueba real, se recomienda levantar estos tres elementos:

1. API REST.
2. Frontend React.
3. Watcher de carpetas.

Esto permite que el flujo completo funcione con aprobación manual, trazabilidad y control del proceso.

## Notas finales

- El sistema requiere conexión con API externas y base de datos según la configuración.
- El modo `--local-test` es útil para pruebas sin depender del frontend o de la aprobación manual.
- Las rutas y credenciales deben configurarse correctamente antes de usarse en producción.
- El servicio se encarga de automatizar la ejecución continua sin necesidad de abrir una terminal cada vez.

## Contacto

Para soporte o mantenimiento del proyecto, consultar el responsable del repositorio o bien revisar las variables y la configuración del entorno antes de desplegarlo en producción.
