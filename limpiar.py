import sqlite3

conexion = sqlite3.connect("finance_bot.db")
cursor = conexion.cursor()

# Lista de tablas a vaciar
tablas = [
    "transacciones",
    "deudas",
    "metas_ahorro",
    "log_abonos",
    "inversiones",
    "presupuestos",
]

for tabla in tablas:
  cursor.execute(f"DELETE FROM {tabla};")

# Reinicia los contadores de ID autoincrementables
cursor.execute("DELETE FROM sqlite_sequence;")

conexion.commit()
conexion.close()

print("✨ Base de datos reiniciada y vaciada con éxito.")