import { useState } from "react";
import { authAPI } from "../services/api";
import { FileText, Lock, User, AlertCircle, LogIn } from "lucide-react";

export default function LoginPage({ onLogin }) {
    const [formData, setFormData] = useState({
        username: '',
        password: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            // 1. Llamada al Backend
            const data = await authAPI.login(formData.username, formData.password);

            // 2. Pasamos la respuesta completa a App.jsx.
            // NOTA: El backend devuelve 'access_token', no 'token'.
            // App.jsx (handleLogin) se encargará de guardar en localStorage.
            onLogin(data); 
            
        } catch (err) {
            console.error('Error al iniciar sesión:', err);
            
            // Manejo de errores basado en la respuesta del backend
            if (err.response?.status === 401) {
                setError('Usuario o contraseña incorrectos');
            } else if (err.response?.status === 403) {
                setError('Acceso denegado');
            } else if (err.response?.data?.detail) {
                // Si el backend envía un mensaje específico de error
                setError(err.response.data.detail);
            } else {
                setError('Error al iniciar sesión. Por favor, verifica tu conexión.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
        if (error) setError('');
    };
    
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 px-4">
      <div className="max-w-md w-full">
        {/* Logo y Título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl shadow-lg mb-4">
            <FileText className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            AetherCore
          </h1>
          <p className="text-gray-600">
            Sistema de Procesamiento de Archivos
          </p>
        </div>

        {/* Card de Login */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
            Iniciar Sesión
          </h2>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Formulario */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Campo Usuario */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Usuario
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  id="username"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Ingrese su usuario"
                  required
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Campo Contraseña */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Contraseña
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Ingrese su contraseña"
                  required
                  autoComplete="current-password"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Botón de Login */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Iniciando sesión...</span>
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  <span>Iniciar Sesión</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <div className="text-center mt-6 text-sm text-gray-500">
          <p>© 2026 AetherCore - Sistema de Procesamiento</p>
        </div>
      </div>
    </div>
  );
}