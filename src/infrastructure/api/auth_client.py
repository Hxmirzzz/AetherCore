import os
import requests
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class AuthApiClient:
    def __init__(self):
        self.base_url = os.getenv("EXTERNAL_API_URL")
        self.username = os.getenv("EXTERNAL_API_USER")
        self.password = os.getenv("EXTERNAL_API_PASSWORD")
        self.token = None
    
    def _login(self):
        url = f"{self.base_url}/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("token")
            logger.info("Authentication successful")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def get_headers(self):
        """Devuelve los headers con el Bearer Token, haciendo login si es necesario."""
        if not self.token:
            self._login()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }