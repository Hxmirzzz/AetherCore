"""
Configuración principal de la aplicación usando Pydantic v2.
"""
from pathlib import Path
from typing import List, Any
import os
import warnings
import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic.functional_validators import field_validator

class DatabaseConfig(BaseSettings):
    """
    Configuración de base de datos (Pydantic v2).
    """
    server: str = Field(..., alias='SQL_SERVER_PROD')
    database: str = Field(..., alias='SQL_DATABASE_PROD')
    username: str = Field(..., alias='SQL_USERNAME_PROD')
    password: str = Field(..., alias='SQL_PASSWORD_PROD')

    # Lee .env automáticamente
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )
    @property
    def connection_string(self) -> str:
        """Genera el connection string para SQL Server"""
        # Si quieres usar el driver de tu .env (TEST_SQL_DRIVER) cámbialo aquí.
        return (
            f'DRIVER={{SQL Server}};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password}'
        )

class TestDatabaseConfig(BaseSettings):
    driver: str = Field(..., alias='TEST_SQL_DRIVER')
    server: str = Field(..., alias='TEST_SQL_SERVER')
    database: str = Field(..., alias='TEST_SQL_DATABASE')
    username: str = Field(..., alias='TEST_SQL_USERNAME')
    password: str = Field(..., alias='TEST_SQL_PASSWORD')
    trusted: int = Field(default=0, alias='TEST_SQL_TRUSTED')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def connection_string(self) -> str:
        if self.trusted == 1:
            return (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
            )
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password}"
        )

class PathConfig(BaseSettings):
    """
    Configuración de rutas/carpetas de la aplicación.
    """
    # TXT
    carpeta_entrada_txt: Path = Field(..., alias='CARPETA_ENTRADA_TXT')
    carpeta_salida_txt: Path = Field(..., alias='CARPETA_SALIDA_TXT')
    carpeta_respuesta_txt: Path = Field(..., alias='CARPETA_RESPUESTA_TXT')
    carpeta_errores_txt: Path = Field(..., alias='CARPETA_ERRORES_TXT')

    # XML
    carpeta_entrada_xml: Path = Field(..., alias='CARPETA_ENTRADA_XML')
    carpeta_salida_xml: Path = Field(..., alias='CARPETA_SALIDA_XML')
    carpeta_gestionados_xml: Path = Field(..., alias='CARPETA_GESTIONADOS_XML')
    carpeta_errores_xml: Path = Field(..., alias='CARPETA_ERRORES_XML')

    # Gestionados
    carpeta_gestionados_txt: Path = Field(..., alias='CARPETA_GESTIONADOS_TXT')

    # Directorios derivados
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    logs_dir: Path | None = None

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        if self.logs_dir is None:
            object.__setattr__(self, 'logs_dir', self.base_dir / 'logs')

    @field_validator(
        'carpeta_entrada_txt', 'carpeta_entrada_xml',
        'carpeta_salida_txt', 'carpeta_salida_xml',
        'carpeta_respuesta_txt', 'carpeta_gestionados_txt',
        'carpeta_gestionados_xml', 'carpeta_errores_xml',
        'carpeta_errores_txt',
        mode='before'
    )
    @classmethod
    def validate_and_expand_path(cls, v: Any) -> Path:
        """Valida y expande rutas (maneja ~, variables de entorno, etc.)"""
        if v is None:
            return v
        v_str = str(v).strip().strip('"').strip("'")
        expanded = os.path.expandvars(os.path.expanduser(v_str))
        return Path(expanded).resolve()

    @property
    def log_file_unificado(self) -> Path:
        return self.logs_dir / 'VATCO-UNIFICADO-LOG.txt'

    @property
    def log_file_txt(self) -> Path:
        return self.logs_dir / 'VATCO-TXT2XLS-LOG.txt'

    @property
    def log_file_xml(self) -> Path:
        return self.logs_dir / 'VATCO-XML2XLS-LOG.txt'


class MonitoringConfig(BaseSettings):
    """
    Configuración de monitoreo y temporización.
    """
    tiempo_espera_segundos: int = Field(default=10, alias='TIEMPO_ESPERA_MONITOREO_GENERAL')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )
    
    @field_validator('tiempo_espera_segundos')
    @classmethod
    def validate_tiempo_espera(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('El tiempo de espera debe ser mayor a 0')
        return v

    @property
    def tiempo_espera_minutos(self) -> float:
        return self.tiempo_espera_segundos / 60.0


class JWTConfig(BaseSettings):
    """
    Configuración de autenticación JWT para la API.
    
    Variables de entorno requeridas:
    - JWT_SECRET_KEY: Clave secreta (mínimo 32 caracteres)
    - JWT_ALGORITHM: Algoritmo de encriptación (default: HS256)
    - JWT_EXPIRATION_HOURS: Horas de validez del token (default: 8)
    
    Para generar una clave segura:
        python -c "import secrets; print(secrets.token_urlsafe(64))"
    """
    secret_key: str = Field(
        default='CLAVE_INSEGURA_CAMBIAR_EN_PRODUCCION_' + secrets.token_urlsafe(32),
        alias='JWT_SECRET_KEY',
        description='Clave secreta para JWT'
    )
    algorithm: str = Field(
        default='HS256',
        alias='JWT_ALGORITHM',
        description='Algoritmo para JWT'
    )
    expiration_hours: int = Field(
        default=8,
        alias='JWT_EXPIRATION_HOURS',
        description='Expiración en horas para JWT'
    )

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que la clave secreta sea segura."""
        if len(v) < 32:
            raise ValueError(
                'JWT_SECRET_KEY debe tener al menos 32 caracteres. '
                'Genera una con: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        
        if v.startswith('CLAVE_INSEGURA_CAMBIAR_EN_PRODUCCION_'):
            warnings.warn(
                "\n" + "="*70 + "\n"
                "⚠️  ADVERTENCIA DE SEGURIDAD ⚠️\n"
                "="*70 + "\n"
                "Usando JWT_SECRET_KEY temporal. Para producción:\n\n"
                "1. Genera una clave segura:\n"
                "   python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n\n"
                "2. Agrégala a tu .env:\n"
                "   JWT_SECRET_KEY=tu_clave_generada_aqui\n"
                "="*70,
                UserWarning,
                stacklevel=2
            )
        
        return v

    @field_validator('expiration_hours')
    @classmethod
    def validate_expiration(cls, v: int) -> int:
        """Valida que la expiración sea razonable."""
        if v <= 0:
            raise ValueError('JWT_EXPIRATION_HOURS debe ser mayor a 0')
        if v > 720:  # 30 días
            warnings.warn(
                f"JWT_EXPIRATION_HOURS es muy alto ({v} horas = {v//24} días). "
                "Se recomienda 8-24 horas para mayor seguridad.",
                UserWarning
            )
        return v

class ValidationConfig(BaseSettings):
    """
    Configuración para reglas de negocio.
    """
    valid_filename_keyword: str = Field(
        default='',
        alias='VALID_FILENAME_KEYWORD',
        description='Palabra clave que deben tener los archivos (ej: EmpresaX, etc)'
    )

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

class AppConfig(BaseSettings):
    """
    Configuración general de la aplicación (Pydantic v2).
    """
    environment: str = Field(default='DEV', alias='APP_ENV')

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    database_test: TestDatabaseConfig = Field(default_factory=TestDatabaseConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    clientes_permitidos: List[str] = Field(default=['45', '46', '47', '48'])

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )
    @property
    def is_production(self) -> bool:
        return self.environment.upper() in ('PRD', 'PROD', 'PRODUCTION')

    @property
    def is_development(self) -> bool:
        return self.environment.upper() in ('DEV', 'DEVELOPMENT')


# Singleton
_config_instance: AppConfig | None = None

def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance

def reload_config() -> AppConfig:
    global _config_instance
    _config_instance = AppConfig()
    return _config_instance