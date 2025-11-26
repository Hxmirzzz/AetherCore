import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock # MagicMock para simular objetos más complejos
from pathlib import Path
import logging

# Importar las clases y funciones a probar
from src.core.config import Config
from src.core.file_operations import FileOperations, ExcelStyler # Importamos ExcelStyler también si lo queremos probar
from src.core.logger_config import setup_logging # Necesario para configurar el logger de los tests

# Configurar un logger para los tests (opcional, pero útil para depurar tests)
# Usaremos un logger específico para evitar interferir con el logger principal de la app.
# Para pruebas, a menudo se usa un StreamHandler para ver los logs en la consola durante la ejecución del test.
@pytest.fixture(autouse=True) # autouse=True para que se ejecute antes de cada test
def setup_test_logger():
    # Configurar un logger temporal para las pruebas, dirigido a la consola.
    test_logger = logging.getLogger('TestFileOperations')
    test_logger.setLevel(logging.DEBUG) # Nivel DEBUG para ver todos los detalles en tests
    
    # Evitar duplicados de handlers si la fixture se ejecuta varias veces
    if not test_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
    
    # Mockear el logger real para que los logs del módulo se dirijan a nuestro test_logger
    # Esto es para que setup_logging en file_operations use nuestro logger simulado
    with patch('src.core.file_operations.logger', new=test_logger):
        yield

# --- Test para FileOperations.verificar_rutas_externas ---
def test_verificar_rutas_externas_todas_existen(tmp_path):
    """
    Verifica que verificar_rutas_externas retorna True cuando todas las carpetas existen.
    """
    # Configurar las rutas externas en Config para que apunten a rutas temporales simuladas.
    # Usamos tmp_path de pytest para crear directorios reales pero temporales.
    Config.CARPETA_ENTRADA_TXT = tmp_path / "entrada_txt"
    Config.CARPETA_SALIDA_TXT = tmp_path / "salida_txt"
    Config.CARPETA_RESPUESTA_TXT = tmp_path / "respuesta_txt"
    Config.CARPETA_ENTRADA_XML = tmp_path / "entrada_xml"
    Config.CARPETA_SALIDA_XML = tmp_path / "salida_xml"

    # Crear los directorios temporales que simulan existir.
    for path in [
        Config.CARPETA_ENTRADA_TXT, Config.CARPETA_SALIDA_TXT, Config.CARPETA_RESPUESTA_TXT,
        Config.CARPETA_ENTRADA_XML, Config.CARPETA_SALIDA_XML
    ]:
        path.mkdir()

    # Ejecutar la función a probar
    assert FileOperations.verificar_rutas_externas() is True

def test_verificar_rutas_externas_alguna_no_existe(tmp_path):
    """
    Verifica que verificar_rutas_externas retorna False cuando alguna carpeta no existe.
    """
    # Configurar solo algunas rutas para que existan
    Config.CARPETA_ENTRADA_TXT = tmp_path / "entrada_txt"
    Config.CARPETA_SALIDA_TXT = tmp_path / "salida_txt"
    Config.CARPETA_RESPUESTA_TXT = tmp_path / "respuesta_txt" # Esta no se creará
    Config.CARPETA_ENTRADA_XML = tmp_path / "entrada_xml"
    Config.CARPETA_SALIDA_XML = tmp_path / "salida_xml"

    # Crear solo algunos directorios
    Config.CARPETA_ENTRADA_TXT.mkdir()
    Config.CARPETA_SALIDA_TXT.mkdir()
    Config.CARPETA_ENTRADA_XML.mkdir()
    Config.CARPETA_SALIDA_XML.mkdir()

    # Esperar que retorne False porque 'respuesta_txt' no existe
    assert FileOperations.verificar_rutas_externas() is False

# --- Test para FileOperations.cargar_excel_a_dict ---
def test_cargar_excel_a_dict_exito(tmp_path):
    """
    Verifica que cargar_excel_a_dict carga un Excel correctamente a un diccionario.
    """
    # Crear un archivo Excel simulado temporalmente
    excel_path = tmp_path / "test_data.xlsx"
    df_test = pd.DataFrame({
        'CODIGO': ['C1', 'C2', 'C3'],
        'DESCRIPCION': ['Desc1', 'Desc2', 'Desc3']
    })
    df_test.to_excel(excel_path, index=False)

    expected_dict = {'C1': 'Desc1', 'C2': 'Desc2', 'C3': 'Desc3'}
    assert FileOperations.cargar_excel_a_dict(excel_path) == expected_dict

def test_cargar_excel_a_dict_archivo_no_existe():
    """
    Verifica que cargar_excel_a_dict retorna un diccionario vacío si el archivo no existe.
    """
    non_existent_path = Path("non_existent_file.xlsx")
    assert FileOperations.cargar_excel_a_dict(non_existent_path) == {}

def test_cargar_excel_a_dict_columnas_faltantes(tmp_path):
    """
    Verifica que cargar_excel_a_dict retorna un diccionario vacío si faltan columnas.
    """
    excel_path = tmp_path / "invalid_data.xlsx"
    df_test = pd.DataFrame({
        'OTRA_COL': ['V1'],
        'DESCRIPCION': ['V2']
    })
    df_test.to_excel(excel_path, index=False)

    # El test espera que no encuentre la columna 'CODIGO' por defecto
    assert FileOperations.cargar_excel_a_dict(excel_path, col_codigo='CODIGO') == {}

def test_cargar_excel_a_dict_col_codigo_es_numerica_pero_debe_ser_string(tmp_path):
    """
    Verifica que los códigos se conviertan a string incluso si son numéricos en Excel.
    """
    excel_path = tmp_path / "numeric_codes.xlsx"
    df_test = pd.DataFrame({
        'CODIGO': [1, 2, 3],
        'DESCRIPCION': ['Item A', 'Item B', 'Item C']
    })
    df_test.to_excel(excel_path, index=False)

    expected_dict = {'1': 'Item A', '2': 'Item B', '3': 'Item C'}
    assert FileOperations.cargar_excel_a_dict(excel_path) == expected_dict

# --- Puedes añadir más tests para ExcelStyler aquí si lo deseas ---
# Por ejemplo, mockeando un worksheet de openpyxl y verificando llamadas a celdas.
# Esto es más complejo y podría dejarse para más adelante.