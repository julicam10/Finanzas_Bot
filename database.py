import sqlite3

def crear_base_datos():
    conexion = sqlite3.connect("finance_bot.db")
    cursor = conexion.cursor()

    # 1. Tabla de Presupuestos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presupuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT NOT NULL,
            limite REAL NOT NULL
        )
    """)

    # 2. Tabla de Transacciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            concepto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            monto REAL NOT NULL,
            metodo_pago TEXT NOT NULL
        )
    """)

    # 3. Tabla de Deudas (con soporte para saldo inicial, abonado y estado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deudas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deuda TEXT NOT NULL,
            monto_inicial REAL NOT NULL,
            monto_total REAL NOT NULL,
            cuota_mes REAL NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente'
        )
    """)

    # 4. Tabla de Metas de Ahorro (con soporte para estado completada)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas_ahorro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_meta TEXT NOT NULL,
            monto_objetivo REAL NOT NULL,
            monto_actual REAL NOT NULL,
            estrategia TEXT,
            estado TEXT NOT NULL DEFAULT 'En curso'
        )
    """)

    # 5. Tabla de Log de Abonos (Historial de pagos y ahorros)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_abonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,         -- 'Deuda' o 'Meta'
            referencia TEXT NOT NULL,   -- Nombre de la deuda o meta
            monto REAL NOT NULL         -- Valor del abono
        )
    """)

    # 6. Tabla de Inversiones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inversiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            activo TEXT NOT NULL,
            monto_invertido REAL NOT NULL
        )
    """)

    # 7. Tabla de Inversiones y Activos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inversiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            activo TEXT NOT NULL,
            monto_invertido REAL NOT NULL
        )
    """)

    conexion.commit()
    conexion.close()
    print("¡Base de datos actualizada con log de abonos y estados!")

if __name__ == "__main__":
    crear_base_datos()