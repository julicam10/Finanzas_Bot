import os
import sqlite3
import unicodedata
from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "7770957118:AAHQTQ4PLdrJ1YRH3Z_U-9T1IB_3KXstLI0")

app = Flask(__name__)


def ejecutar_sql(query, params=()):
  conexion = sqlite3.connect("finance_bot.db")
  cursor = conexion.cursor()
  cursor.execute(query, params)
  conexion.commit()
  conexion.close()


def consultar_sql(query, params=()):
  conexion = sqlite3.connect("finance_bot.db")
  cursor = conexion.cursor()
  cursor.execute(query, params)
  resultados = cursor.fetchall()
  conexion.close()
  return resultados


def normalizar_texto(texto):
  return "".join(
      c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
  ).lower()


def clasificar_gasto(concepto):
  c_lower = normalizar_texto(concepto)

  # Mapeo basado en tu distribución oficial (convertido a minúsculas para evaluar sin errores)
  if any(w in c_lower for w in ["S&P500", "TSMC"]):
    return "Inversión"
  elif any(
      w in c_lower
      for w in ["Fondeloitte", "Ahorro personal", "Ahorro ropa", "Ahorro viajes"]
  ):
    return "Ahorro"
  elif any(w in c_lower for w in ["Arriendo"]):
    return "Casa / Obligaciones"
  elif any(
      w in c_lower
      for w in ["Huevo", "Proteina", "Carne", "D1", "Ara", "Éxito", "Fruta", "Verdura"]
  ):
    return "Mercado"
  elif any(w in c_lower for w in ["Hamburguesa", "Pizza", "Arepas", "Papas king", "Comida fuera"]):
    return "Comida fuera"
  elif any(w in c_lower for w in ["Barberia", "Gimnasio"]):
    return "Bienestar y Cuidado"
  elif any(w in c_lower for w in ["Comida alma", "Arena alma"]):
    return "Mascota (Alma)"
  elif any(w in c_lower for w in ["Netflix", "Youtube", "Google fotos"]):
    return "Suscripciones"
  elif any(w in c_lower for w in ["Paquete de datos", "Datos"]):
    return "Servicios"
  elif any(
      w in c_lower
      for w in ["Crédito hipotecario", "Pago ipad", "T.C Nu", "T.C Bancolombia"]
  ):
    return "Pago deudas"
  elif any(
      w in c_lower
      for w in ["Salida con amigos", "Transporte", "Pasaje", "Cine", "Salida"]
  ):
    return "Gastos del mes"
  else:
    return "Gastos del mes"  # Categoría por defecto si no coincide con ninguna


# Configuración de la aplicación de Telegram para Webhook
telegram_app = ApplicationBuilder().token(TOKEN).build()


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
  texto_usuario = update.message.text
  fecha_hoy = datetime.now().strftime("%Y-%m-%d")

  try:
    lineas = [l.strip() for l in texto_usuario.split("\n") if l.strip()]
    if not lineas:
      return
    primera_linea_lower = normalizar_texto(lineas[0])

    # CASO 1: ABONO A DEUDA
    if "abono" in primera_linea_lower:
      if len(lineas) < 3:
        await update.message.reply_text("⚠️ Formato de abono incompleto.")
        return
      monto_str = (
          lineas[1].replace("$", "").replace(".", "").replace(",", "")
      )
      monto = float(monto_str)
      nombre_deuda_buscada = lineas[2]

      deudas_db = consultar_sql(
          "SELECT deuda, monto_total FROM deudas WHERE estado != 'Completada'"
      )
      deuda_encontrada = None
      for d in deudas_db:
        if normalizar_texto(nombre_deuda_buscada) in normalizar_texto(d[0]):
          deuda_encontrada = d[0]
          saldo_actual = d[1]
          break

      if not deuda_encontrada:
        await update.message.reply_text("⚠️ No encontré esa deuda activa.")
        return

      nuevo_monto = max(0, saldo_actual - monto)
      nuevo_estado = "Completada" if nuevo_monto == 0 else "Pendiente"
      ejecutar_sql(
          "UPDATE deudas SET monto_total = ?, estado = ? WHERE deuda = ?",
          (nuevo_monto, nuevo_estado, deuda_encontrada),
      )
      ejecutar_sql(
          "INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?,"
          " ?, ?, ?)",
          (fecha_hoy, "Deuda", deuda_encontrada, monto),
      )
      await update.message.reply_text(
          f"💳 **¡Abono aplicado!**\nSaldo: $ {nuevo_monto:,.0f} COP"
      )
      return

    # CASO 2: META DE AHORRO
    elif "meta" in primera_linea_lower or "ahorro" in primera_linea_lower:
      if len(lineas) < 3:
        await update.message.reply_text("⚠️ Formato de meta incompleto.")
        return
      monto_str = (
          lineas[1].replace("$", "").replace(".", "").replace(",", "")
      )
      monto = float(monto_str)
      nombre_meta_buscada = lineas[2]

      metas_db = consultar_sql(
          "SELECT nombre_meta, monto_actual, monto_objetivo FROM metas_ahorro"
          " WHERE estado != 'Completada'"
      )
      meta_encontrada = None
      for m in metas_db:
        if normalizar_texto(nombre_meta_buscada) in normalizar_texto(m[0]):
          meta_encontrada = m[0]
          ahorro_actual = m[1]
          monto_obj = m[2]
          break

      if not meta_encontrada:
        await update.message.reply_text("⚠️ No encontré esa meta en curso.")
        return

      nuevo_ahorro = ahorro_actual + monto
      nuevo_estado_meta = (
          "Completada" if nuevo_ahorro >= monto_obj else "En curso"
      )
      ejecutar_sql(
          "UPDATE metas_ahorro SET monto_actual = ?, estado = ? WHERE"
          " nombre_meta = ?",
          (nuevo_ahorro, nuevo_estado_meta, meta_encontrada),
      )
      ejecutar_sql(
          "INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?,"
          " ?, ?, ?)",
          (fecha_hoy, "Meta", meta_encontrada, monto),
      )
      await update.message.reply_text(
          f"💰 **¡Aporte registrado!**\nAhorrado: $ {nuevo_ahorro:,.0f} COP"
      )
      return

    # CASO 3: GASTO ESTÁNDAR
    if len(lineas) < 3:
      await update.message.reply_text(
          "⚠️ Formato incompleto. Envía 3 líneas: Monto, Concepto, Método."
      )
      return

    monto_str = lineas[0].replace("$", "").replace(".", "").replace(",", "")
    monto = float(monto_str)
    concepto = lineas[1]
    metodo_pago = lineas[2]
    categoria = clasificar_gasto(concepto)

    ejecutar_sql(
        "INSERT INTO transacciones (fecha, concepto, categoria, monto,"
        " metodo_pago) VALUES (?, ?, ?, ?, ?)",
        (fecha_hoy, concepto, categoria, monto, metodo_pago),
    )
    await update.message.reply_text(
        f"✅ **Gasto registrado:**\n💰 $ {monto:,.0f} COP\n📝"
        f" {concepto}\n📂 *{categoria}*"
    )

  except Exception as e:
    await update.message.reply_text(
        "⚠️ Ocurrió un error al procesar el mensaje."
    )


telegram_app.add_handler(
    MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje)
)


@app.route("/")
def home():
  return "Bot de Finanzas activo 24/7 🚀"


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  import asyncio

  update = Update.de_json(request.get_json(force=True), telegram_app.bot)

  async def process():
    await telegram_app.initialize()
    await telegram_app.process_update(update)

  asyncio.run(process())
  return "ok", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)