import sqlite3
import os
import unicodedata
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = "7770957118:AAHQTQ4PLdrJ1YRH3Z_U-9T1IB_3KXstLI0"

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
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def clasificar_gasto(concepto):
    c_lower = normalizar_texto(concepto)
    
    if any(w in c_lower for w in ["s&p500", "tsmc"]):
        return "Inversión"
    elif any(w in c_lower for w in ["fondeloitte", "ahorro personal", "ahorro ropa", "ahorro viajes"]):
        return "Ahorro"
    elif any(w in c_lower for w in ["arriendo"]):
        return "Casa / Obligaciones"
    elif any(w in c_lower for w in ["huevo", "proteina", "carne", "d1", "ara", "exito", "fruta", "verdura"]):
        return "Mercado"
    elif any(w in c_lower for w in ["hamburguesa", "pizza", "papas king"]):
        return "Comida fuera"
    elif any(w in c_lower for w in ["barberia", "gimnasio"]):
        return "Bienestar y Cuidado"
    elif any(w in c_lower for w in ["comida alma", "arena alma"]):
        return "Mascota (Alma)"
    elif any(w in c_lower for w in ["netflix", "youtube", "google fotos"]):
        return "Suscripciones"
    elif any(w in c_lower for w in ["paquete de datos", "datos"]):
        return "Servicios"
    elif any(w in c_lower for w in ["credito hipotecario", "pago ipad", "t.c nu", "t.c bancolombia"]):
        return "Pago deudas"
    elif any(w in c_lower for w in ["salida con amigos", "transporte", "pasaje", "cine", "salida"]):
        return "Gastos del mes"
    else:
        return "Gastos del mes"

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    try:
        lineas = [l.strip() for l in texto_usuario.split("\n") if l.strip()]

        if not lineas:
            return

        primera_linea_lower = normalizar_texto(lineas[0])

        # -------------------------------------------------------------
        # CASO 1: ABONO A DEUDA (Actualiza saldo y log_abonos)
        # -------------------------------------------------------------
        if "abono" in primera_linea_lower:
            if len(lineas) < 3:
                await update.message.reply_text(
                    "⚠️ Formato de abono incompleto. Envíalo así:\n\n"
                    "abono\n"
                    "Monto (Ej: 500000)\n"
                    "Nombre de la deuda (Ej: T.C. Bancolombia)"
                )
                return

            monto_str = lineas[1].replace("$", "").replace(".", "").replace(",", "")
            monto = float(monto_str)
            nombre_deuda_buscada = lineas[2]

            deudas_db = consultar_sql("SELECT deuda, monto_total FROM deudas WHERE estado != 'Completada'")
            deuda_encontrada = None
            
            for d in deudas_db:
                if normalizar_texto(nombre_deuda_buscada) in normalizar_texto(d[0]):
                    deuda_encontrada = d[0]
                    saldo_actual = d[1]
                    break

            if not deuda_encontrada:
                await update.message.reply_text(f"⚠️ No encontré una deuda activa que coincida con '{nombre_deuda_buscada}'. Revisa el nombre en la web.")
                return

            nuevo_monto = max(0, saldo_actual - monto)
            nuevo_estado = 'Completada' if nuevo_monto == 0 else 'Pendiente'

            ejecutar_sql("UPDATE deudas SET monto_total = ?, estado = ? WHERE deuda = ?", (nuevo_monto, nuevo_estado, deuda_encontrada))
            
            # Registrar en log_abonos (la tabla unificada con la web)
            ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?, ?, ?, ?)",
                         (fecha_hoy, 'Deuda', deuda_encontrada, monto))

            await update.message.reply_text(
                f"💳 **¡Abono a deuda aplicado!**\n"
                f"🎯 Deuda: {deuda_encontrada}\n"
                f"💰 Monto Abonado: $ {monto:,.0f} COP\n"
                f"📉 Nuevo Saldo: $ {nuevo_monto:,.0f} COP"
            )
            return

        # -------------------------------------------------------------
        # CASO 2: APORTE A META DE AHORRO (Actualiza meta y log_abonos)
        # -------------------------------------------------------------
        elif "meta" in primera_linea_lower or "ahorro" in primera_linea_lower:
            if len(lineas) < 3:
                await update.message.reply_text(
                    "⚠️ Formato de meta incompleto. Envíalo así:\n\n"
                    "meta\n"
                    "Monto (Ej: 200000)\n"
                    "Nombre de la meta (Ej: Viaje a Europa)"
                )
                return

            monto_str = lineas[1].replace("$", "").replace(".", "").replace(",", "")
            monto = float(monto_str)
            nombre_meta_buscada = lineas[2]

            metas_db = consultar_sql("SELECT nombre_meta, monto_actual, monto_objetivo FROM metas_ahorro WHERE estado != 'Completada'")
            meta_encontrada = None

            for m in metas_db:
                if normalizar_texto(nombre_meta_buscada) in normalizar_texto(m[0]):
                    meta_encontrada = m[0]
                    ahorro_actual = m[1]
                    monto_obj = m[2]
                    break

            if not meta_encontrada:
                await update.message.reply_text(f"⚠️ No encontré una meta en curso que coincida con '{nombre_meta_buscada}'. Revisa el nombre en la web.")
                return

            nuevo_ahorro = ahorro_actual + monto
            nuevo_estado_meta = 'Completada' if nuevo_ahorro >= monto_obj else 'En curso'

            ejecutar_sql("UPDATE metas_ahorro SET monto_actual = ?, estado = ? WHERE nombre_meta = ?",
                         (nuevo_ahorro, nuevo_estado_meta, meta_encontrada))

            # Registrar en log_abonos (la tabla unificada con la web)
            ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?, ?, ?, ?)",
                         (fecha_hoy, 'Meta', meta_encontrada, monto))

            await update.message.reply_text(
                f"💰 **¡Aporte a meta registrado!**\n"
                f"🎯 Meta: {meta_encontrada}\n"
                f"💵 Monto Sumado: $ {monto:,.0f} COP\n"
                f"📈 Total Ahorrado: $ {nuevo_ahorro:,.0f} COP"
            )
            return

        # -------------------------------------------------------------
        # CASO 3: GASTO ESTÁNDAR (3 líneas: Monto, Concepto, Método de pago)
        # -------------------------------------------------------------
        if len(lineas) < 3:
            await update.message.reply_text(
                "⚠️ Formato incompleto. Envía los datos en 3 líneas:\n\n"
                "Monto (Ej: 45000)\n"
                "Concepto (Ej: Éxito)\n"
                "Método de pago (Ej: T.C. Bancolombia)"
            )
            return

        monto_str = lineas[0].replace("$", "").replace(".", "").replace(",", "")
        monto = float(monto_str)
        concepto = lineas[1]
        metodo_pago = lineas[2]

        categoria = clasificar_gasto(concepto)

        ejecutar_sql(
            "INSERT INTO transacciones (fecha, concepto, categoria, monto, metodo_pago) VALUES (?, ?, ?, ?, ?)",
            (fecha_hoy, concepto, categoria, monto, metodo_pago)
        )

        await update.message.reply_text(
            f"✅ **Gasto registrado y clasificado:**\n"
            f"💰 Monto: $ {monto:,.0f} COP\n"
            f"📝 Concepto: {concepto}\n"
            f"📂 Categoría: *{categoria}*\n"
            f"💳 Método de Pago: *{metodo_pago}*"
        )

    except Exception as e:
        await update.message.reply_text(
            "⚠️ Ocurrió un error al procesar el mensaje. Verifica el formato e intenta nuevamente."
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje))
    
    print("🤖 Bot de Telegram sincronizado con Deudas y Metas activo...")
    app.run_polling()

if __name__ == "__main__":
    main()