import { useState, useEffect } from 'react';
import { 
  FileText, CheckCircle, XCircle, Clock, LogOut, 
  Menu, Bell, Search, LayoutDashboard, FileSpreadsheet, 
  Settings, ChevronRight, AlertTriangle, Database
} from 'lucide-react';
import { archivoAPI, authAPI } from '../../services/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import ArchivosPendientes from './ArchivosPendientes';
import ModalAprobacion from './ModalAprobacion';

export default function Dashboard({ usuario, onLogout }) {
  const [archivos, setArchivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalData, setModalData] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Estado para menú lateral
  
  const [stats, setStats] = useState({
    pendientes: 0,
    procesados: 0,
    rechazados: 0,
    tiempoPromedio: "2.3s" // Dato dummy para visual
  });
  
  const [tokenExpirando, setTokenExpirando] = useState(false);
  const { mensajes, conectado } = useWebSocket();

  // --- LÓGICA DE TOKEN Y WEBSOCKET (MANTENEMOS TU LÓGICA) ---
  useEffect(() => {
    verificarToken();
    const intervalToken = setInterval(verificarToken, 5 * 60 * 1000);
    return () => clearInterval(intervalToken);
  }, []);

  const verificarToken = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) { handleLogoutSesion(); return; }
      verificarExpiracionToken(token);
      await authAPI.me();
    } catch (error) {
      if (error.response?.status === 401) handleLogoutSesion();
    }
  };

  const verificarExpiracionToken = (token) => {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const tiempoRestante = (payload.exp * 1000) - Date.now();
      setTokenExpirando(tiempoRestante > 0 && tiempoRestante < 10 * 60 * 1000);
      if (tiempoRestante <= 0) handleLogoutSesion();
    } catch (error) { console.error(error); }
  };

  const handleLogoutSesion = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    if (onLogout) onLogout();
  };

  useEffect(() => { cargarArchivos(); }, []);

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
      } else { setArchivos([]); }
    } catch (error) { console.error(error); } 
    finally { setLoading(false); }
  };

  const handleAprobar = (archivo) => { setModalData({ archivo, tipo: 'aprobar' }); };
  const handleRechazar = (archivo) => { setModalData({ archivo, tipo: 'rechazar' }); };

  const handleConfirmarAccion = async (archivo, aprobado, comentarios) => {
    try {
      await archivoAPI.aprobar(archivo.id, aprobado, comentarios);
      setArchivos(prev => prev.filter(a => a.id !== archivo.id));
      setModalData(null);
    } catch (error) {
      alert('Atención: ' + (error.response?.data?.detail || error.message));
      setModalData(null);
      setLoading(true);
      setTimeout(cargarArchivos, 1000);
    }
  };

  const handleDescargar = async (archivo) => {
    try { await archivoAPI.descargarPreview(archivo.id, archivo.nombre_archivo); } 
    catch (error) { alert('Error descargando archivo.'); }
  };

  // --- NUEVA ESTRUCTURA VISUAL (SIDEBAR + HEADER BLANCO) ---
  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900 overflow-hidden">
      
      {/* 1. SIDEBAR LATERAL */}
      <aside className={`bg-white border-r border-gray-200 transition-all duration-300 flex flex-col ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        {/* Logo */}
        <div className="h-16 flex items-center justify-center border-b border-gray-100">
          <div className="bg-blue-600 p-2 rounded-lg shadow-sm">
            <FileText className="w-6 h-6 text-white" />
          </div>
          {sidebarOpen && <span className="ml-3 font-bold text-xl text-gray-800 tracking-tight">AetherCore</span>}
        </div>

        {/* Menú de Navegación */}
        <nav className="flex-1 p-4 space-y-2">
          <div className="space-y-1">
            <p className={`px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ${!sidebarOpen && 'hidden'}`}>
              Principal
            </p>
            <SidebarItem icon={LayoutDashboard} text="Dashboard" active={true} expanded={sidebarOpen} />
            <SidebarItem icon={Database} text="Histórico" expanded={sidebarOpen} />
          </div>
          
          <div className="pt-4 space-y-1">
            <p className={`px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ${!sidebarOpen && 'hidden'}`}>
              Sistema
            </p>
            <SidebarItem icon={Settings} text="Configuración" expanded={sidebarOpen} />
          </div>
        </nav>

        {/* Footer Sidebar (Logout) */}
        <div className="p-4 border-t border-gray-100 bg-gray-50/50">
          <button 
            onClick={handleLogoutSesion}
            className={`flex items-center w-full p-2.5 rounded-lg text-red-600 hover:bg-red-50 hover:text-red-700 transition-all duration-200 group ${!sidebarOpen && 'justify-center'}`}
          >
            <LogOut className="w-5 h-5 transition-transform group-hover:-translate-x-1" />
            {sidebarOpen && <span className="ml-3 font-medium text-sm">Cerrar Sesión</span>}
          </button>
        </div>
      </aside>

      {/* 2. CONTENIDO PRINCIPAL */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        
        {/* Header Superior Minimalista */}
        <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 shadow-sm z-20">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)} 
              className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            
            {/* Breadcrumb o Título */}
            <div className="hidden md:flex items-center text-sm text-gray-500">
              <span className="hover:text-gray-900 cursor-pointer transition-colors">Inicio</span>
              <ChevronRight className="w-4 h-4 mx-2" />
              <span className="font-semibold text-gray-900">Dashboard</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Estado WebSocket */}
            <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              conectado 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}>
              <span className={`relative flex h-2 w-2`}>
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${conectado ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${conectado ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
              </span>
              {conectado ? 'Sistema Online' : 'Desconectado'}
            </div>

            <div className="h-6 w-px bg-gray-200 mx-2 hidden sm:block"></div>

            {/* Perfil Usuario */}
            <div className="flex items-center gap-3 pl-2">
              <div className="text-right hidden md:block">
                <p className="text-sm font-semibold text-gray-800 leading-none">{usuario.nombre_completo}</p>
                <p className="text-xs text-gray-500 mt-1 capitalize">{usuario.username}</p>
              </div>
              <div className="h-9 w-9 bg-gradient-to-tr from-blue-600 to-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-md ring-2 ring-white">
                {usuario.username.charAt(0).toUpperCase()}
              </div>
            </div>
          </div>
        </header>

        {/* Área de Contenido con Scroll */}
        <main className="flex-1 overflow-y-auto bg-gray-50/50 p-6 scroll-smooth">
          <div className="max-w-7xl mx-auto">
            
            {/* Alerta de Token */}
            {tokenExpirando && (
              <div className="mb-6 animate-fade-in">
                <div className="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-r-lg shadow-sm flex items-start gap-3">
                  <AlertTriangle className="text-amber-500 w-5 h-5 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-bold text-amber-800">Sesión por expirar</h3>
                    <p className="text-sm text-amber-700 mt-1">Tu sesión se cerrará pronto por seguridad. Guarda tus cambios.</p>
                  </div>
                </div>
              </div>
            )}

            {/* Grid de Estadísticas Moderno */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCardModern 
                title="Pendientes" 
                value={stats.pendientes} 
                icon={FileText} 
                color="amber" 
                trend="Esperando acción"
              />
              <StatCardModern 
                title="Procesados" 
                value={stats.procesados} 
                icon={CheckCircle} 
                color="emerald" 
                trend="+12% hoy"
              />
              <StatCardModern 
                title="Rechazados" 
                value={stats.rechazados} 
                icon={XCircle} 
                color="rose" 
                trend="Revisar errores"
              />
              <StatCardModern 
                title="Tiempo Prom." 
                value={stats.tiempoPromedio} 
                icon={Clock} 
                color="blue" 
                trend="Por archivo"
              />
            </div>

            {/* Contenedor de la Tabla */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {/* Header de la Tabla */}
              <div className="px-6 py-5 border-b border-gray-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Archivos Recientes</h2>
                  <p className="text-sm text-gray-500 mt-1">Gestione los archivos entrantes y valide su contenido.</p>
                </div>
                
                <div className="relative w-full sm:w-64">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg leading-5 bg-gray-50 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm"
                    placeholder="Buscar por nombre..."
                  />
                </div>
              </div>

              {/* Componente de Tabla */}
              <div className="p-0">
                <ArchivosPendientes 
                  archivos={archivos} 
                  loading={loading}
                  onAprobar={handleAprobar}
                  onRechazar={handleRechazar}
                  onDescargar={handleDescargar}
                />
              </div>
            </div>

          </div>
        </main>
      </div>

      {/* Modal */}
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

// --- SUBCOMPONENTES (ESTILOS MODERNOS) ---

function SidebarItem({ icon: Icon, text, active, expanded }) {
  return (
    <button className={`
      flex items-center w-full p-3 rounded-xl transition-all duration-200 group relative overflow-hidden
      ${active 
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
        : 'text-gray-600 hover:bg-gray-100 hover:text-blue-600'
      } 
      ${!expanded && 'justify-center'}
    `}>
      <Icon className={`w-5 h-5 flex-shrink-0 transition-transform duration-300 ${!active && 'group-hover:scale-110'}`} />
      
      {expanded && (
        <span className="ml-3 font-medium text-sm whitespace-nowrap opacity-100 transition-opacity duration-200">
          {text}
        </span>
      )}
      
      {expanded && !active && (
        <ChevronRight className="w-4 h-4 ml-auto text-gray-300 opacity-0 group-hover:opacity-100 transition-all transform -translate-x-2 group-hover:translate-x-0" />
      )}
    </button>
  );
}

function StatCardModern({ title, value, icon: Icon, color, trend }) {
  // Mapas de colores para flexibilidad
  const colors = {
    amber: { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-100" },
    emerald: { bg: "bg-emerald-50", text: "text-emerald-600", ring: "ring-emerald-100" },
    rose: { bg: "bg-rose-50", text: "text-rose-600", ring: "ring-rose-100" },
    blue: { bg: "bg-blue-50", text: "text-blue-600", ring: "ring-blue-100" }
  };

  const theme = colors[color] || colors.blue;

  return (
    <div className="bg-white p-5 rounded-2xl shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] border border-gray-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-xl ${theme.bg} ${theme.text} ring-1 ${theme.ring}`}>
          <Icon className="w-6 h-6" />
        </div>
        {trend && (
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-gray-50 text-gray-500`}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <p className="text-gray-500 font-medium text-xs uppercase tracking-wide">{title}</p>
        <h3 className="text-2xl font-bold text-gray-900 mt-1">{value}</h3>
      </div>
    </div>
  );
}