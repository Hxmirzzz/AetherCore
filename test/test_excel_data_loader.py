import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
import logging

# Importar las clases a probar
from src.core.config import Config
from src.data_managers.excel_data_loader import ExcelDataLoader
from src.core.file_operations import FileOperations # Necesario para mockearlo
from src.core.logger_config import setup_logging # Necesario para configurar el logger de los tests

# Configurar un logger para los tests (opcional, pero útil para depurar tests)
@pytest.fixture(autouse=True)
def setup_test_logger():
    test_logger = logging.getLogger('TestExcelDataLoader')
    test_logger.setLevel(logging.DEBUG)
    if not test_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
    
    # Mockear el logger real para que los logs del módulo se dirijan a nuestro test_logger
    with patch('src.data_managers.excel_data_loader.logger', new=test_logger):
        yield
    
    # Limpiar la caché de ExcelDataLoader después de cada test para asegurar aislamiento
    ExcelDataLoader._tipos_servicio = None
    ExcelDataLoader._categorias = None
    ExcelDataLoader._tipo_valor = None


# --- Tests para ExcelDataLoader.get_tipos_servicio ---
def test_get_tipos_servicio_carga_correctamente():
    """
    Verifica que get_tipos_servicio carga los datos y los almacena en caché.
    """
    mock_data = {"TS1": "Tipo Servicio 1", "TS2": "Tipo Servicio 2"}
    
    # Mockear la función cargar_excel_a_dict de FileOperations para que devuelva datos simulados
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value=mock_data) as mock_cargar_excel:
        # Primera llamada: debería cargar los datos
        result = ExcelDataLoader.get_tipos_servicio()
        assert result == mock_data
        mock_cargar_excel.assert_called_once_with(Config.RUTA_TIPO_SERVICIO) # Verificar que se llamó con la ruta correcta

        # Segunda llamada: debería devolver los datos en caché sin llamar a cargar_excel_a_dict de nuevo
        result_cached = ExcelDataLoader.get_tipos_servicio()
        assert result_cached == mock_data
        mock_cargar_excel.assert_called_once() # Asegurarse de que no se llamó una segunda vez

def test_get_tipos_servicio_maneja_error_carga():
    """
    Verifica que get_tipos_servicio devuelve un diccionario vacío si la carga falla.
    """
    # Mockear cargar_excel_a_dict para que devuelva un diccionario vacío (simulando fallo de carga)
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value={}) as mock_cargar_excel:
        result = ExcelDataLoader.get_tipos_servicio()
        assert result == {}
        mock_cargar_excel.assert_called_once()

# --- Tests para ExcelDataLoader.get_categorias ---
def test_get_categorias_carga_correctamente():
    """
    Verifica que get_categorias carga los datos y los almacena en caché.
    """
    mock_data = {"CAT1": "Categoria 1", "CAT2": "Categoria 2"}
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value=mock_data) as mock_cargar_excel:
        result = ExcelDataLoader.get_categorias()
        assert result == mock_data
        mock_cargar_excel.assert_called_once_with(Config.RUTA_CATEGORIA)

def test_get_categorias_maneja_error_carga():
    """
    Verifica que get_categorias devuelve un diccionario vacío si la carga falla.
    """
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value={}) as mock_cargar_excel:
        result = ExcelDataLoader.get_categorias()
        assert result == {}
        mock_cargar_excel.assert_called_once()

# --- Tests para ExcelDataLoader.get_tipo_valor ---
def test_get_tipo_valor_carga_correctamente():
    """
    Verifica que get_tipo_valor carga los datos y los almacena en caché.
    """
    mock_data = {"TV1": "Tipo Valor 1", "TV2": "Tipo Valor 2"}
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value=mock_data) as mock_cargar_excel:
        result = ExcelDataLoader.get_tipo_valor()
        assert result == mock_data
        mock_cargar_excel.assert_called_once_with(Config.RUTA_TIPO_VALOR)

def test_get_tipo_valor_maneja_error_carga():
    """
    Verifica que get_tipo_valor devuelve un diccionario vacío si la carga falla.
    """
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', return_value={}) as mock_cargar_excel:
        result = ExcelDataLoader.get_tipo_valor()
        assert result == {}
        mock_cargar_excel.assert_called_once()

# --- Tests para ExcelDataLoader.recargar_todos_los_datos ---
def test_recargar_todos_los_datos_fuerza_recarga():
    """
    Verifica que recargar_todos_los_datos invalida la caché y fuerza nuevas cargas.
    """
    # Preparar con algunos datos en caché
    mock_ts_data_initial = {"TS_OLD": "Old Service Type"}
    mock_cat_data_initial = {"CAT_OLD": "Old Category"}
    mock_tv_data_initial = {"TV_OLD": "Old Type Value"}

    # Mockear las primeras cargas
    with patch('src.core.file_operations.FileOperations.cargar_excel_a_dict', side_effect=[
        mock_ts_data_initial, # Para la primera llamada a get_tipos_servicio
        mock_cat_data_initial, # Para la primera llamada a get_categorias
        mock_tv_data_initial   # Para la primera llamada a get_tipo_valor
    ]) as mock_cargar_excel:
        # Cargar los datos por primera vez
        ExcelDataLoader.get_tipos_servicio()
        ExcelDataLoader.get_categorias()
        ExcelDataLoader.get_tipo_valor()
        assert mock_cargar_excel.call_count == 3 # Verificamos que se cargaron 3 veces

        # Mockear datos nuevos para la recarga
        mock_ts_data_new = {"TS_NEW": "New Service Type"}
        mock_cat_data_new = {"CAT_NEW": "New Category"}
        mock_tv_data_new = {"TV_NEW": "New Type Value"}

        # Resetear el mock y configurarlo para las nuevas devoluciones
        mock_cargar_excel.reset_mock()
        mock_cargar_excel.side_effect = [
            mock_ts_data_new,
            mock_cat_data_new,
            mock_tv_data_new
        ]

        # Recargar todos los datos
        ExcelDataLoader.recargar_todos_los_datos()

        # Verificar que se intentaron recargar los 3 tipos de datos
        assert mock_cargar_excel.call_count == 3

        # Verificar que get_* ahora devuelve los nuevos datos
        assert ExcelDataLoader.get_tipos_servicio() == mock_ts_data_new
        assert ExcelDataLoader.get_categorias() == mock_cat_data_new
        assert ExcelDataLoader.get_tipo_valor() == mock_tv_data_new
        # La llamada a get_* después de recargar NO debería contar como una nueva llamada a cargar_excel_a_dict
        assert mock_cargar_excel.call_count == 3 # Todavía 3, no 6

def test_get_ciudades_siempre_vacio_con_warning():
    """
    Verifica que get_ciudades siempre devuelve un diccionario vacío y emite un warning.
    """
    with patch('src.data_managers.excel_data_loader.logger.warning') as mock_warning:
        result = ExcelDataLoader.get_ciudades()
        assert result == {}
        mock_warning.assert_called_once_with(
            "Advertencia: Se solicitó 'ciudades' a ExcelDataLoader. Las ciudades se obtienen de la base de datos (DatabaseHelper) y no se gestionan en este módulo. Devolviendo diccionario vacío."
        )