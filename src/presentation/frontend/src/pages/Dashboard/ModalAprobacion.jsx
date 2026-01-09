import { useState } from 'react';
import { X, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export default function ModalAprobacion({ archivo, tipo, onConfirmar, onCancelar }) {
  const [comentarios, setComentarios] = useState('');
  const [enviando, setEnviando] = useState(false);

  const esAprobacion = tipo === 'aprobar';

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validar que haya comentarios si es rechazo
    if (!esAprobacion && !comentarios.trim()) {
      alert('Por favor, ingresa un comentario explicando el motivo del rechazo');
      return;
    }

    setEnviando(true);
    try {
      await onConfirmar(archivo, esAprobacion, comentarios.trim() || null);
    } catch (error) {
      console.error('Error en modal:', error);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden animate-slideUp">
        {/* Header */}
        <div className={`px-6 py-5 border-b ${
          esAprobacion 
            ? 'bg-gradient-to-r from-green-500 to-emerald-600' 
            : 'bg-gradient-to-r from-red-500 to-rose-600'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {esAprobacion ? (
                <div className="bg-white/20 backdrop-blur-sm p-2 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
              ) : (
                <div className="bg-white/20 backdrop-blur-sm p-2 rounded-lg">
                  <XCircle className="w-6 h-6 text-white" />
                </div>
              )}
              <h2 className="text-xl font-bold text-white">
                {esAprobacion ? 'Aprobar Archivo' : 'Rechazar Archivo'}
              </h2>
            </div>
            
            <button
              onClick={onCancelar}
              className="text-white/80 hover:text-white hover:bg-white/10 p-2 rounded-lg transition-colors"
              disabled={enviando}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Información del Archivo */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Información del archivo
            </h3>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Nombre:</span>
                <span className="font-mono font-medium text-gray-900 text-right break-all">
                  {archivo.nombre_archivo}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Tipo:</span>
                <span className={`px-2 py-0.5 rounded font-semibold ${
                  archivo.tipo === 'XML' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'bg-purple-100 text-purple-700'
                }`}>
                  {archivo.tipo}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Registros:</span>
                <span className="font-semibold text-gray-900">
                  {archivo.num_registros || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Mensaje de Advertencia para Rechazo */}
          {!esAprobacion && (
            <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg p-4 mb-6">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-yellow-900 mb-1">
                    Atención
                  </p>
                  <p className="text-xs text-yellow-700">
                    El archivo será rechazado y devuelto al origen. Por favor, explica el motivo del rechazo.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Campo de Comentarios */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {esAprobacion ? 'Comentarios (opcional)' : 'Motivo del rechazo *'}
            </label>
            <textarea
              value={comentarios}
              onChange={(e) => setComentarios(e.target.value)}
              placeholder={
                esAprobacion 
                  ? 'Agrega cualquier observación sobre este archivo...'
                  : 'Explica el motivo del rechazo...'
              }
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none text-sm"
              rows="4"
              required={!esAprobacion}
              disabled={enviando}
            />
          </div>

          {/* Botones de Acción */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancelar}
              disabled={enviando}
              className="flex-1 px-4 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancelar
            </button>
            
            <button
              type="submit"
              disabled={enviando}
              className={`flex-1 px-4 py-3 font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
                esAprobacion
                  ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg shadow-green-500/30'
                  : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white shadow-lg shadow-red-500/30'
              }`}
            >
              {enviando ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  {esAprobacion ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Confirmar Aprobación
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      Confirmar Rechazo
                    </>
                  )}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}