import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class InternalApiClient:
    """Cliente para comunicarse con tu API local."""
    def __init__(self, config):
        self.base_url = config.internal_api.url.rstrip('/')
        self.user = config.internal_api.user
        self.password = config.internal_api.password
        self.session = requests.Session()
        self.token = None

    def authenticate(self):
        """Autentica con la API interna."""
        url = f"{self.base_url}/api/auth/login"
        payload = {
            "UserName": self.user,
            "PassWord": self.password
        }
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("token") or data.get("access_token")

            if self.token:
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                logger.info("Authentication successful")
            else:
                logger.error("Authentication failed: token not found in response")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def register_event(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Registra un evento en la API interna."""
        if not self.token:
            self.authenticate()
        
        url = f"{self.base_url}/api/aether/process-upload/"
        try:
            response = self.session.post(url, json=log_data, timeout=15)

            if response.status_code == 401:
                logger.warning("Token expired, re-authenticating...")
                self.authenticate()
                response = self.session.post(url, json=log_data, timeout=15)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to register event: {e}")
            raise

    def update_event(self, log_id: int, status_data: Dict[str, Any]):
        """Actualiza un evento en la API interna."""
        if not self.token:
            self.authenticate()
        
        url = f"{self.base_url}/api/aether/log/{log_id}"
        try:
            response = self.session.put(url, json=status_data, timeout=10)

            if response.status_code == 401:
                self.authenticate()
                response = self.session.put(url, json=status_data, timeout=10)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al actualizar estado del evento interno {log_id}: {e}")
            raise
        
    def create_service_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una orden de servicio en la API interna."""
        url = f"{self.base_url}/api/v1/service-orders/"
        try:
            response = self.session.post(url, json=order_data, timeout=15)
            response.raise_for_status()
            return {"status": "success", "data": response.json(), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create service order: {e}")
            return {"status": "error", "message": str(e), "details": response.text if response else None}
