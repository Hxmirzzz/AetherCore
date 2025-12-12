from src.infrastructure.config.settings import get_config
from src.infrastructure.database.connection_manager import ConnectionManager

def main():
    print("📌 Iniciando prueba de ConnectionManager...")

    cfg = get_config()
    manager = ConnectionManager(cfg)

    print("\n=== 🔍 PROBANDO CONEXIÓN DE LECTURA (PRODUCCIÓN) ===")
    read_conn = manager.get_read_connection()

    print("Clase:", type(read_conn).__name__)
    print("¿Conectado?:", read_conn.is_connected())
    print("Ejecutando SELECT 1...")

    try:
        result = read_conn.execute_scalar("SELECT 1")
        print("Resultado lectura:", result)
    except Exception as e:
        print("❌ Error en lectura:", e)

    print("\n=== 📝 PROBANDO CONEXIÓN DE ESCRITURA (TEST) ===")
    write_conn = manager.get_write_connection()

    print("Clase:", type(write_conn).__name__)
    print("¿Conectado?:", write_conn.is_connected())
    print("Ejecutando SELECT 1...")

    try:
        result = write_conn.execute_scalar("SELECT 1")
        print("Resultado escritura:", result)
    except Exception as e:
        print("❌ Error en escritura:", e)

    print("\nCerrando conexiones...")
    manager.close_all()
    print("✅ Conexiones cerradas correctamente.")

if __name__ == "__main__":
    main()