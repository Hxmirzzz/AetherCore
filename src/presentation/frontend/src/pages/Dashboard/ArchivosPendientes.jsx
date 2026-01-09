import { FileText, CheckCircle, XCircle, AlertCircle, Loader2, AlertTriangle, X } from 'lucide-react';

export default function ArchivosPendientes({ archivos, loading, onAprobar, onRechazar }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
          <p className="text-gray-600 font-medium">Cargando archivos pendientes...</p>
        </div>
      </div>
    );
  }

  if (archivos.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md p-12 text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-4">
          <CheckCircle className="w-10 h-10 text-green-600" />
        </div>
        <h3 className="text-xl font-bold text-gray-800 mb-2">¡Todo al día!</h3>
        <p className="text-gray-600">No hay archivos pendientes de aprobación</p>
      </div>
    );
  }

  const formatFecha = (fecha) => {
    if (!fecha) return "";
    return new Date(fecha).toLocaleString('es-CO');
  };

  const esErrorCritico = (archivo) => {
    if (!archivo.num_registros || archivo.num_registros === 0) return true;
    
if (archivo.errores && archivo.errores.some(e => {
      const error = e.toLowerCase();
      return (
        error.includes("vacío") || 
        error.includes("vacio") ||
        error.includes("corrupto") ||
        error.includes("sin datos") ||
        error.includes("nombre") ||
        error.includes("inválido") ||
        error.includes("invalido")
      );
    })) return true;
    
    return false;
  }

return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-800">Archivos Pendientes</h2>
        <p className="text-sm text-gray-600 mt-1">{archivos.length} archivo(s) esperando revisión</p>
      </div>

      <div className="divide-y divide-gray-200">
        {archivos.map((archivo) => {
          const critico = esErrorCritico(archivo);

          return (
            <div key={archivo.id} className={`p-6 transition-colors ${critico ? 'bg-red-50' : 'hover:bg-gray-50'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${archivo.tipo === 'XML' ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'}`}>
                      {archivo.tipo}
                    </span>
                    <h3 className="font-mono text-sm font-semibold text-gray-900">{archivo.nombre_archivo}</h3>
                    {critico && (
                      <span className="px-2 py-1 rounded text-xs font-bold bg-red-600 text-white flex items-center gap-1">
                        <XCircle className="w-4 h-4" /> INVÁLIDO
                      </span>
                    )}
                  </div>

                  <div className="flex gap-4 text-xs text-gray-600 mb-2">
                    <span>📅 {formatFecha(archivo.fecha_recepcion)}</span>
                    <span className={critico ? "font-bold text-red-600" : ""}>
                      📄 {archivo.num_registros || 0} registros
                    </span>
                    {archivo.tamano && <span>💾 {(archivo.tamano / 1024).toFixed(2)} KB</span>}
                  </div>

                  {archivo.errores && archivo.errores.length > 0 && (
                    <div className={`mt-2 p-3 rounded border text-xs ${
                      critico 
                        ? 'bg-white border-red-200 text-red-700' 
                        : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                    }`}>
                      <div className="flex items-center gap-2 font-bold mb-1">
                        {critico ? <XCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                        {critico ? 'Errores Bloqueantes:' : 'Advertencias:'}
                      </div>
                      <ul className="list-disc list-inside">
                        {archivo.errores.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <button 
                    onClick={() => onAprobar(archivo)} 
                    disabled={critico}
                    className={`flex items-center gap-1 px-3 py-2 rounded text-sm font-medium transition-all ${
                      critico 
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-50' 
                        : 'bg-green-600 text-white hover:bg-green-700 shadow-sm'
                    }`}
                    title={critico ? "No se puede aprobar un archivo vacío o inválido" : "Aprobar y procesar"}
                  >
                     <CheckCircle className="w-4 h-4" /> Aprobar
                  </button>
                  <button 
                    onClick={() => onRechazar(archivo)} 
                    className="flex items-center gap-1 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm shadow-sm"
                  >
                     <XCircle className="w-4 h-4" /> Rechazar
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}