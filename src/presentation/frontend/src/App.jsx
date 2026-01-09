import { useState, useEffect } from 'react';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import { authAPI } from './services/api';

function App() {
  const [usuario, setUsuario] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verificarSesion = async () => {
      const token = localStorage.getItem('token');
      
      if (token) {
        try {
          console.log("Token detectado, verificando con backend...");
          // Intentamos obtener los datos frescos del usuario
          const data = await authAPI.me();
          setUsuario(data);
          console.log("Sesión validada correctamente");
        } catch (error) {
          console.error("Error validando sesión:", error);
          // Si el token no sirve (401 o error de red), limpiamos todo
          localStorage.removeItem('token');
          localStorage.removeItem('usuario');
          setUsuario(null);
        }
      } else {
        console.log("No hay token guardado");
      }

      // IMPORTANTE: Esto se ejecuta SIEMPRE al final, funcione o falle.
      // Esto es lo que quita la pantalla de "Verificando sesión..."
      setLoading(false);
    };

    verificarSesion();
  }, []);

  const handleLogin = (datosLogin) => {
    // Guardamos en localStorage
    localStorage.setItem('token', datosLogin.access_token);
    // Guardamos una copia básica del usuario
    localStorage.setItem('usuario', JSON.stringify(datosLogin.usuario));
    setUsuario(datosLogin.usuario);
  };
  
  const handleLogout = () => {
    authAPI.logout();
    setUsuario(null);
  };

  // Pantalla de Carga
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  // Si hay usuario, mostramos Dashboard. Si no, Login.
  return usuario ? 
    <Dashboard usuario={usuario} onLogout={handleLogout} /> : 
    <LoginPage onLogin={handleLogin} />;
}

export default App;