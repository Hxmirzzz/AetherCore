import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ExternalApiClient:
    """Cliente para comunicarse con la API de servicios externos."""

    def __init__(self, config):
        self.base_url = config.external_api.url.rstrip('/')
        self.user = config.external_api.user
        self.password = config.external_api.password
        self.session = requests.Session()
        self.token = None
    
    def authenticate(self):
        """Obtiene el token de acceso desde /auth/login."""
        url = f"{self.base_url}/auth/login/"
        payload = {
            "login": self.user,
            "password": self.password
        }
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("token") or data.get("access")

            if self.token:
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                logger.info("Authentication successful")
            else:
                logger.error("Authentication failed: token not found in response")
                raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def create_service_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una orden de servicio en la API externa."""
        if not self.token:
            self.authenticate()

        url = f"{self.base_url}/api/v1/service-orders/"
        try:
            response = self.session.post(url, json=order_data, timeout=15)
            response.raise_for_status()
            return {"status": "success", "data": response.json(), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create service order: {e}")
            return {"status": "error", "message": str(e), "details": response.text if response else None}
            
    def create_bulk_orders(self, orders_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Crea múltiples órdenes de servicio en la API externa."""
        if not self.token:
            self.authenticate()

        url = f"{self.base_url}/api/v1/service-orders/bulk/"
        payload = {"orders": orders_list}

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return {"status": "success", "data": response.json(), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create bulk orders: {e}")
            try:
                error_data = response.json()
            except:
                error_data = response.text if response else "Unknown Error"
                
            return {"status": "error", "message": str(e), "details": error_data}

    def get_clients_mapping(self) -> Dict[str, Any]:
        """Descarga los clientes y devuelve un diccionario mapeando el client_code con el nombre."""
        if not self.token:
            self.authenticate()

        url = f"{self.base_url}/clients/"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            clients_data = response.json()
            
            mapping = {}
            for client in clients_data:
                nit = str(client.get("tax_identification", "")).strip()
                code = client.get("client_code", "")
                name = client.get("commercial_name", "") or client.get("business_name", "")
                if nit and code:
                    mapping[nit] = {
                        "code": code,
                        "name": name
                    }
            return mapping
        except Exception as e:
            logger.error(f"Unexpected error getting clients mapping: {e}")
            return {}

    def get_service_types_mapping(self) -> Dict[str, str]:
        """
        Descarga los tipos de servicio y devuelve un diccionario { "name": "code" }.
        Ejemplo: { "RECOLECCION": "RC" }
        """
        if not self.token:
            self.authenticate()

        url = f"{self.base_url}/api/v1/service-types/"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            service_types_data = response.json()
            mapping = {}
            for service_type in service_types_data:
                name = service_type.get("name", "").upper()
                code = service_type.get("code", "")
                if code and name:
                    mapping[name] = code
            return mapping
        except Exception as e:
            logger.error(f"Unexpected error getting service types mapping: {e}")
            return {}