from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List
from fastapi import WebSocket

app = FastAPI(title="Aether Core API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArchivoProcesamientoDTO(BaseModel):
    id: str
    nombre_archivo: str
    tipo: str
    fecha_recepcion: datetime
    estado: str
    num_registros: int
    errores: Optional[List[str]] = None
    excel_path: Optional[str] = None

class AprobacionRequest(BaseModel):
    archivo_id: str
    aprobado: bool
    comentarios: Optional[str] = None
    usuario: str

archivos_pendientes: Dict[str, ArchivoProcesamientoDTO] = {}
conexiones_ws: List[WebSocket] = []

async def notificar_nuevo_archivo(archivo: ArchivoProcesamientoDTO):
    """Envía notificación de nuevo archivo a todos los clientes conectados"""
    mensaje = {
        "tipo": "NUEVO_ARCHIVO",
        "archivo": archivo.model_dump()
    }

    for ws in conexiones_ws[:]:
        try:
            await ws.send_json(mensaje)
        except:
            conexiones_ws.remove(ws)

@app.get("/api/archivos/pendientes")
async def obtener_archivos_pendientes():
    """Lista los archivos pendientes de procesamiento."""
    return list(archivos_pendientes.values())

@app.post("/api/archivos/aprobar")
async def aprobar_archivo(request: AprobacionRequest):
    """Aprueba o rechaza un archivo pendiente de procesamiento."""
    archivo = archivos_pendientes.get(request.archivo_id)

    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")
    
    archivo.estado = "APROBADO" if request.aprobado else "RECHAZADO"
    
    if request.aprobado:
        pass
    await notificar_cambio_estado(archivo)
    del archivos_pendientes[archivo.id]

    return {"mensaje": f"Archivo {archivo.id} procesado correctamente"}

@app.websocket("/ws/notificaciones")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para notificaciones en tiempo real."""
    await websocket.accept()
    conexiones_ws.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        conexiones_ws.remove(websocket)

async def notificar_cambio_estado(archivo: ArchivoProcesamientoDTO):
    """Envía una notificación por WebSocket sobre el cambio de estado de un archivo."""
    mensaje = {
        "tipo": "CAMBIO_ESTADO",
        "archivo": archivo.model_dump()
    }

    for ws in conexiones_ws[:]:
        try:
            await ws.send_json(mensaje)
        except:
            conexiones_ws.remove(ws)

@app.post("/api/archivos/nuevo")
async def registrar_archivo_procesado(archivo: ArchivoProcesamientoDTO):
    """El procesador XML/TXT llama esto cuando termina de procesar"""
    archivo.estado = "PENDIENTE"
    archivos_pendientes[archivo.id] = archivo
    await notificar_nuevo_archivo(archivo)

    return {"mensaje": f"Archivo {archivo.id} registrado correctamente"}