from src.infrastructure.di.container import ApplicationContainer

# Inicializar contenedor de dependencias
container = ApplicationContainer()

# Obtener ConnectionManager
cm = container.connection_manager()

# ═════════════════════
# Paso 1: Obtener conexiones
# ═════════════════════
read_conn = cm.get_read_connection()
write_conn = cm.get_write_connection()

print("Antes de cerrar:")
print("Read alive:", read_conn.is_connected())
print("Write alive:", write_conn.is_connected())

# ═════════════════════
# Paso 2: Cerrar todas las conexiones
# ═════════════════════
cm.close_all()

print("\nDespués de close_all:")
# Las conexiones actuales quedan cerradas
print("Read alive:", read_conn.is_connected())
print("Write alive:", write_conn.is_connected())

# ═════════════════════
# Paso 3: Reconexión automática
# ═════════════════════
read_conn2 = cm.get_read_connection()    # Debe reconectar
write_conn2 = cm.get_write_connection()  # Debe reconectar

print("\nDespués de reconectar automáticamente:")
print("Read alive:", read_conn2.is_connected())
print("Write alive:", write_conn2.is_connected())

# Verificación simple
assert read_conn2.is_connected(), "Read connection no se reconectó"
assert write_conn2.is_connected(), "Write connection no se reconectó"

print("\n✅ Test #5 completado: cierre y reconexión funcionan correctamente")
