"""
API REST de AetherCore con autenticación JWT.

Endpoints:
- POST /api/auth/login - Autenticación de usuarios
- GET /api/auth/me - Obtener usuario actual
- GET /api/archivos/pendientes - Lista archivos pendientes (protegido)
- POST /api/archivos/aprobar - Aprobar/rechazar archivo (protegido)
- POST /api/archivos/nuevo - Registrar archivo nuevo (interno)
- WS /ws/notificaciones - WebSocket para notificaciones en tiempo real
"""
from fastapi import FastAPI, HTTPException, WebSocket, Depends, status, Query, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import jwt
import pyodbc
import logging
import base64
import hashlib
import struct
import tempfile
import os
import pandas as pd
from pathlib import Path

from src.infrastructure.repositories import ciudad_repository
from src.infrastructure.config.settings import get_config
from src.infrastructure.di.container import ApplicationContainer
from src.infrastructure.repositories.punto_repository import PuntoRepository
from src.infrastructure.repositories.ciudad_repository import CiudadRepository
from src.domain.value_objects.codigo_punto import CodigoPunto
from src.infrastructure.config.mapeos import TextosConstantes

from src.application.processors.xml.xml_mappers import map_elements
from src.application.processors.txt.txt_mappers import parse_tipo_records

Config = get_config()
logger = logging.getLogger(__name__)

SECRET_KEY = Config.jwt.secret_key
ALGORITHM = Config.jwt.algorithm
EXPIRATION_HOURS = Config.jwt.expiration_hours

security = HTTPBearer()

app = FastAPI(
    title="Aether Core API",
    description="API REST de AetherCore con autenticación JWT",
    version="1.0.0"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    """Modelo de solicitud de autenticación"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Modelo de respuesta de autenticación"""
    access_token: str
    token_type: str
    usuario: dict

class ArchivoProcesamientoDTO(BaseModel):
    id: str
    nombre_archivo: str
    tipo: str
    fecha_recepcion: datetime
    estado: str
    num_registros: int
    errores: Optional[List[str]] = None
    excel_path: Optional[str] = None
    ruta_interna: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None

class ArchivoNuevoRequest(BaseModel):
    archivo_id: str
    nombre_archivo: str
    tipo: str
    num_registros: int
    errores: List[str]
    preview: Dict[str, Any]
    ruta_interna: str
    fecha_deteccion: str

class AprobacionRequest(BaseModel):
    archivo_id: str
    aprobado: bool
    comentarios: Optional[str] = None

archivos_pendientes: Dict[str, ArchivoProcesamientoDTO] = {}
conexiones_ws: List[WebSocket] = []

def obtener_conexion_test() -> pyodbc.Connection:
    """Obtiene una conexión a la base de datos de pruebas"""
    """
    Crea conexión a la BD TEST (donde están los usuarios).
    
    Usa la configuración del .env:
    - TEST_SQL_DRIVER
    - TEST_SQL_SERVER
    - TEST_SQL_DATABASE
    - TEST_SQL_USERNAME
    - TEST_SQL_PASSWORD
    """
    try:
        return pyodbc.connect(Config.database_test.connection_string)
    except Exception as e:
        logger.error(f"Error al obtener conexión a la base de datos de pruebas: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error al obtener conexión a la base de datos de pruebas"
        )

def verificar_contraseña(password_plain: str, password_hash_base64: str) -> bool:
    """
    Verifica password contra hash ASP.NET Core Identity V3.
    Estructura detectada:
    - Header: 1 byte (0x01)
    - PRF (Algoritmo): 4 bytes (Big Endian) -> 0x02 = HMAC-SHA512
    - Iteraciones: 4 bytes (Big Endian)
    - Salt Length: 4 bytes (Big Endian)
    - Salt: <Salt Length> bytes
    - Subkey: Resto de bytes
    """
    try:
        if not password_hash_base64:
            return False

        missing_padding = len(password_hash_base64) % 4
        if missing_padding:
            password_hash_base64 += '=' * (4 - missing_padding)
            
        decoded_hash = base64.b64decode(password_hash_base64)

        if len(decoded_hash) < 13 or decoded_hash[0] != 0x01:
            logger.error("Formato de hash no reconocido (no empieza con 0x01 o es muy corto)")
            return False

        try:
            (header, prf_type, iter_count, salt_len) = struct.unpack(">BIII", decoded_hash[0:13])
        except struct.error:
            logger.error("Error desempaquetando la cabecera del hash")
            return False

        salt_start_index = 13
        salt_end_index = 13 + salt_len
        
        if len(decoded_hash) < salt_end_index:
            logger.error("Hash corrupto: longitud menor a la esperada")
            return False
            
        salt = decoded_hash[salt_start_index:salt_end_index]
        expected_subkey = decoded_hash[salt_end_index:]

        # 6. Determinar Algoritmo
        # prf_type 2 = HMAC-SHA512 (Común en Identity V3 moderno)
        # prf_type 1 = HMAC-SHA256
        hash_algorithm = 'sha256'
        if prf_type == 2:
            hash_algorithm = 'sha512'
        elif prf_type == 1:
            hash_algorithm = 'sha256'

        # 7. Calcular Hash con los parámetros extraídos
        actual_subkey = hashlib.pbkdf2_hmac(
            hash_algorithm, 
            password_plain.encode('utf-8'), 
            salt, 
            iter_count, 
            dklen=len(expected_subkey)
        )

        # 8. Comparar
        return actual_subkey == expected_subkey

    except Exception as e:
        logger.error(f"Excepción verificando password: {str(e)}")
        return False

def crear_token_jwt(username: str, email: str) -> str:
    """
    Crea un token JWT firmado.
    
    ¿Qué contiene el token?
    - sub: username del usuario
    - email: email del usuario
    - exp: fecha de expiración (ahora + 8 horas)
    
    ¿Cómo funciona?
    1. Se crea un diccionario con los datos
    2. Se firma con SECRET_KEY (como ponerle un sello)
    3. Se convierte en string: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    ¿Por qué es seguro?
    - Si alguien modifica el token, la firma no coincidirá
    - Solo nuestro servidor puede verificarlo (tiene la SECRET_KEY)
    - Expira automáticamente después de 8 horas
    
    Args:
        username: "turno_diurno"
        email: "diurno@aethercore.com"
    
    Returns:
        Token JWT completo
    """
    payload = {
        "sub": username,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRATION_HOURS)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verifica que el token JWT sea válido.
    
    ¿Cuándo se ejecuta?
    - FastAPI ejecuta esto ANTES de endpoints protegidos
    - Si el token es inválido → Error 401 automático
    - Si es válido → retorna datos del usuario
    
    ¿Cómo se usa?
    @app.get("/ruta-protegida")
    async def mi_ruta(user = Depends(verificar_token)):
        # user contiene {"sub": "turno_diurno", "email": "..."}
        pass
    
    Args:
        credentials: FastAPI lo inyecta desde header "Authorization: Bearer TOKEN"
    
    Returns:
        Datos del token: {"sub": "username", "email": "..."}
    
    Raises:
        HTTPException 401 si el token es inválido o expiró
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("sub") is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        
        return payload
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTError as e:
        logger.error(f"Error al verificar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Autentica al usuario y retorna un token JWT"""
    try:
        conn = obtener_conexion_test()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Id, UserName, Email, PasswordHash, NombreUsuario
            FROM AspNetUsers
            WHERE NormalizedUserName = ?
        """, (request.username.upper(),))

        user = cursor.fetchone()
        conn.close()

        if not user:
            logger.warning(f"Intento de login fallido: usuario '{request.username}' no encontrado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )

        user_id, username, email, password_hash, nombre_usuario = user

        if not verificar_contraseña(request.password, password_hash):
            logger.warning(f"Login fallido: contraseña incorrecta para '{request.username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )

        try:
            conn = obtener_conexion_test()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE AspNetUsers 
                SET LockoutEnd = GETDATE() 
                WHERE Id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Error al actualizar el ultimo acceso del usuario: {e}")

        token = crear_token_jwt(username, email or "")

        logger.info(f"Login exitoso para el usuario: {username}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            usuario={
                "username": username,
                "email": email or "",
                "nombre_completo": nombre_usuario or username
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al autenticar al usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al autenticar al usuario"
        )

@app.get("/api/auth/me")
async def obtener_usuario_actual(token_data: dict = Depends(verificar_token)):
    """
    Obtiene información del usuario actual.
    
    ¿Para qué sirve?
    - Verificar que el token siga válido
    - Al recargar la página, frontend llama a esto
    - Si retorna 200 → sesión válida
    - Si retorna 401 → cerrar sesión
    
    NOTA: Depends(verificar_token) valida el token automáticamente
    
    Request:
        GET /api/auth/me
        Headers: {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    
    Response OK (200):
        {
            "username": "turno_diurno",
            "email": "diurno@aethercore.com"
        }
    """
    return {
        "username": token_data["sub"],
        "email": token_data.get("email", "")
    }

@app.get("/api/archivos/pendientes")
async def obtener_archivos_pendientes(
    token_data: dict = Depends(verificar_token)
):
    """Lista los archivos pendientes de procesamiento."""
    logger.info(f"Usuario {token_data['sub']} solicitando archivos pendientes")
    return list(archivos_pendientes.values())

@app.post("/api/archivos/aprobar")
async def aprobar_archivo(
    request: AprobacionRequest,
    token_data: dict = Depends(verificar_token)
):
    """Aprueba o rechaza un archivo pendiente de procesamiento."""
    archivo = archivos_pendientes.get(request.archivo_id)

    if not archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archivo {request.archivo_id} no encontrado"
        )

    usuario = token_data["sub"]
    
    try:
        container = ApplicationContainer()
        
        if archivo.tipo == "XML":
            orchestrator = container.xml_orchestrator()
        else:
            orchestrator = container.txt_orchestrator()

        conn = container.db_connection_read()
        ruta_archivo = Path(archivo.ruta_interna)

        exito = False

        if request.aprobado:
            logger.info(f"⚡ Iniciando procesamiento real para: {archivo.nombre_archivo}")
            exito = orchestrator.process_approved_file(
                archivo_id=archivo.id,
                ruta=ruta_archivo,
                tipo=archivo.tipo,
                conn=conn
            )

            if exito:
                archivo.estado = "APROBADO"
                archivo.errores = []
                logger.info(f"✅ Archivo procesado exitosamente por {usuario}")
            else:
                archivo.estado = "RECHAZADO"
                logger.error(f"❌ Falló el procesamiento")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al procesar el archivo"
                )
        else:
            logger.info(f"Usuario {usuario} rechazando archivo {archivo.id}")
            exito = orchestrator.reject_file(
                archivo_id=archivo.id,
                ruta=ruta_archivo,
                tipo=archivo.tipo,
                motivo=request.comentarios
            )
            archivo.estado = "RECHAZADO"
        
        await notificar_cambio_estado(archivo)

        if archivo.id in archivos_pendientes:
            del archivos_pendientes[archivo.id]
    
        return {"mensaje": f"Archivo {archivo.id} procesado correctamente"}
    
    except Exception as e:
        logger.error(f"Error al procesar el archivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar el archivo"
        )
    finally:
        if 'container' in locals():
            container.close_all_connections()


@app.get("/api/archivos/{archivo_id}/descargar")
async def descargar_preview(
    archivo_id: str,
    background_tasks: BackgroundTasks,
    token_data: dict = Depends(verificar_token)
):
    """
    Genera y descarga una vista previa (Excel para XML, Original para TXT).
    NO inserta en base de datos ni mueve archivos.
    """
    archivo = archivos_pendientes.get(archivo_id)
    if not archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archivo {archivo_id} no encontrado en pendientes"
        )

    ruta_fisica = Path(archivo.ruta_interna)

    if not ruta_fisica.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archivo {archivo_id} no encontrado en disco"
        )

    try:
        container = ApplicationContainer()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)

        exito_generacion = False

        if archivo.tipo == "XML":
            reader = container.xml_file_reader()
            transformer = container.xml_data_transformer()
            conn = container.db_connection_read()
            punto_repo = PuntoRepository(conn)
            dict_clientes, dict_sucursales = punto_repo.mapas_para_mappers()
            puntos_info = {**dict_clientes, **dict_sucursales}

            info_xml = reader.read(ruta_fisica)
            if info_xml.get("empty"):
                raise Exception("El archivo XML está vacío")

            root = info_xml["root"]
            ordenes_filas = map_elements(
                reader.find_elements(root, "order"),
                TextosConstantes.SERVICIO_RECOLECCION_XML,
                puntos_info
            )
            remesas_filas = map_elements(
                reader.find_elements(root, "remit"),
                TextosConstantes.SERVICIO_RECOLECCION_XML,
                puntos_info
            )

            dfs = transformer.to_dataframes(ordenes_filas, remesas_filas)
            exito_generacion = transformer.write_excel_and_style(
                Path(temp_path), dfs["ordenes"], dfs["remesas"]
            )

        elif archivo.tipo == "TXT":
            reader = container.txt_file_reader()
            transformer = container.txt_data_transformer()
            info_txt = reader.read(ruta_fisica)
            if info_txt.get("empty"):
                raise Exception("El archivo TXT está vacío")

            enc = info_txt.get("encoding") or "utf-8"
            with open(ruta_fisica, "r", encoding=enc, errors="ignore") as f:
                raw_lines = [ln.rstrip("\n") for ln in f.readlines()]

            conn = container.db_connection_read()
            ciud_repo = CiudadRepository(conn)
            punto_repo = PuntoRepository(conn)

            dict_ciudades = ciud_repo.obtener_todas()
            dict_clientes_raw, dict_sucursales_raw = punto_repo.mapas_para_mappers()

            dict_clientes = { CodigoPunto.from_raw(k).parte_numerica: v for k, v in dict_clientes_raw.items() }
            dict_sucursales = { CodigoPunto.from_raw(k).parte_numerica: v for k, v in dict_sucursales_raw.items() }

            dict_tipos_servicio = {}
            dict_categorias = {}
            dict_tipo_valor = {}

            df1, df2, df3 = parse_tipo_records(
                raw_lines,
                dict_ciudades,
                dict_tipos_servicio,
                dict_categorias,
                dict_tipo_valor,
                dict_sucursales,
                dict_clientes
            )

            exito_generacion = transformer.write_excel_consolidated(
                Path(temp_path), df1, df2, df3, hoja_titulo="Consolidado"
            )

        else:
            raise HTTPException(status_code=400, detail="Tipo de archivo no soportado")

        if not exito_generacion:
            raise Exception("Error al generar el archivo Excel")

        background_tasks.add_task(os.remove, temp_path)
        nombre_descarga = f"{ruta_fisica.stem}_PREVIEW.xlsx"

        return FileResponse(
            path=temp_path,
            filename=nombre_descarga,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"Error generando preview para {archivo_id}: {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el archivo Excel: {str(e)}"
        )
    finally:
        if 'container' in locals():
            container.close_all_connections()

@app.post("/api/archivos/nuevo")
async def registrar_archivo_procesado(request: ArchivoNuevoRequest):
    """
    Recibe la notificación desde console_app (Pre-validación).
    Convierte el Request de la consola al DTO interno.
    """
    logger.info(f"📥 Recibida notificación de archivo: {request.nombre_archivo}")

    try:
        fecha_obj = datetime.fromisoformat(request.fecha_deteccion)
    except ValueError:
        fecha_obj = datetime.now()

    nuevo_archivo = ArchivoProcesamientoDTO(
        id=request.archivo_id,
        nombre_archivo=request.nombre_archivo,
        tipo=request.tipo,
        fecha_recepcion=fecha_obj,
        estado="PENDIENTE",
        num_registros=request.num_registros,
        errores=request.errores,
        ruta_interna=request.ruta_interna,
        preview=request.preview
    )

    archivos_pendientes[nuevo_archivo.id] = nuevo_archivo
    logger.info(f"✅ Archivo registrado en memoria: {nuevo_archivo.id}")
    
    await notificar_nuevo_archivo(nuevo_archivo)
    return {"mensaje": "Archivo registrado correctamente", "id": nuevo_archivo.id}

# --- WEBSOCKETS ---

@app.websocket("/ws/notificaciones")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    Endpoint WebSocket autenticado.
    El cliente debe conectar a: ws://localhost:8000/ws/notificaciones?token=EL_TOKEN_JWT
    """
    if token is None:
        logger.warning("Intento de conexión WebSocket sin token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario = payload.get("sub")
        
        if not usuario:
            raise Exception("Token sin usuario")
            
    except Exception as e:
        logger.error(f"Token WebSocket inválido: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    conexiones_ws.append(websocket)
    logger.info(f"WebSocket conectado: Usuario {usuario}")
    
    try:
        while True:
            await websocket.receive_text()            
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: Usuario {usuario}")
        if websocket in conexiones_ws:
            conexiones_ws.remove(websocket)
            
    except Exception as e:
        logger.error(f"Error en conexión WebSocket: {e}")
        if websocket in conexiones_ws:
            conexiones_ws.remove(websocket)


async def notificar_nuevo_archivo(archivo: ArchivoProcesamientoDTO):
    """Envía notificación de nuevo archivo a todos los clientes conectados"""
    mensaje = {
        "tipo": "NUEVO_ARCHIVO",
        "archivo": archivo.model_dump(mode='json')
    }

    for ws in conexiones_ws[:]:
        try:
            await ws.send_json(mensaje)
        except Exception as e:
            logger.error(f"Error al enviar notificación por WebSocket: {e}")
            conexiones_ws.remove(ws)

async def notificar_cambio_estado(archivo: ArchivoProcesamientoDTO):
    """Envía una notificación por WebSocket sobre el cambio de estado de un archivo."""
    mensaje = {
        "tipo": "CAMBIO_ESTADO",
        "archivo": archivo.model_dump(mode='json')
    }

    for ws in conexiones_ws[:]:
        try:
            await ws.send_json(mensaje)
        except Exception as e:
            logger.error(f"Error al enviar notificación por WebSocket: {e}")
            conexiones_ws.remove(ws)

@app.get("/api/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "archivos_pendientes": len(archivos_pendientes),
        "conexiones_ws": len(conexiones_ws)
    }

@app.get("/")
async def root():
    """Endpoint raiz que redirige a la documentación"""
    return {
        "nombre": "AetherCore",
        "version": "1.0.0",
        "descripcion": "API para el procesamiento de archivos XML y TXT",
        "documentacion": "/docs"
    }