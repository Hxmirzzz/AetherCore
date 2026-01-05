import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

export const archivoAPI = {
    obtenerPendientes: async () => {
        const response = await api.get('/archivos/pendientes');
        return response.data;
    },

    aprobar: async (archivoId, aprobado, comentario, usuario) => {
        const response = await api.post('/archivos/aprobar', {
            archivo_id: archivoId,
            aprobado,
            comentario,
            usuario
        });
        return response.data;
    },

    registrarNuevo: async (archivos) => {
        const response = await api.post('/archivos/nuevo', archivos);
        return response.data;
    }
};

export const healthAPI = {
    checkStatus: async () => {
        const response = await api.get('/health');
        return response.data;
    }
};

export default api;