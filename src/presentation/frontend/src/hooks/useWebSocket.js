import { useEffect, useState, useRef } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export const useWebSocket = (url = `${WS_URL}/notificaciones`) => {
    const [mensajes, setMensajes] = useState([]);
    const [conectado, setConectado] = useState(false);
    const ws = useRef(null);

    useEffect(() => {
        ws.current = new WebSocket(url);
        
        ws.current.onopen = () => {
            console.log('WebSocket conectado');
            setConectado(true);
        };
        
        ws.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMensajes(prev => [...prev, data]);
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.current.onclose = () => {
            console.log('WebSocket desconectado');
            setConectado(false);
        };
        
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [url]);
    
    const enviarMensaje = (mensaje) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(mensaje));
        }
    };
    
    return { mensajes, conectado, enviarMensaje };
}