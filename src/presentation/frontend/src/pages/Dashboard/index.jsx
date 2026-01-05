import React, { useState, useEffect } from "react";
import { Bell, CheckCircle, XCircle, FileText, Database, Activity } from "lucide-react";
import { archivoAPI, healthAPI } from "../../services/api";
import { useWebSocket } from "../../hooks/useWebSocket";

const Dashboard = () => {
    const [archivos, setArchivos] = useState([]);
    const [healthStatus, setHealthStatus] = useState({
        database: true,
        folders: true,
        lastCheck: new Date().toISOString()
    });
    const [loading, setLoading] = useState(false);

    const { mensajes, conectado } = useWebSocket();

    useEffect(() => {
        cargarArchivosPendientes();
        verificarSalud();

        const interval = setInterval(cargarArchivosPendientes, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (mensajes.length > 0) {
        const ultimoMensaje = mensajes[mensajes.length - 1];
        
        if (ultimoMensaje.tipo === 'NUEVO_ARCHIVO') {
            setArchivos(prev => [ultimoMensaje.archivo, ...prev]);
            mostrarNotificacion('Nuevo archivo', ultimoMensaje.archivo.nombre);
        } else if (ultimoMensaje.tipo === 'CAMBIO_ESTADO') {
            setArchivos(prev => prev.filter(a => a.id !== ultimoMensaje.archivo.id));
        }
        }
    }, [mensajes]);

    const cargarArchivosPendientes = async () => {
        try {
            const data = await archivoAPI.obtenerPendientes();
            setArchivos(data);
        } catch (error) {
            console.error('Error al cargar archivos:', error);
        }
    };

    const verificarSalud = async () => {
        try {
            const data = await healthAPI.checkStatus();
            setHealthStatus({
                database: data.database.is_healthy,
                folders: Object.values(data.folders).every(f => f.is_healthy),
                lastCheck: data.timestamp
            });
        } catch (error) {
            console.error('Error al verificar salud:', error);
            setHealthStatus(prev => ({
                ...prev,
                database: false
            }));
        }
    };

    const aprobarArchivo = async (id, aprobado) => {
        setLoading(true);
        try {
            await archivoAPI.aprobar(id, aprobado, null, 'admin');
            setArchivos(prev => prev.filter(a => a.id !== id));
            
            const mensaje = aprobado ? 'Archivo aprobado exitosamente' : 'Archivo rechazado exitosamente';
            mostrarNotificacion('Éxito', mensaje);
        } catch (error) {
            console.error('Error al aprobar archivo:', error);
            alert('Error al procesar el archivo: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const mostrarNotificacion = (titulo, mensaje) => {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(titulo, { body: mensaje });
        }
    };

    const formatFecha = (isoString) => {
        return new Date(isoString).toLocaleString('es-CO');
    };

    useEffect(() => {
        if ('Notification' in window && Notification.permission !== 'granted') {
            Notification.requestPermission();
        }
    }, []);


    if (loading) {
        return <div>Cargando...</div>;
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
                <div className="max-w-7xl mx-auto px-4 py-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Activity className="h-8 w-8" />
                            <div>
                                <h1 className="text-2xl font-bold">AetherCore Dashboard</h1>
                                <p className="text-blue-100 text-sm">Panel de control de procesamiento de archivos</p>
                            </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
                                <Database className="h-5 w-5" />
                                <span className="text-sm font-medium">
                                    {healthStatus.database ? 'Conectado' : 'Desconectado'}
                                </span>
                                <div className={`w-2 h-2 rounded-full ${healthStatus.database ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
                            </div>

                            <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
                                <Activity className="w-5 h-5" />
                                <span className="text-sm font-medium">
                                    {conectado ? 'Conectado' : 'Desconectado'}
                                </span>
                                <div className={`w-2 h-2 rounded-full ${conectado ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
                            </div>

                            <div className="relative">
                                <Bell className="h-6 w-6 cursor-pointer hover:text-blue-200 transition-colors" />
                                {archivos.length > 0 && (
                                    <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center animate-bounce">
                                        {archivos.length}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 py-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-500 text-sm font-medium">Pendientes</p>
                                <p className="text-3xl font-bold text-orange-600">{archivos.length}</p>
                            </div>
                            <FileText className="w-12 h-12 text-orange-600 opacity-20" />
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-500 text-sm font-medium">WebSocket</p>
                                <p className="text-lg font-bold text-green-600">
                                    {conectado ? 'Conectado' : 'Desconectado'}
                                </p>
                            </div>
                            <Activity className="w-12 h-12 text-green-600 opacity-20" />
                        </div>
                    </div>
                    
                    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-gray-500 text-sm font-medium">Base de Datos</p>
                                <p className="text-lg font-bold text-blue-600">
                                    {healthStatus.database ? 'Activa' : 'Inactiva'}
                                </p>
                            </div>
                            <Database className="w-12 h-12 text-blue-600 opacity-20" />
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h2 className="text-xl font-bold text-gray-800">Archivos Pendientes de Aprobación</h2>
                    </div>

                    <div className="divide-y divide-gray-200">
                        {archivos.length === 0 ? (
                            <div className="px-6 py-12 text-center text-gray-500">
                                <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
                                <p className="text-lg font-medium">No hay archivos pendientes</p>
                                <p className="text-sm">Todos los archivos han sido aprobados</p>
                            </div>
                        ) : (
                            archivos.map((archivo) => (
                                <div key={archivo.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <span className={`px-2 py-1 rounded text-xs font-bold ${
                                                    archivo.tipo === 'XML' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                                                }`}>
                                                    {archivo.tipo}
                                                </span>
                                                <h3 className="font-mono text-sm font-medium text-gray-900">{archivo.nombre_archivo}</h3>
                                            </div>
                                            
                                            <div className="flex items-center gap-4 text-sm text-gray-600">
                                                <span>Fecha: {formatFecha(archivo.fecha_recepcion)}</span>
                                                <span>Registros: {archivo.num_registros}</span>
                                            </div>

                                            {archivo.errores && archivo.errores.length > 0 && (
                                                <div className="mt-2 bg-red-50 border border-red-200 rounded p-2">
                                                    <p className="text-sm font-medium text-red-800">Errores detectados:</p>
                                                    <ul className="list-disc list-inside text-sm text-red-700">
                                                        {archivo.errores.map((error, idx) => (
                                                            <li key={idx}>{error}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex gap-2 ml-4">
                                            <button
                                                onClick={() => aprobarArchivo(archivo.id, true)}
                                                disabled={loading}
                                                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed">
                                                <CheckCircle className="w-4 h-4" />
                                                Aprobar
                                            </button>
                                            <button
                                                onClick={() => aprobarArchivo(archivo.id, false)}
                                                disabled={loading}
                                                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed">
                                                <XCircle className="w-4 h-4" />
                                                Rechazar
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;