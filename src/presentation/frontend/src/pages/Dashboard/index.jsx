import { useState, useEffect } from 'react';
import { FileText, CheckCircle, XCircle, Clock, LogOut, User, AlertCircle, Database } from 'lucide-react';
import { archivoAPI, authAPI } from '../../services/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import ArchivosPendientes from './ArchivosPendientes';
import ModalAprobacion from './ModalAprobacion';

export default function Dashboard({ usuario, onLogout }) {
  const [archivos, setArchivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalData, setModalData] = useState(null);
  const [stats, setStats] = useState({
    pendientes: 0,
    procesados: 0,
    rechazados: 0
  });
  const [tokenExpirando, setTokenExpirando] = useState(false);
  const { mensajes, conectado } = useWebSocket();

  useEffect(() => {
    verificarToken();
    const intervalToken = setInterval(verificarToken, 5 * 60 * 1000);
    return () => clearInterval(intervalToken);
  }, []);

  const verificarToken = async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        handleLogoutSesion();
        return;
      }

      verificarExpiracionToken(token);
      await authAPI.me();
    } catch (error) {
      if (error.response?.status === 401) {
        handleLogoutSesion();
      }
    }
  };

  const verificarExpiracionToken = (token) => {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const tiempoRestante = (payload.exp * 1000) - Date.now();
      setTokenExpirando(tiempoRestante > 0 && tiempoRestante < 10 * 60 * 1000);
      if (tiempoRestante <= 0) handleLogoutSesion();
    } catch (error) {
      console.error('Error decodificando token:', error);
    }
  };

  const handleLogoutSesion = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    
    if (onLogout) {
      onLogout();
    }
  };

  useEffect(() => {
    cargarArchivos();
  }, []);

  useEffect(() => {
    if (mensajes.length === 0) return;

    const ultimo = mensajes[mensajes.length - 1];
    
    if (ultimo.tipo === 'NUEVO_ARCHIVO') {
        setArchivos(prev => {
            if (prev.find(a => a.id === ultimo.archivo.id)) return prev;
            return [...prev, ultimo.archivo];
        });
        setStats(prev => ({ ...prev, pendientes: prev.pendientes + 1 }));
    }
    else if (ultimo.tipo === 'CAMBIO_ESTADO') {
        setArchivos(prev => prev.filter(a => a.id !== ultimo.archivo.id));

        const esAprobado = ultimo.archivo.estado === 'APROBADO';
        setStats(prev => ({
            ...prev,
            pendientes: Math.max(0, prev.pendientes - 1),
            procesados: esAprobado ? prev.procesados + 1 : prev.procesados,
            rechazados: !esAprobado ? prev.rechazados + 1 : prev.rechazados
         }));
    }
  }, [mensajes]);

  const cargarArchivos = async () => {
    try {
      setLoading(true);
      const data = await archivoAPI.obtenerPendientes();

      if (Array.isArray(data)) {
        setArchivos(data);
        setStats(prev => ({ ...prev, pendientes: data.length }));
      } else {
        setArchivos([]);
      }
    } catch (error) {
      console.error('Error cargando archivos:', error);
      if (error.response?.status !== 401) {
        //alert('Error cargando archivos. Por favor, recarga la página.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAprobar = (archivo) => {
    setModalData({
      archivo,
      tipo: 'aprobar'
    });
  };

  const handleRechazar = (archivo) => {
    setModalData({
      archivo,
      tipo: 'rechazar'
    });
  };

  const handleConfirmarAccion = async (archivo, aprobado, comentarios) => {
    try {
      await archivoAPI.aprobar(archivo.id, aprobado, comentarios);
      
      setArchivos(prev => prev.filter(a => a.id !== archivo.id));
      setModalData(null);
    } catch (error) {
      if (error.response?.status === 401) {
        alert("El archivo ya no se encuentra disponible (posible reinicio del servidor). Se actualizará la lista.");
      } else {
        alert('Atención: ' + (error.response?.data?.detail || error.message));
      }
      setModalData(null);
      setLoading(true);
      setTimeout(cargarArchivos, 1000);
    }
  };

return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {tokenExpirando && (
        <div className="fixed top-4 right-4 z-50 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg shadow-lg max-w-md animate-bounce">
           <p className="text-yellow-800 font-bold">⚠️ Tu sesión expirará pronto</p>
        </div>
      )}

      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
             <div className="bg-white/10 p-2 rounded-lg"><FileText className="w-8 h-8" /></div>
             <div>
                <h1 className="text-2xl font-bold">AetherCore Dashboard</h1>
                <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${conectado ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    <p className="text-blue-200 text-xs">{conectado ? 'Conectado' : 'Desconectado'}</p>
                </div>
             </div>
          </div>
          
          <div className="flex items-center gap-4">
             <div className="text-right hidden sm:block">
               <p className="text-sm font-medium">{usuario.nombre_completo}</p>
               <p className="text-xs text-blue-200">{usuario.username}</p>
             </div>
             <button onClick={handleLogoutSesion} className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg text-sm flex gap-2 items-center transition-colors">
               <LogOut className="w-4 h-4" /> Salir
             </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard title="Pendientes" value={stats.pendientes} icon={Clock} color="yellow" />
          <StatCard title="Procesados" value={stats.procesados} icon={CheckCircle} color="green" />
          <StatCard title="Rechazados" value={stats.rechazados} icon={XCircle} color="red" />
        </div>

        <ArchivosPendientes
          archivos={archivos}
          loading={loading}
          onAprobar={handleAprobar}
          onRechazar={handleRechazar}
        />
      </main>

      {modalData && (
        <ModalAprobacion
          archivo={modalData.archivo}
          tipo={modalData.tipo}
          onConfirmar={handleConfirmarAccion}
          onCancelar={() => setModalData(null)}
        />
      )}
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color }) {
    const colors = {
        yellow: "border-yellow-500 text-yellow-600 bg-yellow-100",
        green: "border-green-500 text-green-600 bg-green-100",
        red: "border-red-500 text-red-600 bg-red-100"
    };
    return (
        <div className={`bg-white rounded-xl shadow-md p-6 border-l-4 ${colors[color].split(' ')[0]}`}>
            <div className="flex justify-between items-center">
                <div>
                    <p className="text-sm text-gray-600 font-medium">{title}</p>
                    <p className="text-3xl font-bold text-gray-800 mt-2">{value}</p>
                </div>
                <div className={`p-3 rounded-full ${colors[color].split(' ').slice(2).join(' ')}`}>
                    <Icon className={`w-8 h-8 ${colors[color].split(' ')[1]}`} />
                </div>
            </div>
        </div>
    );
}