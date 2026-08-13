import os
import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
import threading

# Configuración de la página web
st.set_page_config(
    page_title="Centro de Comando Financiero",
    page_icon="📊",
    layout="wide"
)

def ejecutar_sql(query, params=()):
    conexion = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conexion.cursor()
    cursor.execute(query, params)
    conexion.commit()
    conexion.close()

def cargar_datos(query):
    try:
        # Formateamos la URL para que sea compatible con SQLAlchemy
        url_db = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://")
        
        # Le pasamos la URL cruda directamente. Pandas hará la magia por debajo.
        df = pd.read_sql(query, url_db)
        
        return df
    except Exception as e:
        # Si algo falla, el log nos dirá exactamente qué fue
        print(f"🚨 ERROR AL LEER BD ({query}): {e}")
        return pd.DataFrame()

st.title("📊 Centro de Comando Financiero")
st.markdown("Monitoreo en vivo de transacciones, presupuestos, deudas, metas de ahorro y patrimonio.")

# Cargar datos de la base de datos
try:
    df_transacciones = cargar_datos("SELECT * FROM transacciones ORDER BY id DESC")
except:
    df_transacciones = pd.DataFrame()

try:
    df_inversiones = cargar_datos("SELECT * FROM inversiones")
except:
    df_inversiones = pd.DataFrame()

try:
    df_presupuestos = cargar_datos("SELECT * FROM presupuestos")
except:
    df_presupuestos = pd.DataFrame()

try:
    df_deudas = cargar_datos("SELECT * FROM deudas")
except:
    df_deudas = pd.DataFrame()

try:
    df_metas = cargar_datos("SELECT * FROM metas_ahorro")
except:
    df_metas = pd.DataFrame()

try:
    df_log = cargar_datos("SELECT * FROM log_abonos ORDER BY fecha DESC")
except:
    df_log = pd.DataFrame()

# --- 1. FILTRADO DEL MES ACTUAL (OBLIGATORIO ANTES DE LOS KPIS) ---
if not df_transacciones.empty and 'fecha' in df_transacciones.columns:
    df_transacciones['fecha_dt'] = pd.to_datetime(df_transacciones['fecha'], errors='coerce')
    mes_actual_str = datetime.now().strftime("%Y-%m")
    df_mes_actual = df_transacciones[df_transacciones['fecha_dt'].dt.strftime("%Y-%m") == mes_actual_str]
else:
    df_mes_actual = pd.DataFrame()

# --- 2. BLOQUE DE KPIS PRINCIPALES CORREGIDO Y SEGURO ---
salario_actual = 6427740 
gasto_actual = float(df_mes_actual['monto'].sum()) if not df_mes_actual.empty and 'monto' in df_mes_actual.columns else 0.0
dinero_disponible = salario_actual - gasto_actual

total_patrimonio = 0.0
if not df_inversiones.empty:
    col_pat = 'monto_invertido' if 'monto_invertido' in df_inversiones.columns else 'monto'
    if col_pat in df_inversiones.columns:
        total_patrimonio = float(pd.to_numeric(df_inversiones[col_pat], errors='coerce').sum())

total_deudas = 0.0
if not df_deudas.empty:
    col_deuda = 'monto_total' if 'monto_total' in df_deudas.columns else 'monto'
    if col_deuda in df_deudas.columns:
        total_deudas = float(pd.to_numeric(df_deudas[col_deuda], errors='coerce').sum())

col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.metric(label="💰 Disponible Mes", value=f"$ {dinero_disponible:,.0f}".replace(",", "."))
with col_k2:
    st.metric(label="📉 Gastos del Mes", value=f"$ {gasto_actual:,.0f}".replace(",", "."))
with col_k3:
    st.metric(label="🏦 Patrimonio Actual", value=f"$ {total_patrimonio:,.0f}".replace(",", "."))
with col_k4:
    st.metric(label="💳 Deudas Totales", value=f"$ {total_deudas:,.0f}".replace(",", "."))

st.markdown("---")

# Pestañas de navegación organizadas
pestana_trans, pestana_historial, pestana_presupuestos, pestana_deudas, pestana_metas, pestana_inversiones, pestana_patrones, pestana_control, pestana_salud = st.tabs([
    "📝 Gastos del mes", 
    "📅 Historial de gastos",
    "🎯 Presupuestos", 
    "💳 Deudas", 
    "💰 Ahorro",
    "💎 Patrimonio & Inversiones",
    "📊 Análisis financiero",
    "📀 Control presupuestario", 
    "📈 Salud financiera"
])

with pestana_trans:
    st.subheader("📝 Gastos del mes actual")

     # --- NUEVO: Guía de categorías desplegable ---
    with st.expander("💡 Ver categorías del bot y palabras clave (Haz clic para desplegar)"):
        st.markdown("""
        **Usa los nombres principales (en negrita) al crear tu presupuesto.** El bot clasificará automáticamente los gastos si usas las palabras clave asociadas:
        
        * **Inversión**: s&p500, tsmc
        * **Ahorro**: fondeloitte, ahorro personal, ahorro ropa, ahorro viajes
        * **Casa / Obligaciones**: arriendo
        * **Mercado**: huevo, proteina, carne, d1, ara, éxito, exito, fruta, verdura
        * **Comida fuera**: hamburguesa, pizza, papas king, comida fuera
        * **Carro**: carro, gasolina, arreglo, llave, llanta, parqueadero, peaje, lavadero, soat
        * **Oficina**: oficina, transmilenio, almuerzo, desayuno
        * **Bienestar y Cuidado**: barberia, gimnasio, uñas
        * **Mascota (Alma)**: comida alma, arena alma
        * **Suscripciones**: netflix, youtube, google fotos
        * **Servicios**: paquete de datos, datos
        * **Pago deudas**: crédito hipotecario, credito hipotecario, pago ipad, t.c nu, t.c bancolombia
        * **Gastos del mes**: salida con amigos, transporte, pasaje, cine, salida *(Esta es también la categoría por defecto)*
        """)
    # ---------------------------------------------

    # --- PANEL DESPLEGABLE PARA REGISTRO MANUAL DE TRANSACCIONES ---
    with st.expander("➕ Registrar nueva transacción manual"):
        with st.form("form_transaccion_manual", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                # Fecha por defecto el día de hoy (puedes ajustarla si fue en otro momento)
                from datetime import date
                fecha_input = st.date_input("Fecha", value=date.today(), key="fecha_manual")
                concepto_input = st.text_input("Concepto (Ej. Almuerzo, Uber, etc.)", key="concepto_manual")
                
            with col_m2:
                # Categorías habituales (puedes adaptarlas a las que usas en tus presupuestos)
                categorias_opciones = ['Inversion', 'Ahorro', 'Casa', 'Mercado', 'Comida fuera', 'Bienestar y cuidado', 'Mascota', 'Suscripciones', 'Servicios', 'Pago deudas', 'Gastos del mes']
                categoria_input = st.selectbox("Categoría", categorias_opciones, key="categoria_manual")
                
                monto_input = st.number_input("Monto (COP)", min_value=0, value=0, step=10000, format="%d", key="monto_manual")
                
            # Opciones comunes para el método de pago
            metodo_pago_input = st.selectbox("Método de Pago", ['Transferencia', 'T.C. Bancolombia', 'T.C. Nu', 'Efectivo', 'Otro'], key="metodo_pago_manual")
            
            # Botón de envío del formulario
            guardar_transaccion = st.form_submit_button("Guardar Transacción", use_container_width=True)
            
            if guardar_transaccion:
                if concepto_input and monto_input > 0:
                    # Asegúrate de que el nombre de tu tabla en la base de datos sea el correcto (ej. 'transacciones' o 'gastos')
                    query = """
                        INSERT INTO transacciones (fecha, concepto, categoria, monto, metodo_pago) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    # Formateamos la fecha a string YYYY-MM-DD para SQL
                    params = (str(fecha_input), concepto_input, categoria_input, float(monto_input), metodo_pago_input)
                    
                    ejecutar_sql(query, params)
                    st.success(f"¡Transacción de '{concepto_input}' guardada exitosamente!")
                    st.rerun()
                else:
                    st.warning("Por favor ingresa un concepto válido y un monto mayor a cero.")
        
    if not df_transacciones.empty:
        # 1. Obtener el mes actual (Ej. "2026-07")
        mes_actual = datetime.now().strftime("%Y-%m")
        
        # 2. Filtrar solo las transacciones que empiecen con ese mes
        df_mes_actual = df_transacciones[df_transacciones['fecha'].str.startswith(mes_actual)].copy()
        
        if not df_mes_actual.empty:
            # --- 1. TABLA VISUAL DE LECTURA (Formato COP impecable) ---
            df_trans_visual = df_mes_actual.copy()
            
            # Aplicamos la capa de formato estético al monto
            df_trans_visual['Monto'] = df_trans_visual['monto'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            
            # Renombramos y organizamos para la presentación
            df_trans_visual = df_trans_visual[['fecha', 'concepto', 'categoria', 'Monto', 'metodo_pago']].rename(columns={
                'fecha': 'Fecha', 'concepto': 'Concepto', 'categoria': 'Categoría', 'metodo_pago': 'Método de Pago'
            })
            
            st.dataframe(df_trans_visual, use_container_width=True)

            # --- 2. PANEL DESPLEGABLE DE EDICIÓN (Transacciones) ---
            with st.expander("✏️ Editar o eliminar un gasto"):
            
                # 1. Limpieza de estado pendiente al guardar o eliminar
                if "limpiar_seleccion_trans" in st.session_state and st.session_state["limpiar_seleccion_trans"]:
                    st.session_state["sel_trans_edit"] = "-- Selecciona un gasto --"
                    st.session_state["limpiar_seleccion_trans"] = False

                if "sel_trans_edit" not in st.session_state:
                    st.session_state["sel_trans_edit"] = "-- Selecciona un gasto --"
                    
                # 2. Construimos etiquetas únicas: ID | Fecha | Concepto | Monto
                opciones_trans = []
                for _, row in df_mes_actual.iterrows():
                    etiqueta = f"ID {row['id']} | {row['fecha']} | {row['concepto']} | $ {row['monto']:,.0f}".replace(",", ".")
                    opciones_trans.append((row['id'], etiqueta))
                
                etiquetas_trans = [op[1] for op in opciones_trans]
                etiquetas_opciones_t = ["-- Selecciona un gasto --"] + etiquetas_trans
                
                # 3. Función que refresca los datos al cambiar la selección
                def actualizar_campos_transaccion():
                    seleccion = st.session_state.get("sel_trans_edit", "-- Selecciona un gasto --")
                    if seleccion and seleccion != "-- Selecciona un gasto --":
                        id_sel = next(op[0] for op in opciones_trans if op[1] == seleccion)
                        fila_trans = df_mes_actual[df_mes_actual['id'] == id_sel].iloc[0]
                        
                        # Actualizamos el session_state con los datos reales
                        st.session_state["edit_fecha_trans"] = str(fila_trans['fecha'])
                        st.session_state["edit_concepto_trans"] = str(fila_trans['concepto'])
                        st.session_state["edit_cat_trans"] = str(fila_trans['categoria'])
                        st.session_state["edit_monto_trans"] = int(fila_trans['monto'])
                        st.session_state["edit_metodo_trans"] = str(fila_trans['metodo_pago'])
                    else:
                        # Limpiamos si no hay selección
                        st.session_state["edit_fecha_trans"] = ""
                        st.session_state["edit_concepto_trans"] = ""
                        st.session_state["edit_cat_trans"] = ""
                        st.session_state["edit_monto_trans"] = 0
                        st.session_state["edit_metodo_trans"] = ""

                # 4. El selectbox conectado a la función on_change
                trans_sel_etiqueta = st.selectbox(
                    "Selecciona el gasto a modificar:", 
                    etiquetas_opciones_t, 
                    key="sel_trans_edit",
                    on_change=actualizar_campos_transaccion
                )
                
                # Inicializamos keys si no existen para evitar errores visuales
                if "edit_fecha_trans" not in st.session_state: st.session_state["edit_fecha_trans"] = ""
                if "edit_concepto_trans" not in st.session_state: st.session_state["edit_concepto_trans"] = ""
                if "edit_cat_trans" not in st.session_state: st.session_state["edit_cat_trans"] = ""
                if "edit_metodo_trans" not in st.session_state: st.session_state["edit_metodo_trans"] = ""
                if "edit_monto_trans" not in st.session_state: st.session_state["edit_monto_trans"] = 0
                
                if trans_sel_etiqueta and trans_sel_etiqueta != "-- Selecciona un gasto --":
                    # Extraemos el ID real a partir de la selección
                    id_seleccionado_t = next(op[0] for op in opciones_trans if op[1] == trans_sel_etiqueta)
                    
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        # 5. Inputs SIN el parámetro 'value', solo conectados por su 'key'
                        nueva_fecha_t = st.text_input("Fecha (YYYY-MM-DD)", key="edit_fecha_trans")
                        nuevo_concepto_t = st.text_input("Concepto", key="edit_concepto_trans")
                        nueva_categoria_t = st.text_input("Categoría", key="edit_cat_trans")
                    with col_g2:
                        nuevo_monto_t = st.number_input("Monto (COP)", step=10000, format="%d", key="edit_monto_trans")
                        nuevo_metodo_t = st.text_input("Método de Pago", key="edit_metodo_trans")
                        
                    col_gb1, col_gb2 = st.columns(2)
                    with col_gb1:
                        if st.button("Guardar cambios", use_container_width=True, key="btn_guardar_cambios_transacciones"):
                            query = """
                                UPDATE transacciones 
                                SET fecha = %s, concepto = %s, categoria = %s, monto = %s, metodo_pago = %s 
                                WHERE id = %s
                            """
                            params = (nueva_fecha_t, nuevo_concepto_t, nueva_categoria_t, float(nuevo_monto_t), nuevo_metodo_t, int(id_seleccionado_t))
                            ejecutar_sql(query, params)
                            st.success("¡Transacción actualizada correctamente!")
                            
                            # Activa la bandera para limpiar los campos
                            st.session_state["limpiar_seleccion_trans"] = True
                            st.rerun()
                    with col_gb2:
                        if st.button("Eliminar Gasto", type="primary", use_container_width=True, key="btn_eliminar_gasto_transacciones"):
                            query = "DELETE FROM transacciones WHERE id = %s"
                            ejecutar_sql(query, (int(id_seleccionado_t),))
                            st.warning("¡Transacción eliminada!")
                            
                            # Activa la bandera para limpiar los campos
                            st.session_state["limpiar_seleccion_trans"] = True
                            st.rerun()
            
            # --- 3. GRÁFICA INTACTA ---
            st.subheader("Gastos por categoría")
            df_categoria = df_mes_actual.groupby('categoria')['monto'].sum().reset_index()
            df_categoria.columns = ['Categoría', 'Monto']
            
            grafico = alt.Chart(df_categoria).mark_bar().encode(
                x=alt.X('Categoría:N', sort='-y'),
                y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='Monto (COP)')),
                color=alt.Color('Categoría:N', legend=None),
                tooltip=['Categoría:N', alt.Tooltip('Monto:Q', format=',.0f')]
            ).properties(height=350)
            st.altair_chart(grafico, use_container_width=True)
        else:
            st.info("Aún no hay transacciones registradas este mes. ¡Escríbele a tu bot de Telegram!")
    else:
        st.info("Aún no hay transacciones en la base de datos.")

with pestana_historial:
    st.subheader("📅 Historial de transacciones por mes")
    
    if not df_transacciones.empty:
        # Extraer los meses únicos
        df_transacciones['Mes'] = df_transacciones['fecha'].str[:7]
        meses_disponibles = sorted(df_transacciones['Mes'].unique(), reverse=True)
        
        # Selector de mes
        mes_seleccionado = st.selectbox("Selecciona el mes que deseas consultar", meses_disponibles)
        
        # Filtrar datos por el mes seleccionado
        df_mes_historial = df_transacciones[df_transacciones['Mes'] == mes_seleccionado].drop(columns=['Mes'])
        
        # 1. Total gastado en la parte de arriba
        total_mes = df_mes_historial['monto'].sum()
        st.metric("Total Gastado en el Mes", f"$ {total_mes:,.0f}".replace(",", "."))
        
        st.markdown("---")
        
        # 2. Tabla de transacciones
        st.markdown(f"### Detalle de transacciones ({mes_seleccionado})")
        
        # 1. Validamos que haya datos para mostrar
        if not df_mes_historial.empty:
            df_historial_visual = df_mes_historial.copy()
            
            # 2. Aplicamos el formato de moneda (COP)
            df_historial_visual['monto'] = df_historial_visual['monto'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            
            # 3. Excluimos la columna 'id' y renombramos el resto
            df_historial_visual = df_historial_visual[['fecha', 'concepto', 'categoria', 'monto', 'metodo_pago']].rename(columns={
                'fecha': 'Fecha', 
                'concepto': 'Concepto', 
                'categoria': 'Categoría', 
                'monto': 'Monto', 
                'metodo_pago': 'Método de Pago'
            })
            
            # 4. Imprimimos la tabla visual sin el índice
            st.dataframe(df_historial_visual, use_container_width=True, hide_index=True)
        else:
            st.info("No hay transacciones registradas para este mes.")
        
        # 3. Gráfica por categoría de ese mes
        st.subheader("Gastos por categoría")
        df_categoria_hist = df_mes_historial.groupby('categoria')['monto'].sum().reset_index()
        df_categoria_hist.columns = ['Categoría', 'Monto']
        
        # Definición segura de escala de colores
        escala_colores_categorias = alt.Scale(
            domain=['Inversion', 'Ahorro', 'Casa', 'Mercado', 'Comida fuera', 'Bienestar y cuidado', 'Mascota', 'Suscripciones', 'Servicios', 'Pago deudas', 'Gastos del mes'],
            range=['#2AA63E', '#E1712B', '#E7180B', '#155DFC', '#8E44AD', '#1ABC9C', '#95A5A6', '#95A5A6', '#95A5A6', '#95A5A6', '#95A5A6']
        )

        grafico_hist = alt.Chart(df_categoria_hist).mark_bar().encode(
            x=alt.X('Categoría:N', sort='-y', axis=alt.Axis(
                labelAngle=0,         # Forzar ángulo horizontal estricto
                labelOverlap=False,   # Evitar que se solapen o roten automáticas
                title='Categoría'
            )),
            y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='Monto (COP)')),
            color=alt.Color('Categoría:N', scale=escala_colores_categorias, legend=None),
            tooltip=[
                alt.Tooltip('Categoría:N', title='Categoría'), 
                alt.Tooltip('Monto:Q', title='Monto', format=',.0f')
            ]
        ).properties(height=350)
        
        st.altair_chart(grafico_hist, use_container_width=True)
        
    else:
        st.info("No hay historial disponible todavía.")

with pestana_presupuestos:
    st.subheader("🎯 Gestión de presupuesto")

    # Lista estandarizada de opciones para ubicación del dinero
    opciones_ubicacion = ["Nu", "Bancolombia", "Efectivo", "No aplica", "Otro"]

    # --- BOTÓN DE ACTUALIZACIÓN MANUAL EN LA BARRA LATERAL ---
    with st.sidebar:
        st.markdown("---")
        if st.button("🔄 Actualizar Datos Manualmente", use_container_width=True):
            st.cache_data.clear()
            st.success("¡Datos actualizados!")
            st.rerun()

    # --- Guía de categorías desplegable ---
    with st.expander("💡 Ver categorías del bot y palabras clave (Haz clic para desplegar)"):
        st.markdown("""
        **Usa los nombres principales (en negrita) al crear tu presupuesto.** El bot clasificará automáticamente los gastos si usas las palabras clave asociadas:
        
        * **Inversión**: s&p500, tsmc
        * **Ahorro**: fondeloitte, ahorro personal, ahorro ropa, ahorro viajes
        * **Casa / Obligaciones**: arriendo
        * **Mercado**: huevo, proteina, carne, d1, ara, éxito, exito, fruta, verdura
        * **Comida fuera**: hamburguesa, pizza, papas king, comida fuera
        * **Carro**: carro, gasolina, arreglo, llave, llanta, parqueadero, peaje, lavadero, soat
        * **Oficina**: oficina, transmilenio, almuerzo, desayuno
        * **Bienestar y Cuidado**: barberia, gimnasio, uñas
        * **Mascota (Alma)**: comida alma, arena alma
        * **Suscripciones**: netflix, youtube, google fotos
        * **Servicios**: paquete de datos, datos
        * **Pago deudas**: crédito hipotecario, credito hipotecario, pago ipad, t.c nu, t.c bancolombia
        * **Gastos del mes**: salida con amigos, transporte, pasaje, cine, salida *(Esta es también la categoría por defecto)*
        """)
    
    col_sal1, col_sal2, col_sal3 = st.columns(3)
    with col_sal1:
        salario_mes = st.number_input("Ingreso / Salario del Mes (COP)", min_value=0, value=6427740, step=100000, format="%d", key="input_salario_presupuesto")

    from datetime import datetime
    mes_actual_top = datetime.now().strftime("%Y-%m")

    df_presupuestos_mes = df_presupuestos[df_presupuestos['mes'] == mes_actual_top]

    total_presupuestado = df_presupuestos_mes['limite'].sum() if not df_presupuestos_mes.empty else 0
    disponible_por_asignar = salario_mes - total_presupuestado
    
    with col_sal2:
        st.metric(label=f"Total Presupuestado ({mes_actual_top})", value=f"$ {total_presupuestado:,.0f}".replace(",", "."))
    with col_sal3:
        st.metric(label="Disponible por Asignar", value=f"$ {disponible_por_asignar:,.0f}".replace(",", "."))
    
    # =========================================================================
    # 1. FORMULARIO DE NUEVO PRESUPUESTO
    # =========================================================================
    with st.expander("➕ Registrar nuevo presupuesto"):
        with st.form("form_presupuesto", clear_on_submit=True):
            st.markdown("**Asignar presupuesto, categoría, clasificación y ubicación**")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                # Por defecto pre-llenamos con el mes actual
                from datetime import datetime
                mes_actual_sugerido = datetime.now().strftime("%Y-%m")
                
                mes_input = st.text_input("Mes (Ej. 2026-07)", value=mes_actual_sugerido, key="nuevo_mes_presupuesto")
                cat_input = st.text_input("Categoría (Ej. Mercado, VOO, Arriendo)", key="nueva_cat_presupuesto")
                ubicacion_input = st.selectbox("Ubicación del Dinero", opciones_ubicacion, key="nueva_ubicacion_presupuesto")
            with col_p2:
                tipo_input = st.selectbox(
                    "Tipo de Presupuesto", 
                    ["Necesidad", "Ahorro", "Inversión", "Gasto General"],
                    key="nuevo_tipo_presupuesto"
                )
                limite_input = st.number_input("Límite Presupuestado (COP)", min_value=0, value=0, step=50000, format="%d", key="nuevo_limite_presupuesto")
                
            guardar_p = st.form_submit_button("Guardar Presupuesto")
            if guardar_p and cat_input:
                ejecutar_sql(
                    "INSERT INTO presupuestos (mes, categoria, tipo, limite, ubicacion) VALUES (%s, %s, %s, %s, %s)",
                    (mes_input, cat_input.capitalize(), tipo_input, limite_input, ubicacion_input)
                )
                st.success(f"¡Presupuesto para {cat_input} guardado exitosamente!")
                st.rerun()
    # =========================================================================
    # 2. PANEL DE EDICIÓN O ELIMINACIÓN DE REGISTROS
    # =========================================================================
    with st.expander("✏️ Editar o eliminar un presupuesto histórico"):
        if "limpiar_seleccion" in st.session_state and st.session_state["limpiar_seleccion"]:
            st.session_state["sel_presupuesto_edit"] = "-- Selecciona un presupuesto --"
            st.session_state["limpiar_seleccion"] = False

        if "sel_presupuesto_edit" not in st.session_state:
            st.session_state["sel_presupuesto_edit"] = "-- Selecciona un presupuesto --"

        opciones_pres = []
        for _, row in df_presupuestos.iterrows():
            ubi_txt = f" | {row['ubicacion']}" if 'ubicacion' in row and row['ubicacion'] else ""
            etiqueta = f"{row['mes']} | {row['categoria']}{ubi_txt} | $ {row['limite']:,.0f}".replace(",", ".")
            opciones_pres.append((row['id'], etiqueta))
        
        etiquetas_pres = [op[1] for op in opciones_pres]
        etiquetas_opciones = ["-- Selecciona un presupuesto --"] + etiquetas_pres
        
        def actualizar_campos_edicion():
            seleccion = st.session_state.get("sel_presupuesto_edit", "-- Selecciona un presupuesto --")
            if seleccion and seleccion != "-- Selecciona un presupuesto --":
                id_sel = next(op[0] for op in opciones_pres if op[1] == seleccion)
                fila = df_presupuestos[df_presupuestos['id'] == id_sel].iloc[0]
                
                st.session_state["edit_mes_val"] = str(fila['mes'])
                st.session_state["edit_cat_val"] = str(fila['categoria'])
                st.session_state["edit_asig_val"] = bool(fila['asignado']) if 'asignado' in fila else False
                st.session_state["edit_tipo_val"] = str(fila['tipo']) if fila['tipo'] in ['Inversión', 'Necesidad', 'Gasto General', 'Ahorro'] else 'Necesidad'
                st.session_state["edit_ubi_val"] = str(fila['ubicacion']) if 'ubicacion' in fila and fila['ubicacion'] in opciones_ubicacion else 'Nu'
                st.session_state["edit_lim_val"] = int(fila['limite'])
            else:
                st.session_state["edit_mes_val"] = ""
                st.session_state["edit_cat_val"] = ""
                st.session_state["edit_asig_val"] = False
                st.session_state["edit_tipo_val"] = "Necesidad"
                st.session_state["edit_ubi_val"] = "Nu"
                st.session_state["edit_lim_val"] = 0

        pres_sel_etiqueta = st.selectbox(
            "Selecciona el presupuesto a modificar:", 
            etiquetas_opciones, 
            key="sel_presupuesto_edit",
            on_change=actualizar_campos_edicion
        )
        
        if "edit_cat_val" not in st.session_state:
            st.session_state["edit_cat_val"] = ""
        if "edit_mes_val" not in st.session_state:
            st.session_state["edit_mes_val"] = ""
        if "edit_lim_val" not in st.session_state:
            st.session_state["edit_lim_val"] = 0
        if "edit_ubi_val" not in st.session_state:
            st.session_state["edit_ubi_val"] = "Nu"

        if pres_sel_etiqueta and pres_sel_etiqueta != "-- Selecciona un presupuesto --":
            id_seleccionado_p = next(op[0] for op in opciones_pres if op[1] == pres_sel_etiqueta)
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                nuevo_mes_p = st.text_input("Mes (YYYY-MM)", value=st.session_state.get("edit_mes_val", ""), key="input_mes_presupuesto")
                nueva_categoria_p = st.text_input("Categoría", value=st.session_state.get("edit_cat_val", ""), key="input_categoria_presupuesto")
                nuevo_asignado_p = st.checkbox("¿Asignado en banco?", value=st.session_state.get("edit_asig_val", False), key="input_asignado_presupuesto")
                
            with col_p2:
                opciones_tipo = ['Inversión', 'Necesidad', 'Gasto General', 'Ahorro']
                tipo_actual_idx = opciones_tipo.index(st.session_state.get("edit_tipo_val", "Necesidad")) if st.session_state.get("edit_tipo_val", "Necesidad") in opciones_tipo else 1
                nuevo_tipo_p = st.selectbox("Tipo", opciones_tipo, index=tipo_actual_idx, key="input_tipo_presupuesto")
                
                ubi_actual = st.session_state.get("edit_ubi_val", "Nu")
                ubi_actual_idx = opciones_ubicacion.index(ubi_actual) if ubi_actual in opciones_ubicacion else 0
                nueva_ubicacion_p = st.selectbox("Ubicación del Dinero", opciones_ubicacion, index=ubi_actual_idx, key="input_ubicacion_presupuesto")
                
                nuevo_limite_p = st.number_input("Límite (COP)", value=st.session_state.get("edit_lim_val", 0), step=50000, format="%d", key="input_limite_presupuesto")
                
            col_pb1, col_pb2 = st.columns(2)
            with col_pb1:
                if st.button("Guardar Cambios en Presupuesto", use_container_width=True, key="btn_guardar_cambios_presupuestos"):
                    query = """
                        UPDATE presupuestos 
                        SET mes = %s, categoria = %s, tipo = %s, limite = %s, asignado = %s, ubicacion = %s 
                        WHERE id = %s
                    """
                    params = (nuevo_mes_p, nueva_categoria_p, nuevo_tipo_p, float(nuevo_limite_p), nuevo_asignado_p, nueva_ubicacion_p, int(id_seleccionado_p))
                    ejecutar_sql(query, params)
                    st.success("¡Presupuesto actualizado correctamente!")
                    
                    st.session_state["limpiar_seleccion"] = True
                    st.rerun()
            with col_pb2:
                if st.button("Eliminar Presupuesto", type="primary", use_container_width=True, key="btn_eliminar_presupuesto"):
                    query = "DELETE FROM presupuestos WHERE id = %s"
                    ejecutar_sql(query, (int(id_seleccionado_p),))
                    st.warning("¡Presupuesto eliminado!")
                    
                    st.session_state["limpiar_seleccion"] = True
                    st.rerun()

    # =========================================================================
    # 3. TABLA Y GRÁFICO CIRCULAR (FILTRADOS POR MES)
    # =========================================================================
    st.subheader("📊 Detalle y gráfico de presupuestos")
    
    if not df_presupuestos.empty:
        from datetime import datetime
        
        # Obtenemos el mes actual en formato YYYY-MM
        mes_actual = datetime.now().strftime("%Y-%m")
        
        # Filtro de visualización (Mes Actual vs Seleccionar Histórico)
        opcion_vista = st.radio(
            "Selecciona la vista de tus presupuestos:", 
            ["Presupuesto del mes actual", "Consultar otro mes"], 
            horizontal=True,
            key="radio_filtro_mes_presupuesto"
        )
        
        if opcion_vista == "Presupuesto del mes actual":
            mes_filtrado = mes_actual
            st.info(f"Mostrando el presupuesto correspondiente al mes en curso: **{mes_filtrado}**")
        else:
            # Obtenemos la lista única de meses disponibles en la BD de forma descendente
            meses_disponibles = sorted(df_presupuestos['mes'].unique().tolist(), reverse=True)
            if not meses_disponibles:
                meses_disponibles = [mes_actual]
            mes_filtrado = st.selectbox("Selecciona el mes a consultar:", meses_disponibles, key="sel_filtro_mes_historico")

        # Filtramos el DataFrame original según el mes seleccionado en la interfaz
        df_pres_filtrado = df_presupuestos[df_presupuestos['mes'] == mes_filtrado]

        if not df_pres_filtrado.empty:
            # --- TABLA DE LECTURA (FILTRADA) ---
            df_pres_visual = df_pres_filtrado.copy()
            if 'asignado' not in df_pres_visual.columns:
                df_pres_visual['asignado'] = False
            if 'ubicacion' not in df_pres_visual.columns:
                df_pres_visual['ubicacion'] = 'Sin asignar'
            
            # Calculamos el total de ese mes para mostrarlo
            total_mes_filtrado = df_pres_visual['limite'].sum()
            st.markdown(f"**Total presupuestado para {mes_filtrado}:** $ {total_mes_filtrado:,.0f}".replace(",", "."))
            
            df_pres_visual['Límite'] = df_pres_visual['limite'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_pres_visual = df_pres_visual[['mes', 'categoria', 'tipo', 'ubicacion', 'Límite', 'asignado']].rename(columns={
                'mes': 'Mes', 
                'categoria': 'Categoría', 
                'tipo': 'Tipo',
                'ubicacion': 'Ubicación',
                'asignado': '¿Asignado en banco?'
            })
            
            st.dataframe(df_pres_visual, use_container_width=True, hide_index=True)

            # --- GRÁFICO CIRCULAR (TIPO DONUT) AGRUPADO POR TIPO (FILTRADO) ---
            import pandas as pd
            import altair as alt

            df_tipo_agrupado = df_pres_filtrado.groupby('tipo')['limite'].sum().reset_index()

            escala_colores_tipo = alt.Scale(
                domain=['Inversión', 'Necesidad', 'Gasto General', 'Ahorro'],
                range=['#2AA63E', '#155DFC', '#E1712B', '#8E44AD']
            )

            base_circular = alt.Chart(df_tipo_agrupado).encode(
                theta=alt.Theta(field="limite", type="quantitative", stack=True),
                color=alt.Color(field="tipo", type="nominal", scale=escala_colores_tipo, title="Tipo de Presupuesto"),
                tooltip=[
                    alt.Tooltip('tipo:N', title='Tipo'),
                    alt.Tooltip('limite:Q', title='Total Límite', format=',.0f')
                ]
            )

            pie = base_circular.mark_arc(outerRadius=120, innerRadius=70)
            texto = base_circular.mark_text(radius=145, size=13).encode(
                text=alt.Text('limite:Q', format=',.0f')
            )

            grafico_circular = (pie + texto).properties(
                title=f"Distribución de Presupuestos ({mes_filtrado})",
                height=400
            )
            
            st.altair_chart(grafico_circular, use_container_width=True)
        else:
            st.warning(f"No hay presupuestos asignados para el mes seleccionado ({mes_filtrado}).")
    else:
        st.info("No hay presupuestos configurados todavía.")

with pestana_deudas:
    st.subheader("💳 Gestión de deudas")
    
    with st.expander("➕ Registrar nueva deuda"):
        with st.form("form_deuda", clear_on_submit=True):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                deuda_input = st.text_input("Deuda (Ej. T.C. Bancolombia, Curso de inglés)", key="input_deuda_pestana_deudas")
                estado_deuda = st.selectbox("Estado inicial", ["Pendiente", "Completada"], key="sel_estado_inicial_deuda")
            with col_d2:
                monto_total_deuda = st.number_input("Monto Total Inicial (COP)", min_value=0, value=0, step=50000, format="%d", key="num_monto_total_deuda")
                cuota_mes_deuda = st.number_input("Cuota o Pago Mínimo del Mes (COP)", min_value=0, value=0, step=10000, format="%d", key="num_cuota_mes_deuda")
                
            guardar_d = st.form_submit_button("Guardar Deuda")
            if guardar_d and deuda_input:
                ejecutar_sql(
                    "INSERT INTO deudas (deuda, monto_inicial, monto_total, cuota_mes, estado) VALUES (%s, %s, %s, %s, %s)",
                    (deuda_input, monto_total_deuda, monto_total_deuda, cuota_mes_deuda, estado_deuda)
                )
                st.success(f"¡Deuda '{deuda_input}' registrada exitosamente!")
                st.rerun()

    if not df_deudas.empty:
        ver_completadas_d = st.checkbox("Mostrar deudas completadas / pagadas", key="chk_comp_d")
        df_deudas_filtradas = df_deudas if ver_completadas_d else df_deudas[df_deudas['estado'] != 'Completada']

        if not df_deudas_filtradas.empty:
            with st.expander("➕ Registrar nuevo abono a dedua"):
                with st.form("form_abono_deuda", clear_on_submit=True):
                    col_ab1, col_ab2 = st.columns(2)
                    with col_ab1:
                        deudas_activas_lista = df_deudas[df_deudas['estado'] != 'Completada']['deuda'].tolist()
                        deuda_a_abonar = st.selectbox("Selecciona la deuda", deudas_activas_lista if deudas_activas_lista else ["Sin deudas pendientes"], key="sel_deuda_abonar")
                    with col_ab2:
                        monto_abono = st.number_input("Monto a abonar (COP)", min_value=0, value=0, step=10000, format="%d", key="num_monto_abono")
                    
                    btn_abonar = st.form_submit_button("Aplicar Abono")
                    if btn_abonar and monto_abono > 0 and deuda_a_abonar != "Sin deudas pendientes":
                        deuda_actual = df_deudas.loc[df_deudas['deuda'] == deuda_a_abonar, 'monto_total'].values[0]
                        nuevo_monto = max(0, deuda_actual - monto_abono)
                        nuevo_estado = 'Completada' if nuevo_monto == 0 else 'Pendiente'
                        
                        ejecutar_sql("UPDATE deudas SET monto_total = %s, estado = %s WHERE deuda = %s", (float(nuevo_monto), nuevo_estado, deuda_a_abonar))
                        
                        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                        ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (%s, %s, %s, %s)",
                                     (fecha_hoy, 'Deuda', deuda_a_abonar, monto_abono))
                        
                        st.success(f"¡Abono de $ {monto_abono:,.0f} aplicado a '{deuda_a_abonar}'!".replace(",", "."))
                        st.rerun()

            st.subheader("📊 Progreso de abonos a deudas")
            
            df_deudas_melted = df_deudas_filtradas.melt(id_vars=['deuda'], value_vars=['monto_inicial', 'monto_total'],
                                                        var_name='Concepto', value_name='Monto')
            df_deudas_melted['Concepto'] = df_deudas_melted['Concepto'].replace({
                'monto_inicial': 'Deuda Inicial', 'monto_total': 'Saldo Pendiente'
            })
            
            escala_colores_deudas = alt.Scale(
                domain=['Deuda Inicial', 'Saldo Pendiente'],
                range=['#CC0000', '#FF6666']
            )

            grafico_deudas = alt.Chart(df_deudas_melted).mark_bar().encode(
                x=alt.X('deuda:N', title='Deuda', axis=alt.Axis(
                    labelAngle=0, 
                    labelExpr="split(datum.value, ' ')"
                )),
                y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='COP')),
                color=alt.Color('Concepto:N', scale=escala_colores_deudas),
                xOffset='Concepto:N',
                tooltip=[
                    alt.Tooltip('deuda:N', title='Deuda'), 
                    'Concepto', 
                    alt.Tooltip('Monto:Q', format=',.0f')
                ]
            ).properties(height=350)
            
            st.altair_chart(grafico_deudas, use_container_width=True)

            st.markdown("### 💳 Detalle de deudas")
            
            # --- 1. PREPARACIÓN DE DATOS Y CÁLCULO REAL ---
            try:
                df_log_deudas_calc = cargar_datos("SELECT * FROM log_abonos WHERE tipo = 'Deuda'")
                if not df_log_deudas_calc.empty:
                    abonos_agrupados = df_log_deudas_calc.groupby('referencia')['monto'].sum().reset_index()
                    abonos_agrupados.rename(columns={'referencia': 'deuda', 'monto': 'Abonado Acumulado (COP)'}, inplace=True)
                else:
                    abonos_agrupados = pd.DataFrame(columns=['deuda', 'Abonado Acumulado (COP)'])
            except:
                abonos_agrupados = pd.DataFrame(columns=['deuda', 'Abonado Acumulado (COP)'])

            df_deudas_mostrar = df_deudas_filtradas.copy()
            if not df_deudas_mostrar.empty:
                df_deudas_mostrar = pd.merge(df_deudas_mostrar, abonos_agrupados, on='deuda', how='left')
                df_deudas_mostrar['Abonado Acumulado (COP)'] = df_deudas_mostrar['Abonado Acumulado (COP)'].fillna(0)
                
                df_deudas_mostrar['monto_total'] = df_deudas_mostrar['monto_inicial'] - df_deudas_mostrar['Abonado Acumulado (COP)']
                df_deudas_mostrar['monto_total'] = df_deudas_mostrar['monto_total'].apply(lambda x: max(0, x))

                # --- 2. TABLA VISUAL DE LECTURA (Formato COP) ---
                df_deudas_visual = df_deudas_mostrar.copy()
                df_deudas_visual['Monto Inicial'] = df_deudas_visual['monto_inicial'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                df_deudas_visual['Saldo Pendiente'] = df_deudas_visual['monto_total'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                df_deudas_visual['Cuota Mensual'] = df_deudas_visual['cuota_mes'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                df_deudas_visual['Abonado Acumulado'] = df_deudas_visual['Abonado Acumulado (COP)'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                
                df_deudas_visual = df_deudas_visual[['deuda', 'Monto Inicial', 'Saldo Pendiente', 'Cuota Mensual', 'estado', 'Abonado Acumulado']]
                df_deudas_visual = df_deudas_visual.rename(columns={'deuda': 'Deuda', 'estado': 'Estado'})
                
                st.dataframe(df_deudas_visual, use_container_width=True)

                # --- 3. PANEL DESPLEGABLE DE EDICIÓN (Deudas) ---
                with st.expander("✏️ Editar o eliminar una deuda"):
                    deudas_lista = df_deudas_mostrar['deuda'].tolist()
                    deuda_sel = st.selectbox("Selecciona la deuda a modificar:", deudas_lista, key="sel_deuda_edit")
                    
                    if deuda_sel:
                        fila_sel = df_deudas_mostrar[df_deudas_mostrar['deuda'] == deuda_sel].iloc[0]
                        
                        col_d1, col_d2, col_d3 = st.columns(3)
                        with col_d1:
                            nueva_deuda = st.text_input("Nombre de la Deuda", value=fila_sel['deuda'], key="edit_nombre_deuda")
                            opciones_estado_d = ['Pendiente', 'Completada']
                            estado_actual_d = fila_sel['estado'] if fila_sel['estado'] in opciones_estado_d else 'Pendiente'
                            nuevo_estado_d = st.selectbox("Estado", opciones_estado_d, index=opciones_estado_d.index(estado_actual_d), key="edit_estado_deuda")
                        with col_d2:
                            nuevo_inicial = st.number_input("Monto Inicial (COP)", value=int(fila_sel['monto_inicial']), step=100000, format="%d", key="edit_monto_inicial_deuda")
                        with col_d3:
                            nueva_cuota = st.number_input("Cuota Mensual (COP)", value=int(fila_sel['cuota_mes']), step=50000, format="%d", key="edit_cuota_deuda")
                            
                        col_db1, col_db2 = st.columns(2)
                        with col_db1:
                            if st.button("Guardar Cambios en Deuda", use_container_width=True, key="btn_guardar_cambios_deudas"):
                                nuevo_saldo = float(nuevo_inicial) - float(fila_sel['Abonado Acumulado (COP)'])
                                nuevo_saldo = max(0, nuevo_saldo)
                                
                                if nuevo_saldo <= 0:
                                    nuevo_estado_d = 'Completada'
                                    
                                query = """
                                    UPDATE deudas 
                                    SET deuda = %s, monto_inicial = %s, monto_total = %s, cuota_mes = %s, estado = %s 
                                    WHERE id = %s
                                """
                                params = (nueva_deuda, float(nuevo_inicial), nuevo_saldo, float(nueva_cuota), nuevo_estado_d, int(fila_sel['id']))
                                ejecutar_sql(query, params)
                                st.success("¡Deuda actualizada!")
                                st.rerun()
                        with col_db2:
                            if st.button("Eliminar Deuda", type="primary", use_container_width=True, key="btn_eliminar_deuda"):
                                query = "DELETE FROM deudas WHERE id = %s"
                                ejecutar_sql(query, (int(fila_sel['id']),))
                                st.warning("¡Deuda eliminada!")
                                st.rerun()
            else:
                st.info("No hay deudas para mostrar en este momento.")

            # --- 4. TABLA VISUAL Y EDICIÓN DEL HISTORIAL DE ABONOS ---
            st.markdown("### 📜 Historial de abonos a deudas")
            
            if 'df_log_deudas_calc' in locals() and not df_log_deudas_calc.empty:
                df_log_deudas = df_log_deudas_calc.sort_values(by='id', ascending=False)
                
                df_log_deudas_visual = df_log_deudas.copy()
                df_log_deudas_visual['Monto Abonado'] = df_log_deudas_visual['monto'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                df_log_deudas_visual = df_log_deudas_visual[['fecha', 'referencia', 'Monto Abonado']].rename(columns={
                    'fecha': 'Fecha', 'referencia': 'Deuda'
                })
                st.dataframe(df_log_deudas_visual, use_container_width=True)

                with st.expander("✏️ Editar o Eliminar un Abono de Deuda"):
                    opciones_log_d = []
                    for _, row in df_log_deudas.iterrows():
                        etiqueta = f"ID {row['id']} | {row['fecha']} | {row['referencia']} | $ {row['monto']:,.0f}".replace(",", ".")
                        opciones_log_d.append((row['id'], etiqueta))
                    
                    etiquetas_log_d = [op[1] for op in opciones_log_d]
                    log_sel_etiqueta_d = st.selectbox("Selecciona el abono a modificar:", etiquetas_log_d, key="sel_log_deuda")
                    
                    if log_sel_etiqueta_d:
                        id_seleccionado_d = next(op[0] for op in opciones_log_d if op[1] == log_sel_etiqueta_d)
                        fila_log_d = df_log_deudas[df_log_deudas['id'] == id_seleccionado_d].iloc[0]
                        
                        col_ld1, col_ld2, col_ld3 = st.columns(3)
                        with col_ld1:
                            nueva_fecha_d = st.text_input("Fecha (YYYY-MM-DD)", value=str(fila_log_d['fecha']), key="fecha_d")
                        with col_ld2:
                            nueva_ref_d = st.text_input("Referencia (Deuda)", value=fila_log_d['referencia'], key="ref_d")
                        with col_ld3:
                            nuevo_monto_d = st.number_input("Monto Abonado (COP)", value=int(fila_log_d['monto']), step=50000, format="%d", key="monto_d")
                            
                        col_ldb1, col_ldb2 = st.columns(2)
                        with col_ldb1:
                            if st.button("Guardar Cambios en Historial", use_container_width=True, key="btn_save_log_d"):
                                query = "UPDATE log_abonos SET fecha = %s, referencia = %s, monto = %s WHERE id = %s"
                                ejecutar_sql(query, (nueva_fecha_d, nueva_ref_d, float(nuevo_monto_d), int(id_seleccionado_d)))
                                st.success("¡Historial actualizado!")
                                st.rerun()
                        with col_ldb2:
                            if st.button("Eliminar Registro", type="primary", use_container_width=True, key="btn_del_log_d"):
                                query = "DELETE FROM log_abonos WHERE id = %s"
                                ejecutar_sql(query, (int(id_seleccionado_d),))
                                st.warning("¡Registro eliminado!")
                                st.rerun()
            else:
                st.info("Aún no hay abonos registrados para deudas.")
        else:
            st.info("No hay deudas pendientes en este momento. ¡Buen trabajo!")
    else:
        st.info("No hay deudas registradas en el sistema.")

with pestana_metas:
    st.subheader("💰 Gestión de ahorro")

    with st.expander("➕ Registrar nueva meta de ahorro"):
        with st.form("form_meta", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                nombre_meta = st.text_input("Nombre de la Meta (Ej. Viaje a Europa)", key="input_meta_pestana_metas")
                estrategia_meta = st.text_input("Estrategia / Plataforma (Ej. Cajitas Nu)", key="input_estrategia_pestana_metas")
            with col_m2:
                monto_obj = st.number_input("Monto Objetivo (COP)", min_value=0, value=0, step=100000, format="%d")
                monto_act = st.number_input("Monto Actual Ahorrado (COP)", min_value=0, value=0, step=50000, format="%d")
                
            guardar_m = st.form_submit_button("Guardar meta de ahorro")
            if guardar_m and nombre_meta:
                estado_inicial_meta = 'Completada' if monto_act >= monto_obj and monto_obj > 0 else 'En curso'
                ejecutar_sql(
                    "INSERT INTO metas_ahorro (nombre_meta, monto_objetivo, monto_actual, estrategia, estado) VALUES (%s, %s, %s, %s, %s)",
                    (nombre_meta, monto_obj, monto_act, estrategia_meta, estado_inicial_meta)
                )
                st.success(f"¡Meta '{nombre_meta}' registrada con éxito!")
                st.rerun()

    if not df_metas.empty:
        ver_completadas_m = st.checkbox("Mostrar metas completadas", key="chk_comp_m")
        df_metas_filtradas = df_metas if ver_completadas_m else df_metas[df_metas['estado'] != 'Completada']

        if not df_metas_filtradas.empty:
            with st.expander("➕ Registrar nuevo abono a ahorro"):
                with st.form("form_abono_meta", clear_on_submit=True):
                    col_am1, col_am2 = st.columns(2)
                    with col_am1:
                        metas_activas_lista = df_metas[df_metas['estado'] != 'Completada']['nombre_meta'].tolist()
                        meta_a_abonar = st.selectbox("Selecciona la Meta", metas_activas_lista if metas_activas_lista else ["Sin metas en curso"])
                    with col_am2:
                        monto_ahorro_nuevo = st.number_input("Monto a Sumar al Ahorro (COP)", min_value=0, value=0, step=50000, format="%d")
                    
                    btn_sumar_ahorro = st.form_submit_button("Actualizar Ahorro")
                    if btn_sumar_ahorro and monto_ahorro_nuevo > 0 and meta_a_abonar != "Sin metas en curso":
                        meta_row = df_metas.loc[df_metas['nombre_meta'] == meta_a_abonar].iloc[0]
                        ahorro_actual = meta_row['monto_actual']
                        monto_obj_val = meta_row['monto_objetivo']
                        
                        nuevo_ahorro = ahorro_actual + monto_ahorro_nuevo
                        nuevo_estado_meta = 'Completada' if nuevo_ahorro >= monto_obj_val else 'En curso'
                        
                        ejecutar_sql("UPDATE metas_ahorro SET monto_actual = %s, estado = %s WHERE nombre_meta = %s", 
                                     (float(nuevo_ahorro), nuevo_estado_meta, meta_a_abonar))
                        
                        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                        ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (%s, %s, %s, %s)",
                                     (fecha_hoy, 'Meta', meta_a_abonar, monto_ahorro_nuevo))
                        
                        st.success(f"¡Se sumaron $ {monto_ahorro_nuevo:,.0f} a la meta '{meta_a_abonar}'!".replace(",", "."))
                        st.rerun()

            st.subheader("📊 Progreso de metas de ahorro")
            df_metas_melted = df_metas_filtradas.melt(id_vars=['nombre_meta'], value_vars=['monto_objetivo', 'monto_actual'],
                                                     var_name='Tipo', value_name='Monto')
            df_metas_melted['Tipo'] = df_metas_melted['Tipo'].replace({
                'monto_objetivo': 'Objetivo', 'monto_actual': 'Ahorrado Actual'
            })
            
            # 1. Definimos la escala de colores explícita 
            escala_colores_metas = alt.Scale(
                domain=['Ahorrado Actual', 'Objetivo'], # Nombres exactos de tu variable 'Tipo'
                range=['#005B9F', '#79C1F8']            # Azul oscuro y Azul claro
            )

            grafico_metas = alt.Chart(df_metas_melted).mark_bar().encode(
                # 1. labelAngle=0 mantiene el texto estrictamente horizontal
                # 2. labelExpr="split(datum.value, ' ')" fuerza el salto de línea en cada espacio
                x=alt.X('nombre_meta:N', title='Meta', axis=alt.Axis(
                    labelAngle=0, 
                    labelExpr="split(datum.value, ' ')"
                )),
                y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='COP')),
                
                # 3. Inyectamos la escala en el parámetro color
                color=alt.Color('Tipo:N', scale=escala_colores_metas),
                
                xOffset='Tipo:N',
                tooltip=[
                    alt.Tooltip('nombre_meta:N', title='Meta'), 
                    'Tipo', 
                    alt.Tooltip('Monto:Q', format=',.0f')
                ]
            ).properties(height=350)
            
            st.altair_chart(grafico_metas, use_container_width=True)

            st.markdown("### 🎯 Detalle de metas de ahorro")
            
            # --- 1. TABLA VISUAL DE METAS (Lectura con formato COP impecable) ---
            df_metas_mostrar = df_metas_filtradas.copy()

            # Cálculos matemáticos previos
            df_metas_mostrar['Restante (COP)'] = df_metas_mostrar['monto_objetivo'] - df_metas_mostrar['monto_actual']
            df_metas_mostrar['Restante (COP)'] = df_metas_mostrar['Restante (COP)'].apply(lambda x: max(0, x))
            df_metas_mostrar['Progreso (%)'] = (df_metas_mostrar['monto_actual'] / df_metas_mostrar['monto_objetivo']) * 100

            # Aplicamos la capa de formato estético (Puntos de mil y símbolo $)
            df_metas_mostrar['Monto Objetivo'] = df_metas_mostrar['monto_objetivo'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_metas_mostrar['Ahorrado Actual'] = df_metas_mostrar['monto_actual'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_metas_mostrar['Restante (COP)'] = df_metas_mostrar['Restante (COP)'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_metas_mostrar['Progreso (%)'] = df_metas_mostrar['Progreso (%)'].apply(lambda x: f"{x:.2f}%")

            # Organizamos las columnas para presentarlas (SIN EL ID)
            df_metas_visual = df_metas_mostrar[['nombre_meta', 'Monto Objetivo', 'Ahorrado Actual', 'estrategia', 'estado', 'Restante (COP)', 'Progreso (%)']]
            df_metas_visual = df_metas_visual.rename(columns={'nombre_meta': 'Meta', 'estrategia': 'Estrategia', 'estado': 'Estado'})

            st.dataframe(df_metas_visual, use_container_width=True, hide_index=True)

            # --- 2. PANEL DESPLEGABLE DE EDICIÓN (Metas) ---
            with st.expander("✏️ Editar o eliminar una meta de ahorro"):
                metas_lista = df_metas_filtradas['nombre_meta'].tolist()
                meta_sel = st.selectbox("Selecciona la meta a modificar:", metas_lista, key="sel_meta_edit")
                
                if meta_sel:
                    # Extraemos la fila original de la base de datos (con números puros)
                    fila_sel = df_metas_filtradas[df_metas_filtradas['nombre_meta'] == meta_sel].iloc[0]
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        nuevo_nombre = st.text_input("Nombre de la Meta", value=fila_sel['nombre_meta'], key="input_nueva_meta_pestana_metas")
                        nueva_estrategia = st.text_input("Estrategia", value=fila_sel['estrategia'], key="input_nueva_estrategia_pestana_metas")
                    with col_m2:
                        nuevo_objetivo = st.number_input("Monto Objetivo (COP)", value=int(fila_sel['monto_objetivo']), step=100000, format="%d")
                        nuevo_actual = st.number_input("Ahorrado Actual (COP)", value=int(fila_sel['monto_actual']), step=50000, format="%d")
                    with col_m3:
                        opciones_estado = ['En curso', 'Completada', 'Pausada']
                        estado_actual = fila_sel['estado'] if fila_sel['estado'] in opciones_estado else 'En curso'
                        nuevo_estado = st.selectbox("Estado", opciones_estado, index=opciones_estado.index(estado_actual))

                    col_mb1, col_mb2 = st.columns(2)
                    with col_mb1:
                        if st.button("Guardar Cambios", use_container_width=True, key="guardar_cambios_metas"):
                            # Control inteligente: Si el nuevo ahorro supera el objetivo, se marca completada sola
                            if nuevo_actual >= nuevo_objetivo:
                                nuevo_estado = 'Completada'
                                
                            query = """
                                UPDATE metas_ahorro 
                                SET nombre_meta = %s, monto_objetivo = %s, monto_actual = %s, estrategia = %s, estado = %s 
                                WHERE id = %s
                            """
                            params = (nuevo_nombre, float(nuevo_objetivo), float(nuevo_actual), nueva_estrategia, nuevo_estado, int(fila_sel['id']))
                            ejecutar_sql(query, params)
                            st.success("¡Meta actualizada correctamente!")
                            st.rerun()
                            
                    with col_mb2:
                        # Botón destructivo en rojo (type="primary" en temas oscuros/claros de Streamlit)
                        if st.button("Eliminar Meta", type="primary", use_container_width=True, key="btn_eliminar_metas"):
                            query = "DELETE FROM metas_ahorro WHERE id = %s"
                            ejecutar_sql(query, (int(fila_sel['id']),))
                            st.warning("¡Meta eliminada!")
                            st.rerun()

            # --- 3. TABLA VISUAL Y EDICIÓN DEL HISTORIAL DE ABONOS ---
            st.markdown("### 📜 Historial abonos a metas")
            
            try:
                df_log_metas = cargar_datos("SELECT * FROM log_abonos WHERE tipo = 'Meta' ORDER BY id DESC")
            except:
                df_log_metas = pd.DataFrame()

            if not df_log_metas.empty:
                # Tabla Visual Historial
                df_log_metas_visual = df_log_metas.copy()
                df_log_metas_visual['Monto Abonado'] = df_log_metas_visual['monto'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                
                # Seleccionamos y renombramos sin incluir el ID
                df_log_metas_visual = df_log_metas_visual[['fecha', 'referencia', 'Monto Abonado']].rename(columns={
                    'fecha': 'Fecha', 
                    'referencia': 'Meta'
                })
                
                st.dataframe(df_log_metas_visual, use_container_width=True, hide_index=True)

                # Panel de Edición Historial
                with st.expander("✏️ Editar o Eliminar un Abono del Historial"):
                    # Construimos etiquetas amigables para encontrar fácilmente el registro
                    opciones_log = []
                    for _, row in df_log_metas.iterrows():
                        etiqueta = f"ID {row['id']} | {row['fecha']} | {row['referencia']} | $ {row['monto']:,.0f}".replace(",", ".")
                        opciones_log.append((row['id'], etiqueta))
                    
                    etiquetas_log = [op[1] for op in opciones_log]
                    log_sel_etiqueta = st.selectbox("Selecciona el registro a modificar:", etiquetas_log)
                    
                    if log_sel_etiqueta:
                        # Vinculamos la etiqueta visual con el ID real
                        id_seleccionado = next(op[0] for op in opciones_log if op[1] == log_sel_etiqueta)
                        fila_log = df_log_metas[df_log_metas['id'] == id_seleccionado].iloc[0]
                        
                        col_l1, col_l2, col_l3 = st.columns(3)
                        with col_l1:
                            nueva_fecha_log = st.text_input("Fecha (YYYY-MM-DD)", value=str(fila_log['fecha']), key="input_nueva_fecha_pestana_metas")
                        with col_l2:
                            nueva_ref_log = st.text_input("Referencia (Meta)", value=fila_log['referencia'], key="input_nueva_referencia_meta_pestana_metas")
                        with col_l3:
                            nuevo_monto_log = st.number_input("Monto Abonado (COP)", value=int(fila_log['monto']), step=50000, format="%d")
                            
                        col_lb1, col_lb2 = st.columns(2)
                        with col_lb1:
                            # Agregamos un 'key' único para que Streamlit no se confunda con otros botones
                            if st.button("Guardar Cambios", use_container_width=True, key="btn_guardar_historial_metas"):
                                query = "UPDATE log_abonos SET fecha = %s, referencia = %s, monto = %s WHERE id = %s"
                                ejecutar_sql(query, (nueva_fecha_log, nueva_ref_log, float(nuevo_monto_log), int(id_seleccionado)))
                                st.success("¡Historial actualizado!")
                                st.rerun()
                        with col_lb2:
                            # Hacemos lo mismo para el botón de eliminar por precaución
                            if st.button("Eliminar Registro", type="primary", use_container_width=True, key="btn_eliminar_historial_metas"):
                                query = "DELETE FROM log_abonos WHERE id = %s"
                                ejecutar_sql(query, (int(id_seleccionado),))
                                st.warning("¡Registro eliminado!")
                                st.rerun()
            else:
                st.info("Aún no hay abonos registrados para metas.")
                
        else:
            st.info("No hay metas de ahorro en curso en este momento.")
    else:
        st.info("No hay metas de ahorro registradas.")

with pestana_inversiones:
    st.subheader("💎 Patrimonio neto e inversiones")
    
    # 1. Cálculos principales
    total_inversiones = df_inversiones['monto_invertido'].sum() if not df_inversiones.empty else 0
    
    # Calcula las deudas pendientes actuales
    total_deudas_pendientes = 0
    if 'df_deudas' in locals() and not df_deudas.empty:
        total_deudas_pendientes = df_deudas[df_deudas['estado'] != 'Completada']['monto_total'].sum()
    else:
        try:
            df_deudas_temp = cargar_datos("SELECT monto_total FROM deudas WHERE estado != 'Completada'")
            total_deudas_pendientes = df_deudas_temp['monto_total'].sum() if not df_deudas_temp.empty else 0
        except:
            total_deudas_pendientes = 0

    patrimonio_neto = total_inversiones - total_deudas_pendientes

    # Mostrar Métricas Principales en tarjetas
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="Patrimonio Neto Total", value=f"$ {patrimonio_neto:,.0f}".replace(",", "."))
    with col_m2:
        st.metric(label="Total Invertido", value=f"$ {total_inversiones:,.0f}".replace(",", "."))
    with col_m3:
        st.metric(label="Deudas Totales (Pendientes)", value=f"$ {total_deudas_pendientes:,.0f}".replace(",", "."))

    # 2. Formulario para registrar o actualizar activos/inversiones
    with st.expander("➕ Registrar nueva inversión"):
        with st.form("form_inversion", clear_on_submit=True):
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                activo_input = st.text_input("Nombre del activo (Ej. S&P 500 VOO, TSMC)", key="input_activo_pestana_patrimonio")
            with col_i2:
                monto_inv_input = st.number_input("Monto actual invertido (COP)", min_value=0, value=0, step=50000, format="%d")
                
            guardar_inv = st.form_submit_button("Guardar Inversión")
            if guardar_inv and activo_input:
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                ejecutar_sql(
                    "INSERT INTO inversiones (fecha, activo, monto_invertido) VALUES (%s, %s, %s)",
                    (fecha_hoy, activo_input, monto_inv_input)
                )
                st.success(f"¡Inversión en '{activo_input}' registrada exitosamente!")
                st.rerun()

    # 3. Visualización y Gráfico
    if not df_inversiones.empty:
        st.subheader("📊 Distribución del portafolio")
        
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            # 1. TABLA VISUAL DE LECTURA (Con formato COP impecable)
            df_inv_mostrar = df_inversiones.copy()
            df_inv_mostrar['monto_invertido'] = df_inv_mostrar['monto_invertido'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            
            # Seleccionamos y renombramos únicamente las columnas que queremos mostrar (sin el ID)
            df_inv_mostrar = df_inv_mostrar[['fecha', 'activo', 'monto_invertido']].rename(columns={
                'fecha': 'Fecha Registro', 
                'activo': 'Activo', 
                'monto_invertido': 'Monto Invertido (COP)'
            })
            
            st.dataframe(df_inv_mostrar, use_container_width=True, hide_index=True)

            # 2. PANEL DESPLEGABLE DE EDICIÓN
            with st.expander("✏️ Editar o eliminar un activo existente"):
                activos_lista = df_inversiones['activo'].tolist()
                activo_sel = st.selectbox("Selecciona el activo a modificar:", activos_lista)
                
                if activo_sel:
                    # Traemos los datos crudos actuales del activo seleccionado
                    fila_sel = df_inversiones[df_inversiones['activo'] == activo_sel].iloc[0]
                    
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        nuevo_nombre_activo = st.text_input("Nombre del activo", value=fila_sel['activo'], key="input_nombre_activo_pestana_metas")
                    with col_ed2:
                        nuevo_monto_activo = st.number_input(
                            "Monto invertido (COP)", 
                            value=int(fila_sel['monto_invertido']), 
                            step=50000, 
                            format="%d"
                        )
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("Guardar Cambios", use_container_width=True, key="btn_guardar_cambios_inversiones"):
                            query = "UPDATE inversiones SET activo = %s, monto_invertido = %s WHERE id = %s"
                            ejecutar_sql(query, (nuevo_nombre_activo, float(nuevo_monto_activo), int(fila_sel['id'])))
                            st.success("¡Activo actualizado!")
                            st.rerun()
                            
                    with col_b2:
                        if st.button("Eliminar Activo", type="primary", use_container_width=True, key="btn_eliminar_activo"):
                            query = "DELETE FROM inversiones WHERE id = %s"
                            ejecutar_sql(query, (int(fila_sel['id']),))
                            st.warning("¡Activo eliminado!")
                            st.rerun()
            
        with col_g2:
            grafico_inversiones = alt.Chart(df_inversiones).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="monto_invertido", type="quantitative"),
                # 1. Agregamos title="Activo" al color para arreglar el título de la leyenda
                color=alt.Color(field="activo", type="nominal", title="Activo"),
                
                # 2. Reestructuramos el tooltip para darle un 'title' a cada variable
                tooltip=[
                    alt.Tooltip('activo:N', title="Activo"), 
                    alt.Tooltip('monto_invertido:Q', title="Monto Invertido", format=',.0f')
                ]
            ).properties(height=300)
            
            st.altair_chart(grafico_inversiones, use_container_width=True)
    else:
        st.info("Aún no tienes inversiones registradas. Usa el formulario de arriba para agregar tu primer activo (ej. VOO o TSMC).")

with pestana_patrones:
    st.subheader("🕵️ Detector de Patrones y Hábitos")
    st.markdown("Aquí analizamos el comportamiento de tus gastos para mostrarte alertas basadas en tus costumbres de consumo.")

    # Verificamos si tienes la variable de transacciones del mes cargada
    if 'df_mes_actual' in locals() and not df_mes_actual.empty:
        df_patrones = df_mes_actual.copy()
        
        # Convertimos la fecha a formato datetime
        df_patrones['fecha_dt'] = pd.to_datetime(df_patrones['fecha'])
        df_patrones['dia_semana'] = df_patrones['fecha_dt'].dt.day_name()
        df_patrones['dia_numero'] = df_patrones['fecha_dt'].dt.day

        # Traducimos los días al español
        dias_es = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df_patrones['dia_semana'] = df_patrones['dia_semana'].map(dias_es)

        gasto_total = df_patrones['monto'].sum()
        gasto_primera_semana = df_patrones[df_patrones['dia_numero'] <= 7]['monto'].sum()
        porcentaje_primera = (gasto_primera_semana / gasto_total) * 100 if gasto_total > 0 else 0

        # --- SECCIÓN 1: RITMO Y DÍAS DE RIESGO ---
        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.markdown("### ⏳ Ritmo de Gasto")
            if porcentaje_primera > 40:
                st.error(f"🚨 **Alerta de inicio de mes:** Te gastaste el **{porcentaje_primera:.0f}%** de tu dinero en los primeros 7 días. Cuidado con dosificar mejor para no llegar apretado a fin de mes.")
            else:
                st.success(f"✅ **Buen ritmo:** Tu gasto en la primera semana fue del **{porcentaje_primera:.0f}%**. Mantener este nivel indica un excelente control de flujo de caja inicial.")

        with col_p2:
            st.markdown("### 📅 Días de Riesgo")
            gasto_por_dia = df_patrones.groupby('dia_semana')['monto'].sum().sort_values(ascending=False)
            
            if not gasto_por_dia.empty:
                dia_top = gasto_por_dia.index[0]
                porcentaje_top = (gasto_por_dia.iloc[0] / gasto_total) * 100
                st.warning(f"💸 **Fuga recurrente:** Los **{dia_top}s** son tus días de mayor gasto. Representan el **{porcentaje_top:.0f}%** de todas tus salidas de dinero de este mes.")

        # Análisis específico para Comida Fuera
        df_comida = df_patrones[df_patrones['categoria'].str.lower().str.contains('comida fuera', na=False)]
        if not df_comida.empty:
            dia_comida = df_comida.groupby('dia_semana')['monto'].sum().sort_values(ascending=False).index[0]
            st.info(f"🍔 **Patrón de Antojos:** La mayor parte de tus gastos en 'Comida fuera' ocurren los **{dia_comida}s**. Si quieres optimizar tus ahorros, este es el día clave para planear algo en casa.")

        st.markdown("---")

        # --- SECCIÓN 2: ANÁLISIS AVANZADO (Frecuencia y Quincenas) ---
        st.subheader("📊 Análisis Avanzado de Comportamiento")
        
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.markdown("### 🔄 Frecuencia por Categoría")
            # Agrupamos para contar cuántas transacciones haces por categoría y cuánto suman
            frecuencia_cat = df_patrones.groupby('categoria').agg(
                transacciones=('monto', 'count'),
                total_gastado=('monto', 'sum')
            ).sort_values(by='transacciones', ascending=False).reset_index()

            if not frecuencia_cat.empty:
                for _, row in frecuencia_cat.head(4).iterrows():
                    st.markdown(f"- **{row['categoria']}**: {int(row['transacciones'])} veces este mes (Total: $ {row['total_gastado']:,.0f})".replace(",", "."))
            else:
                st.info("No hay suficientes datos de categorías aún.")

        with col_a2:
            st.markdown("### ⚖️ Comparativa de Quincenas")
            # Dividimos el mes en quincena 1 (días 1 al 15) y quincena 2 (del 16 en adelante)
            q1 = df_patrones[df_patrones['dia_numero'] <= 15]['monto'].sum()
            q2 = df_patrones[df_patrones['dia_numero'] > 15]['monto'].sum()
            total_q = q1 + q2

            if total_q > 0:
                p_q1 = (q1 / total_q) * 100
                p_q2 = (q2 / total_q) * 100

                st.markdown(f"- **1ra Quincena (Días 1-15):** $ {q1:,.0f} ({p_q1:.0f}%)".replace(",", "."))
                st.markdown(f"- **2da Quincena (Días 16-31):** $ {q2:,.0f} ({p_q2:.0f}%)".replace(",", "."))

                if p_q1 > 65:
                    st.warning("⚠️ **Efecto Rebote:** Estás concentrando más del 65% de tus gastos en la primera mitad del mes.")
                elif abs(p_q1 - p_q2) < 10:
                    st.success("✅ **Gasto Equilibrado:** Tus salidas de dinero están muy bien distribuidas entre ambas quincenas.")
                else:
                    st.info("ℹ️ Mayor volumen de gasto registrado en la segunda quincena.")
            else:
                st.info("Aún no hay transacciones suficientes para comparar quincenas.")
            
    else:
        st.info("Aún no hay suficientes transacciones registradas este mes para activar el detector de patrones.")

with pestana_control:
    st.subheader("🎯 Radar de Desviación Presupuestaria")

    if not df_presupuestos.empty and not df_transacciones.empty:
        # Asegúrate de que ambas tablas tengan una columna de categoría en común (ej. 'categoria')
        if 'categoria' in df_presupuestos.columns and 'categoria' in df_transacciones.columns:
            # Sumamos los gastos reales por categoría en el mes actual
            gastos_por_cat = df_mes_actual.groupby('categoria')['monto'].sum().reset_index()
            
            # Unimos presupuesto vs real
            comparativa = pd.merge(df_presupuestos, gastos_por_cat, on='categoria', how='left', suffixes=('_presupuestado', '_real'))
            comparativa['monto_real'] = comparativa['monto_real'].fillna(0)
            
            # Renombramos columnas de forma segura según tu estructura de BD
            col_p = next((c for c in ['monto', 'presupuesto', 'limite'] if c in comparativa.columns), None)
            
            if col_p:
                comparativa['Desviación'] = comparativa['monto_real'] - comparativa[col_p]
                comparativa['% Ejecución'] = (comparativa['monto_real'] / comparativa[col_p]) * 100
                
                st.dataframe(comparativa[['categoria', col_p, 'monto_real', 'Desviación', '% Ejecución']], use_container_width=True)
            else:
                st.warning("No se encontró la columna de monto límite en la tabla de presupuestos.")
        else:
            st.info("Las tablas 'presupuestos' y 'transacciones' deben compartir una columna llamada 'categoria'.")
    else:
        st.info("Faltan datos en las tablas de presupuestos o transacciones para generar el radar.")

with pestana_salud:

    st.subheader("💳 Salud de Endeudamiento")

    # Verificamos que existan deudas con cuota mensual
    if not df_deudas.empty:
        posibles_col_cuota = ['cuota_mensual', 'cuota', 'pago_mensual']
        col_cuota = next((c for c in posibles_col_cuota if c in df_deudas.columns), None)
        
        if col_cuota:
            total_cuotas_mes = float(pd.to_numeric(df_deudas[col_cuota], errors='coerce').sum())
            porcentaje_endeudamiento = (total_cuotas_mes / salario_actual) * 100
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.metric(label="Total Cuotas Mensuales", value=f"$ {total_cuotas_mes:,.0f}".replace(",", "."))
            with col_e2:
                st.metric(label="Compromiso de Ingresos", value=f"{porcentaje_endeudamiento:.1f}%")
                
            if porcentaje_endeudamiento <= 30:
                st.success("🟢 Tu nivel de endeudamiento es saludable (menor al 30% de tus ingresos).")
            elif porcentaje_endeudamiento <= 40:
                st.warning("🟡 Estás en zona de alerta (entre 30% y 40% de tus ingresos en deudas).")
            else:
                st.error("🔴 ¡Riesgo alto! Estás destinando más del 40% de tus ingresos a deudas.")
        else:
            st.info("Añade una columna de cuota mensual en tu tabla de deudas para activar este indicador con precisión.")
    else:
        st.info("No hay registros de deudas actualmente.")

    st.subheader("📅 Estacionalidad de Gastos por Mes")

    if not df_transacciones.empty and 'fecha' in df_transacciones.columns and 'monto' in df_transacciones.columns:
        df_temp = df_transacciones.copy()
        df_temp['fecha_dt'] = pd.to_datetime(df_temp['fecha'], errors='coerce')
        df_temp['Mes_Num'] = df_temp['fecha_dt'].dt.month
        df_temp['Mes_Nombre'] = df_temp['fecha_dt'].dt.strftime('%B')
        
        # Filtramos solo gastos (asumiendo montos negativos o una columna de tipo)
        # Si tus gastos son positivos, puedes omitir el filtro de signo o ajustarlo según tu BD
        gastos_mensuales = df_temp.groupby(['Mes_Num', 'Mes_Nombre'])['monto'].sum().reset_index()
        gastos_mensuales = gastos_mensuales.sort_values('Mes_Num')
        
        if not gastos_mensuales.empty:
            st.bar_chart(data=gastos_mensuales, x='Mes_Nombre', y='monto')
        else:
            st.info("No hay suficientes datos históricos para calcular la estacionalidad.")
    else:
        st.info("La tabla de transacciones necesita datos válidos de fecha y monto.")

st.sidebar.title("Navegación")
st.sidebar.info(
    "Panel conectado a `finance_bot.db`. "
    "Logs independientes por pestaña y cálculo dinámico de montos restantes."
)