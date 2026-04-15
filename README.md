# AetherCore - Procesamiento de Archivos y Dashboard Interactivo

## Descripción General

AetherCore es una aplicación integral para el procesamiento automatizado de archivos (TXT/XML) y la visualización de datos en tiempo real. Combina un backend robusto en Python, construido con **Arquitectura Limpia**, con un frontend moderno en React.

El sistema transforma archivos de entrada en formatos estructurados (Excel), genera respuestas de estado, inserta los datos en SQL Server y presenta la información en un dashboard interactivo.

## Características Principales

- **Arquitectura Limpia (Backend):** Separación clara de responsabilidades en capas (dominio, aplicación, infraestructura, presentación) que garantiza un bajo acoplamiento y alta cohesión.
- **Procesamiento de Archivos:** Soporte para archivos TXT y XML, con mapeo de datos y generación de reportes en Excel.
- **Integración con SQL Server:** Inserción de datos mediante `stored procedures`, asegurando transacciones atómicas (commit/rollback).
- **Frontend Interactivo (React):** Un dashboard en tiempo real para monitorear el estado de los archivos, ver registros de actividad y gestionar el procesamiento.
- **Comunicación en Tiempo Real:** Uso de WebSockets para notificaciones instantáneas entre el backend y el frontend.
- **Manejo de Errores:** Sistema de logging centralizado y manejo robusto de excepciones.
- **Instalación como Servicio de Windows:** Script automatizado para instalar el backend como un servicio de Windows, garantizando su ejecución continua.

## Estructura del Proyecto

```
AetherCore/
├── src/
│   ├── application/           # Lógica de negocio y casos de uso
│   ├── domain/                # Entidades y reglas del dominio
│   ├── infrastructure/        # Acceso a datos, sistemas externos
│   └── presentation/          # UI (frontend) y API (backend)
│       ├── api/               # API REST y WebSockets (FastAPI)
│       ├── console/           # Aplicación de consola (CLI)
│       └── frontend/          # Aplicación en React
├── config/                    # Archivos de configuración YAML
├── logs/                      # Logs de la aplicación
├── .env.example               # Plantilla de variables de entorno
├── requirements.txt           # Dependencias de Python
└── install_windows_service.bat # Script de instalación
```

## Configuración y Uso

### Backend (Python)

1.  **Entorno Virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate    # Windows
    ```

2.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Variables de Entorno:**
    - Copie `.env.example` a `.env` y configure las credenciales de la base de datos y las rutas de las carpetas.

4.  **Ejecutar la Aplicación:**
    - **Modo de Monitoreo (Servicio):**
      ```bash
      python -m src.presentation.console.console_app --watch
      ```
    - **API y WebSockets:**
      ```bash
      uvicorn src.presentation.api.main:app --reload
      ```

### Frontend (React)

1.  **Navegar al Directorio:**
    ```bash
    cd src/presentation/frontend
    ```

2.  **Instalar Dependencias:**
    ```bash
    npm install
    ```

3.  **Iniciar la Aplicación:**
    ```bash
    npm run dev
    ```
    La aplicación estará disponible en `http://localhost:5173`.

## Contacto

Para obtener ayuda o reportar problemas, contacte a [Hxmirzzz](mailto:jamir08david@gmail.com).