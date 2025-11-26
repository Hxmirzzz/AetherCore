# mi_aplicacion/tests/test_database_helper.py

import pytest
from unittest.mock import patch, MagicMock
import logging
import sys
import pyodbc

from src.core.config import Config
from src.core.database_helper import DatabaseHelper
from src.core.logger_config import setup_logging

@pytest.fixture(autouse=True)
def setup_test_logger():
    test_logger = logging.getLogger('TestDatabaseHelper')
    test_logger.setLevel(logging.DEBUG)
    # Evitar duplicados de handlers si la fixture se ejecuta varias veces
    if not test_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
    with patch('src.core.database_helper.logger', new=test_logger):
        yield

@pytest.fixture
def mock_db_connection():
    """
    Mockea la conexión a la base de datos y el cursor para los tests.
    El cursor mockeado se devuelve directamente sin un context manager especial,
    ya que el cierre se maneja con un try-finally en el DatabaseHelper.
    """
    with patch('src.core.database_helper.pyodbc.connect') as mock_connect:
        mock_conn = MagicMock(spec=pyodbc.Connection)
        mock_connect.return_value = mock_conn

        mock_cursor = MagicMock(spec=pyodbc.Cursor)

        # La conexión mockeada llamará a .cursor() y devolverá este mock_cursor
        mock_conn.cursor.return_value = mock_cursor

        yield mock_connect, mock_conn, mock_cursor

# --- Tests para DatabaseHelper.conectar_bd (Estos ya estaban bien) ---
def test_conectar_bd_exito(mock_db_connection):
    mock_connect, mock_conn, _ = mock_db_connection
    conn = DatabaseHelper.conectar_bd()
    assert conn is not None
    assert conn == mock_conn
    mock_connect.assert_called_once()

def test_conectar_bd_falla_conexion():
    with patch('src.core.database_helper.pyodbc.connect', side_effect=pyodbc.Error("Connection failed")) as mock_connect:
        conn = DatabaseHelper.conectar_bd()
        assert conn is None
        mock_connect.assert_called_once()

# --- Tests para DatabaseHelper.obtener_ciudades (Corregido el cierre del cursor en el fallo) ---
def test_obtener_ciudades_exito(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    mock_row1 = MagicMock(cod_ciudad=1, ciudad="Bogota")
    mock_row2 = MagicMock(cod_ciudad=2, ciudad="Medellin")
    mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
    ciudades = DatabaseHelper.obtener_ciudades(mock_conn)
    assert ciudades == {"1": "Bogota", "2": "Medellin"}
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SELECT cod_ciudad, ciudad FROM adm_ciudades")
    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once() # Ahora debería pasar por __exit__ y llamarse

def test_obtener_ciudades_falla_db(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    mock_cursor.execute.side_effect = pyodbc.Error("Query failed")
    ciudades = DatabaseHelper.obtener_ciudades(mock_conn)
    assert ciudades == {}
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once() # Ahora debería pasar por __exit__ y llamarse

# --- Tests para obtener_sucursales, obtener_clientes, obtener_puntos_clientes ---
# (Asegúrate de que estas también tengan mock_cursor.close.assert_called_once())
# Aquí solo muestro un ejemplo, aplica la misma lógica a los demás

def test_obtener_sucursales_exito(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    mock_row1 = MagicMock(cod_p_cliente=100, cod_suc=1, sucursal="Sucursal A")
    mock_row2 = MagicMock(cod_p_cliente=101, cod_suc=2, sucursal="Sucursal B")
    mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
    expected_sucursales = {
        "100": {"cod_suc": "1", "sucursal": "1 - Sucursal A"},
        "101": {"cod_suc": "2", "sucursal": "2 - Sucursal B"},
    }
    sucursales = DatabaseHelper.obtener_sucursales(mock_conn)
    assert sucursales == expected_sucursales
    mock_conn.cursor.assert_called_once()
    mock_cursor.close.assert_called_once()

# ... (rest of simple tests like obtener_clientes_exito, obtener_puntos_clientes_exito, etc.)

# --- Tests para DatabaseHelper.obtener_codigos_cliente_unicos ---
def test_obtener_codigos_cliente_unicos_exito(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    mock_row1 = MagicMock(cod_cliente=47)
    mock_row2 = MagicMock(cod_cliente=48)
    mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
    codigo_puntos = ["P1", "P2"]
    clientes = DatabaseHelper.obtener_codigos_cliente_unicos(mock_conn, codigo_puntos)
    assert clientes == ["47", "48"]
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()

def test_obtener_codigos_cliente_unicos_lista_vacia_de_puntos(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    clientes = DatabaseHelper.obtener_codigos_cliente_unicos(mock_conn, [])
    assert clientes == []
    mock_conn.cursor.assert_not_called()
    mock_cursor.execute.assert_not_called()
    mock_cursor.close.assert_not_called()


# --- Tests para DatabaseHelper.obtener_cod_cliente_por_punto (Correcciones Clave) ---
def test_obtener_cod_cliente_por_punto_exito_exacto(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'47': '02', '46': '01'} 
    mock_row = MagicMock(cod_cliente=47)
    mock_cursor.fetchone.side_effect = [mock_row] # SOLO UNA LLAMADA: el test es para 'exito_exacto'
    client_code = DatabaseHelper.obtener_cod_cliente_por_punto(mock_conn, "47-6081")
    assert client_code == "47"
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once() # SOLO LA PRIMERA CONSULTA
    mock_cursor.close.assert_called_once()

def test_obtener_cod_cliente_por_punto_exito_like(mock_db_connection):
    """
    Verifica que obtener_cod_cliente_por_punto encuentra el cliente por patrón LIKE.
    """
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'47': '02', '46': '01'} 
    mock_row = MagicMock(cod_cliente=47)
    mock_cursor.fetchone.side_effect = [None, mock_row] # Exacta no devuelve, LIKE sí.
    client_code = DatabaseHelper.obtener_cod_cliente_por_punto(mock_conn, "6081")
    assert client_code == "47"
    mock_conn.cursor.assert_called_once()
    assert mock_cursor.execute.call_count == 2 # Ambas consultas
    mock_cursor.close.assert_called_once()

def test_obtener_cod_cliente_por_punto_no_encontrado(mock_db_connection):
    """
    Verifica que obtener_cod_cliente_por_punto retorna None si NO se encuentra el cliente
    (ni por exacta ni por LIKE).
    """
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'47': '02'}
    mock_cursor.fetchone.side_effect = [None, None] # Ninguna consulta devuelve nada
    client_code = DatabaseHelper.obtener_cod_cliente_por_punto(mock_conn, "9999")
    assert client_code is None
    mock_conn.cursor.assert_called_once()
    assert mock_cursor.execute.call_count == 2 # Ambas consultas
    mock_cursor.close.assert_called_once()

def test_obtener_cod_cliente_por_punto_cliente_no_permitido(mock_db_connection):
    """
    Verifica que obtener_cod_cliente_por_punto retorna None si el cliente NO está en CLIENTE_TO_CC.
    El mock del cursor DEBE simular que la consulta SQL (con el IN) NO devuelve ninguna fila
    para un cliente NO permitido, ya que la DB real filtraría esto.
    """
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'48': '23'} # Solo permitimos el 48
    
    # La consulta SQL 'AND c.cod_cliente IN (...)' filtra clientes no permitidos.
    # Por lo tanto, el mock del cursor NO debe devolver una fila si el cliente no está permitido.
    mock_cursor.fetchone.side_effect = [None, None] # Simula que la DB no devuelve nada (porque el cliente '1' no está en el IN)

    client_code = DatabaseHelper.obtener_cod_cliente_por_punto(mock_conn, "1-1234") # Buscamos un punto que mapearía a cliente '1'
    assert client_code is None 
    mock_conn.cursor.assert_called_once()
    assert mock_cursor.execute.call_count == 2 # Ambas consultas se ejecutan, pero ninguna devuelve nada
    mock_cursor.close.assert_called_once()

# --- Tests para DatabaseHelper.obtener_cod_cliente_por_nit (Corregido Cliente no Permitido) ---
def test_obtener_cod_cliente_por_nit_exito(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'47': '02'} 
    mock_row = MagicMock(cod_cliente=47)
    mock_cursor.fetchone.return_value = mock_row
    client_code = DatabaseHelper.obtener_cod_cliente_por_nit(mock_conn, "123456789")
    assert client_code == "47"
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()

def test_obtener_cod_cliente_por_nit_no_encontrado(mock_db_connection):
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'47': '02'}
    mock_cursor.fetchone.return_value = None
    client_code = DatabaseHelper.obtener_cod_cliente_por_nit(mock_conn, "non_existent_nit")
    assert client_code is None
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()

def test_obtener_cod_cliente_por_nit_cliente_no_permitido(mock_db_connection):
    """
    Verifica que obtener_cod_cliente_por_nit retorna None si el cliente del NIT NO está en CLIENTE_TO_CC.
    El mock del cursor DEBE simular que la consulta SQL (con el IN) NO devuelve ninguna fila
    para un cliente NO permitido.
    """
    _, mock_conn, mock_cursor = mock_db_connection
    Config.CLIENTE_TO_CC = {'48': '23'} # Solo permitimos el 48
    
    # La consulta SQL 'AND c.cod_cliente IN (...)' filtra clientes no permitidos.
    # Por lo tanto, el mock del cursor NO debe devolver una fila si el cliente no está permitido.
    mock_cursor.fetchone.return_value = None # Simula que la DB no devuelve nada.

    client_code = DatabaseHelper.obtener_cod_cliente_por_nit(mock_conn, "some_nit") # Buscamos un NIT que mapearía a cliente '1'
    assert client_code is None 
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()