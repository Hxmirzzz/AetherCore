import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    }
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
      const originalRequest = error.config;
        if (error.response?.status === 401) {
          if (!originalRequest.url.includes('/auth/login')) {
            localStorage.removeItem('token');
            localStorage.removeItem('usuario');
            if (window.location.pathname !== '/') {
              window.location.href = '/';
            }
          }
        }
        return Promise.reject(error);
    }
);

export const authAPI = {
  /**
   * Inicia sesión con usuario y contraseña.
   * 
   * @param {string} username - Nombre de usuario
   * @param {string} password - Contraseña
   * @returns {Promise<{token: string, usuario: object}>}
   */
  login: async (username, password) => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },
  
  /**
   * Obtiene información del usuario actual (verifica token).
   * 
   * @returns {Promise<{usuario: object}>}
   */
  me: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  /**
   * Cierra sesión del usuario (opcional: llamar endpoint del backend)
   */
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    window.location.href = '/';
  }
};

export const archivoAPI = {
  /**
   * Obtiene la lista de archivos pendientes de aprobación.
   * 
   * @returns {Promise<Array>} Lista de archivos pendientes
   */
  obtenerPendientes: async () => {
    const response = await api.get('/archivos/pendientes');
    return response.data;
  },

  /**
   * Aprueba o rechaza un archivo.
   * 
   * @param {string} archivoId - ID del archivo
   * @param {boolean} aprobado - true para aprobar, false para rechazar
   * @param {string} comentario - Comentarios opcionales (requerido si rechaza)
   * @param {string} usuario - Usuario que realiza la acción (opcional, se obtiene del token)
   * @returns {Promise<object>} Resultado de la operación
   */
  aprobar: async (archivoId, aprobado, comentario = '', usuario = null) => {
    const response = await api.post('/archivos/aprobar', {
      archivo_id: archivoId,
      aprobado,
      comentarios: comentario,
    });
    return response.data;
  },

  /**
   * Registra nuevos archivos en el sistema.
   * 
   * @param {Array|object} archivos - Archivo(s) a registrar
   * @returns {Promise<object>} Resultado del registro
   */
  registrarNuevo: async (archivos) => {
    const response = await api.post('/archivos/nuevo', archivos);
    return response.data;
  },

  /**
   * Obtiene el historial de archivos procesados.
   * 
   * @param {object} filtros - Filtros opcionales (tipo, fecha_desde, fecha_hasta)
   * @returns {Promise<Array>} Lista de archivos procesados
   */
  obtenerHistorial: async (filtros = {}) => {
    const response = await api.get('/archivos/historial', { params: filtros });
    return response.data;
  }
};

export const estadisticasAPI = {
  /**
   * Obtiene estadísticas generales del sistema.
   * 
   * @returns {Promise<object>} Estadísticas del sistema
   */
  obtenerEstadisticas: async () => {
    const response = await api.get('/estadisticas');
    return response.data;
  }
};

export const healthAPI = {
  /**
   * Verifica el estado de la API.
   * 
   * @returns {Promise<object>} Estado del servidor
   */
  checkStatus: async () => {
    const response = await api.get('/health');
    return response.data;
  }
};

export default api;