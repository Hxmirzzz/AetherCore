import { useEffect, useState, useRef } from 'react';

export const useWebSocket = () => {
    const [mensajes, setMensajes] = useState([]);
    const [conectado, setConectado] = useState(false);
    const ws = useRef(null);

    useEffect(() => {
        const token = localStorage.getItem('token');

        if (!token) {
            console.warn("No hay token para conectar al WebSocket");
            return;
        }

        // --- CORRECCIÓN DE URL ---
        // 1. Obtenemos la variable de entorno o el default
        let baseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
        
        // 2. Limpieza agresiva: Quitamos cualquier barra o '/ws' al final para empezar limpios
        // Esto convierte 'ws://localhost:8000/ws/' -> 'ws://localhost:8000'
        baseUrl = baseUrl.replace(/\/ws\/?$/, '').replace(/\/$/, '');

        // 3. Construimos la ruta correcta
        const wsUrl = `${baseUrl}/ws/notificaciones?token=${token}`;
        // -------------------------

        console.log(`🔌 Conectando a: ${wsUrl}`);
        
        ws.current = new WebSocket(wsUrl);
        
        ws.current.onopen = () => {
            console.log('✅ WebSocket conectado exitosamente');
            setConectado(true);
        };
        
        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("📩 Notificación recibida:", data);
                setMensajes(prev => [...prev, data]);
            } catch (e) {
                console.error("Error parseando mensaje WS:", e);
            }
        };

        ws.current.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
        
        ws.current.onclose = (event) => {
            console.log(`WebSocket desconectado (Código: ${event.code})`);
            setConectado(false);
            
            // 403 suele ser error de autenticación o ruta prohibida
            if (event.code === 1008 || event.code === 403) {
                console.error("Desconexión por política de seguridad (Token inválido o Ruta errónea)");
            }
        };
        
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []); 
    
    return { mensajes, conectado };
}