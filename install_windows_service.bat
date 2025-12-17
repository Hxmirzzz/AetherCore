@echo off
REM ============================================
REM Instalador de Servicio AetherCore
REM Sistema de procesamiento automatico TXT/XML
REM ============================================

echo.
echo ============================================
echo Instalador de Servicio AetherCore
echo ============================================
echo.

REM Verificar privilegios de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script requiere privilegios de administrador
    echo.
    echo Por favor:
    echo 1. Cierra esta ventana
    echo 2. Click derecho en el archivo install_windows_service.bat
    echo 3. Selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo [OK] Ejecutando con privilegios de administrador
echo.

REM Obtener directiorio actual (donde esta el .bat)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Directorio de trabajo: %CD%
echo.

REM Verificar Python (probar python y py)
echo Verificando instalacion de Python...

REM intentar con 'python'
python --version >nul 2>&1
if %errorLevel% equ 0 (
    set "PYTHON_CMD=python"
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] %PYTHON_VERSION% detectado (comando: python^)
    goto python_found
)

REM intentar con 'py'
py --version >nul 2>&1
if %errorLevel% equ 0 (
    set "PYTHON_CMD=py"
    for /f "tokens=*" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] %PYTHON_VERSION% detectado (comando: py^)
    goto python_found
)

REM Buscar Python en ubicaciones comunes
echo Buscando Python en ubicaciones comunes...
for %%P in (
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) do (
    if exist %%P (
        set "PYTHON_CMD=%%~P"
        for /f "tokens=*" %%i in ('%%~P --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo [OK] %PYTHON_VERSION% encontrado en: %%~P
        goto :python_found
    )
)

REM Si llegamos aqui, Python no se encontro
echo.
echo ============================================
echo ERROR: Python no esta instalado o no esta en el PATH
echo ============================================
echo.
echo Soluciones:
echo.
echo OPCION 1 - Verificar instalacion:
echo   1. Abre CMD y prueba:
echo      python --version
echo      py --version
echo.
echo OPCION 2 - Reinstalar Python:
echo   1. Ve a: https://www.python.org/downloads/
echo   2. Descarga Python 3.9 o superior
echo   3. IMPORTANTE: Marca "Add Python to PATH"
echo   4. Reinicia la terminal despues de instalar
echo.
pause
exit /b 1

:python_found
echo.

REM Verificar que existe src/presentation/console/console_app.py
if not exist "src\presentation\console\console_app.py" (
    echo ERROR: No se encuentra src\presentation\console\console_app.py
    echo Asegurate de estar en la raiz del proyecto AetherCore
    echo.
    pause
    exit /b 1
)

echo [OK] console_app.py encontrado
echo.

REM Crear directorios necesarios
echo Creando directorios del sistema...
if not exist "logs" mkdir logs
if not exist "data\in\txt" mkdir data\in\txt
if not exist "data\in\xml" mkdir data\in\xml
if not exist "data\out\txt" mkdir data\out\txt
if not exist "data\out\xml" mkdir data\out\xml
if not exist "data\handled\txt" mkdir data\handled\txt
if not exist "data\handled\xml" mkdir data\handled\xml
echo [OK] Directorios creados
echo.

REM Verificar/Crear entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    %PYTHON_CMD% -m venv venv
    if %errorLevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
    
    echo Instalando dependencias...
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorLevel% neq 0 (
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
    call venv\Scripts\deactivate
    echo [OK] Dependencias instaladas
    echo.
) else (
    echo [OK] Entorno virtual ya existe
    echo.
)

REM Verificar archivos de configuracion
echo Verificando archivos de configuracion...

if not exist ".env" (
    if exist ".env.example" (
        echo Copiando .env.example a .env...
        copy .env.example .env >nul
        echo.
        echo IMPORTANTE: Debes editar .env con tu configuracion
        set NEED_CONFIG=1
    ) else (
        echo ADVERTENCIA: No se encuentra .env.example
        echo Debes crear manualmente el archivo .env
        set NEED_CONFIG=1
    )
) else (
    echo [OK] .env encontrado
)

echo.

REM Advertencia de configuracion
if defined NEED_CONFIG (
    echo ============================================
    echo ATENCION: CONFIGURACION REQUERIDA
    echo ============================================
    echo.
    echo Se han creado archivos de configuracion de ejemplo.
    echo DEBES editarlos antes de continuar:
    echo.
    echo 1. Edita .env con:
    echo    - SQL_SERVER_PROD=servidor-produccion
    echo    - SQL_DATABASE_PROD=base-datos-produccion
    echo    - SQL_USERNAME_PROD=usuario
    echo    - SQL_PASSWORD_PROD=password
    echo.
    echo    - TEST_SQL_SERVER=servidor-pruebas
    echo    - TEST_SQL_DATABASE=base-datos-pruebas
    echo    - TEST_SQL_USERNAME=usuario-test
    echo    - TEST_SQL_PASSWORD=password-test
    echo.
    echo    - CARPETA_ENTRADA_TXT=C:\AetherCore\in\txt
    echo    - CARPETA_SALIDA_TXT=C:\AetherCore\out\txt
    echo    - CARPETA_ENTRADA_XML=C:\AetherCore\in\xml
    echo    - CARPETA_SALIDA_XML=C:\AetherCore\out\xml
    echo.
    echo Presiona cualquier tecla cuando hayas terminado...
    pause >nul
    echo.
)

REM Verificar NSSM
echo Verificando NSSM (Non-Sucking Service Manager^)...
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo ERROR: NSSM no esta instalado
    echo ============================================
    echo.
    echo NSSM es necesario para instalar el servicio de Windows.
    echo.
    echo Opciones:
    echo.
    echo 1. INSTALAR NSSM (Recomendado^):
    echo    a. Descarga desde: https://nssm.cc/download
    echo    b. Extrae nssm.exe a C:\Windows\System32
    echo    c. O agrega la carpeta de NSSM al PATH
    echo.
    echo 2. USAR TASK SCHEDULER:
    echo    - Abre "Programador de tareas"
    echo    - Crea tarea basica
    echo    - Disparador: "Al iniciar el sistema"
    echo    - Accion: "%CD%\venv\Scripts\python.exe" -m src.presentation.console.console_app --watch
    echo.
    pause
    exit /b 1
)

echo [OK] NSSM instalado
echo.

REM Detener y eliminar servicio existente
echo Verificando servicios existentes...
nssm status AetherCoreService >nul 2>&1
if %errorLevel% equ 0 (
    echo Servicio existente detectado. Deteniendo...
    nssm stop AetherCoreService
    timeout /t 2 /nobreak >nul
    echo Eliminando servicio anterior...
    nssm remove AetherCoreService confirm
    timeout /t 2 /nobreak >nul
    echo [OK] Servicio anterior eliminado
) else (
    echo [OK] No hay servicios previos
)
echo.

REM Instalar servicio
echo ============================================
echo INSTALANDO SERVICIO
echo ============================================
echo.
echo Configuracion:
echo - Nombre: AetherCoreService
echo - Python: %CD%\venv\Scripts\python.exe
echo - Modulo: src.presentation.console.console_app
echo - Modo: --watch (monitoreo continuo)
echo - Directorio: %CD%
echo.

nssm install AetherCoreService "%CD%\venv\Scripts\python.exe"
nssm set AetherCoreService AppParameters "-m src.presentation.console.console_app --watch"
nssm set AetherCoreService AppDirectory "%CD%"

if %errorLevel% neq 0 (
    echo ERROR: No se pudo instalar el servicio
    pause
    exit /b 1
)
echo [OK] Servicio instalado
echo.

REM Configurar servicio
echo Configurando parametros del servicio...

nssm set AetherCoreService AppDirectory "%CD%"
nssm set AetherCoreService DisplayName "AetherCore File Processor"
nssm set AetherCoreService Description "Sistema automatico de procesamiento de archivos TXT/XML con insercion en SQL Server"
nssm set AetherCoreService Start SERVICE_AUTO_START

REM Configurar logs
nssm set AetherCoreService AppStdout "%CD%\logs\service_stdout.log"
nssm set AetherCoreService AppStderr "%CD%\logs\service_stderr.log"
nssm set AetherCoreService AppStdoutCreationDisposition 4
nssm set AetherCoreService AppStderrCreationDisposition 4
nssm set AetherCoreService AppEnvironmentExtra "PYTHONUNBUFFERED=1"

REM Configurar rotacion de logs (10MB maximo)
nssm set AetherCoreService AppRotateFiles 1
nssm set AetherCoreService AppRotateOnline 1
nssm set AetherCoreService AppRotateSeconds 86400
nssm set AetherCoreService AppRotateBytes 10485760

REM Configurar reinicio automatico
nssm set AetherCoreService AppExit Default Restart
nssm set AetherCoreService AppRestartDelay 5000
nssm set AetherCoreService AppThrottle 10000

echo [OK] Servicio configurado
echo.

REM Verificar instalacion
echo Verificando instalacion...
nssm status AetherCoreService >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: El servicio no se instalo correctamente
    pause
    exit /b 1
)

echo [OK] Servicio verificado
echo.

REM Resumen
echo ============================================
echo INSTALACION COMPLETADA
echo ============================================
echo.
echo El servicio "AetherCoreService" ha sido instalado correctamente.
echo.
echo COMANDOS UTILES:
echo.
echo   Iniciar servicio:
echo     nssm start AetherCoreService
echo     o desde Servicios de Windows (services.msc^)
echo.
echo   Detener servicio:
echo     nssm stop AetherCoreService
echo.
echo   Reiniciar servicio:
echo     nssm restart AetherCoreService
echo.
echo   Ver estado:
echo     nssm status AetherCoreService
echo.
echo   Editar configuracion:
echo     nssm edit AetherCoreService
echo.
echo   Ver logs:
echo     type logs\service_stdout.log
echo     type logs\service_stderr.log
echo     type logs\aethercore_*.log
echo.
echo   Eliminar servicio:
echo     nssm stop AetherCoreService
echo     nssm remove AetherCoreService confirm
echo.
echo ARCHIVOS IMPORTANTES:
echo   - .env                    : Variables de entorno (credenciales BD)
echo   - config/config.yaml      : Configuracion de rutas
echo   - logs\                   : Logs del sistema
echo   - data\in\txt\            : Archivos TXT de entrada
echo   - data\in\xml\            : Archivos XML de entrada
echo   - data\out\txt\           : Archivos TXT procesados (Excel)
echo   - data\out\xml\           : Archivos XML procesados (Excel)
echo   - data\handled\txt\       : TXT gestionados (backup)
echo   - data\handled\xml\       : XML gestionados (backup)
echo.
echo NOTAS IMPORTANTES:
echo   - El servicio se ejecuta en modo --watch (monitoreo continuo)
echo   - Procesa automaticamente archivos TXT y XML
echo   - Inserta en BD si ENABLE_TEST_DB_WRITE=1 en .env
echo   - Revisa logs regularmente para detectar errores
echo.
echo ============================================
echo.

set /p START_NOW="¿Deseas iniciar el servicio ahora? (S/N): "
if /i "%START_NOW%"=="S" (
    echo.
    echo Iniciando servicio...
    nssm start AetherCoreService
    timeout /t 3 /nobreak >nul
    echo.
    nssm status AetherCoreService
    echo.
    echo Revisa los logs en: %CD%\logs\
    echo.
) else (
    echo.
    echo El servicio esta instalado pero NO iniciado.
    echo Para iniciarlo manualmente:
    echo   nssm start AetherCoreService
    echo   o desde Servicios de Windows (services.msc^)
    echo.
)

echo Presiona cualquier tecla para salir...
pause >nul