import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

# Configuración de la página web
st.set_page_config(
    page_title="Centro de Comando Financiero",
    page_icon="📊",
    layout="wide"
)

def ejecutar_sql(query, params=()):
    conexion = sqlite3.connect("finance_bot.db")
    cursor = conexion.cursor()
    cursor.execute(query, params)
    conexion.commit()
    conexion.close()

def cargar_datos(query):
    conexion = sqlite3.connect("finance_bot.db")
    df = pd.read_sql(query, conexion)
    conexion.close()
    return df

st.title("📊 Centro de Comando Financiero")
st.markdown("Monitoreo en vivo de tus transacciones, presupuestos, deudas y metas de ahorro.")
st.divider()

# Cargar datos de la base de datos
try:
    df_transacciones = cargar_datos("SELECT * FROM transacciones ORDER BY id")
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

# Pestañas de navegación organizadas
pestana_trans, pestana_presupuestos, pestana_deudas, pestana_metas, pestana_inversiones = st.tabs([
    "📝 Transacciones", 
    "🎯 Presupuestos & Tipos", 
    "💳 Deudas", 
    "💰 Metas de Ahorro",
    "💎 Patrimonio & Inversiones"
])

with pestana_trans:
    st.subheader("Historial de Transacciones (Telegram)")
    if not df_transacciones.empty:
        df_mostrar = df_transacciones.rename(columns={
            'id': 'ID', 'fecha': 'Fecha', 'concepto': 'Concepto',
            'categoria': 'Categoría', 'monto': 'Monto', 'metodo_pago': 'Método de Pago'
        })
        df_mostrar['Monto'] = df_mostrar['Monto'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
        st.dataframe(df_mostrar, use_container_width=True)
        
        st.subheader("Gastos por Categoría")
        df_categoria = df_transacciones.groupby('categoria')['monto'].sum().reset_index()
        df_categoria.columns = ['Categoría', 'Monto']
        
        grafico = alt.Chart(df_categoria).mark_bar().encode(
            x=alt.X('Categoría:N', sort='-y'),
            y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='Monto (COP)')),
            color=alt.Color('Categoría:N', legend=None),
            tooltip=['Categoría:N', alt.Tooltip('Monto:Q', format=',.0f')]
        ).properties(height=350)
        st.altair_chart(grafico, use_container_width=True)
    else:
        st.info("Aún no hay transacciones registradas. ¡Escríbele a tu bot de Telegram!")

with pestana_presupuestos:
    st.subheader("Gestión de Presupuestos (Enfoque 50/30/20)")
    
    col_sal1, col_sal2, col_sal3 = st.columns(3)
    with col_sal1:
        salario_mes = st.number_input("Ingreso / Salario del Mes (COP)", min_value=0, value=5000000, step=100000, format="%d")
    
    total_presupuestado = df_presupuestos['limite'].sum() if not df_presupuestos.empty else 0
    disponible_por_asignar = salario_mes - total_presupuestado
    
    with col_sal2:
        st.metric(label="Total Presupuestado", value=f"$ {total_presupuestado:,.0f}".replace(",", "."))
    with col_sal3:
        st.metric(label="Disponible por Asignar", value=f"$ {disponible_por_asignar:,.0f}".replace(",", "."))

    st.markdown("---")
    
    with st.form("form_presupuesto", clear_on_submit=True):
        st.markdown("**Asignar presupuesto, categoría y clasificación**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            mes_input = st.text_input("Mes (Ej. 2026-07)", value="2026-07")
            cat_input = st.text_input("Categoría (Ej. Mercado, VOO, Arriendo)")
        with col_p2:
            tipo_input = st.selectbox(
                "Tipo de Presupuesto", 
                ["Necesidad", "Ahorro", "Inversión", "Gasto General"]
            )
            limite_input = st.number_input("Límite Presupuestado (COP)", min_value=0, value=0, step=50000, format="%d")
            
        guardar_p = st.form_submit_button("Guardar Presupuesto")
        if guardar_p and cat_input:
            ejecutar_sql(
                "INSERT INTO presupuestos (mes, categoria, tipo, limite) VALUES (?, ?, ?, ?)",
                (mes_input, cat_input.capitalize(), tipo_input, limite_input)
            )
            st.success(f"¡Presupuesto para {cat_input} guardado exitosamente!")
            st.rerun()

    st.markdown("---")
    st.subheader("Tus Presupuestos Registrados")
    if not df_presupuestos.empty:
        if total_presupuestado > 0:
            df_presupuestos['Porcentaje'] = (df_presupuestos['limite'] / total_presupuestado) * 100
            df_presupuestos['Porcentaje_Str'] = df_presupuestos['Porcentaje'].apply(lambda x: f"{x:.2f}%")
        else:
            df_presupuestos['Porcentaje_Str'] = "0.00%"
            
        df_presup_mostrar = df_presupuestos.rename(columns={
            'id': 'ID', 'mes': 'Mes', 'categoria': 'Categoría', 
            'tipo': 'Tipo', 'limite': 'Límite (COP)', 'Porcentaje_Str': '% del Total'
        })
        df_presup_mostrar['Límite (COP)'] = df_presup_mostrar['Límite (COP)'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
        st.dataframe(df_presup_mostrar, use_container_width=True)
        
        st.markdown("### 📊 Distribución por Tipo de Gasto / Inversión")
        df_tipo_resumen = df_presupuestos.groupby('tipo')['limite'].sum().reset_index()
        df_tipo_resumen['Porcentaje'] = (df_tipo_resumen['limite'] / total_presupuestado) * 100 if total_presupuestado > 0 else 0
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            df_tipo_mostrar = df_tipo_resumen.copy()
            df_tipo_mostrar['Porcentaje'] = df_tipo_mostrar['Porcentaje'].apply(lambda x: f"{x:.2f}%")
            df_tipo_mostrar['limite'] = df_tipo_mostrar['limite'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_tipo_mostrar.columns = ['Tipo', 'Límite (COP)', '% del Total']
            st.dataframe(df_tipo_mostrar, use_container_width=True)
        with col_t2:
            grafico_tipo = alt.Chart(df_tipo_resumen).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="limite", type="quantitative"),
                color=alt.Color(field="tipo", type="nominal"),
                tooltip=['tipo', alt.Tooltip('limite:Q', format=',.0f'), alt.Tooltip('Porcentaje:Q', format='.2f')]
            ).properties(height=250)
            st.altair_chart(grafico_tipo, use_container_width=True)
    else:
        st.info("No hay presupuestos configurados todavía.")

with pestana_deudas:
    st.subheader("Control y Registro de Deudas")
    
    with st.form("form_deuda", clear_on_submit=True):
        st.markdown("**Registrar nueva deuda activa**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            deuda_input = st.text_input("Deuda (Ej. T.C. Bancolombia, Curso de inglés)")
            estado_deuda = st.selectbox("Estado inicial", ["Pendiente", "Completada"])
        with col_d2:
            monto_total_deuda = st.number_input("Monto Total Inicial (COP)", min_value=0, value=0, step=50000, format="%d")
            cuota_mes_deuda = st.number_input("Cuota o Pago Mínimo del Mes (COP)", min_value=0, value=0, step=10000, format="%d")
            
        guardar_d = st.form_submit_button("Guardar Deuda")
        if guardar_d and deuda_input:
            ejecutar_sql(
                "INSERT INTO deudas (deuda, monto_inicial, monto_total, cuota_mes, estado) VALUES (?, ?, ?, ?, ?)",
                (deuda_input, monto_total_deuda, monto_total_deuda, cuota_mes_deuda, estado_deuda)
            )
            st.success(f"¡Deuda '{deuda_input}' registrada exitosamente!")
            st.rerun()

    st.markdown("---")
    if not df_deudas.empty:
        ver_completadas_d = st.checkbox("Mostrar deudas completadas / pagadas", key="chk_comp_d")
        df_deudas_filtradas = df_deudas if ver_completadas_d else df_deudas[df_deudas['estado'] != 'Completada']

        if not df_deudas_filtradas.empty:
            st.markdown("### 💸 Registrar Abono a Deuda")
            with st.form("form_abono_deuda", clear_on_submit=True):
                col_ab1, col_ab2 = st.columns(2)
                with col_ab1:
                    deudas_activas_lista = df_deudas[df_deudas['estado'] != 'Completada']['deuda'].tolist()
                    deuda_a_abonar = st.selectbox("Selecciona la Deuda", deudas_activas_lista if deudas_activas_lista else ["Sin deudas pendientes"])
                with col_ab2:
                    monto_abono = st.number_input("Monto a Abonar (COP)", min_value=0, value=0, step=10000, format="%d")
                
                btn_abonar = st.form_submit_button("Aplicar Abono")
                if btn_abonar and monto_abono > 0 and deuda_a_abonar != "Sin deudas pendientes":
                    deuda_actual = df_deudas.loc[df_deudas['deuda'] == deuda_a_abonar, 'monto_total'].values[0]
                    nuevo_monto = max(0, deuda_actual - monto_abono)
                    nuevo_estado = 'Completada' if nuevo_monto == 0 else 'Pendiente'
                    
                    ejecutar_sql("UPDATE deudas SET monto_total = ?, estado = ? WHERE deuda = ?", (nuevo_monto, nuevo_estado, deuda_a_abonar))
                    
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?, ?, ?, ?)",
                                 (fecha_hoy, 'Deuda', deuda_a_abonar, monto_abono))
                    
                    st.success(f"¡Abono de $ {monto_abono:,.0f} aplicado a '{deuda_a_abonar}'!".replace(",", "."))
                    st.rerun()

            st.markdown("---")
            st.subheader("📊 Comparativa de Deudas (Inicial vs Saldo Actual)")
            
            df_deudas_melted = df_deudas_filtradas.melt(id_vars=['deuda'], value_vars=['monto_inicial', 'monto_total'],
                                                        var_name='Concepto', value_name='Monto')
            df_deudas_melted['Concepto'] = df_deudas_melted['Concepto'].replace({
                'monto_inicial': 'Deuda Inicial', 'monto_total': 'Saldo Pendiente'
            })
            
            grafico_deudas = alt.Chart(df_deudas_melted).mark_bar().encode(
                x=alt.X('deuda:N', title='Deuda'),
                y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='COP')),
                color='Concepto:N',
                xOffset='Concepto:N',
                tooltip=['deuda', 'Concepto', alt.Tooltip('Monto:Q', format=',.0f')]
            ).properties(height=350)
            st.altair_chart(grafico_deudas, use_container_width=True)

            st.markdown("### Detalle de Deudas y Restante")
            df_deudas_mostrar = df_deudas_filtradas.copy()
            # Calcular lo ya abonado como la diferencia entre inicial y total actual
            df_deudas_mostrar['Abonado Acumulado'] = df_deudas_mostrar['monto_inicial'] - df_deudas_mostrar['monto_total']
            
            df_deudas_mostrar = df_deudas_mostrar.rename(columns={
                'id': 'ID', 'deuda': 'Deuda', 'monto_inicial': 'Deuda Inicial',
                'Abonado Acumulado': 'Abonado Acumulado', 'monto_total': 'Restante Pendiente', 
                'cuota_mes': 'Cuota del Mes', 'estado': 'Estado'
            })
            
            df_deudas_mostrar['Deuda Inicial'] = df_deudas_mostrar['Deuda Inicial'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_deudas_mostrar['Abonado Acumulado'] = df_deudas_mostrar['Abonado Acumulado'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_deudas_mostrar['Restante Pendiente'] = df_deudas_mostrar['Restante Pendiente'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_deudas_mostrar['Cuota del Mes'] = df_deudas_mostrar['Cuota del Mes'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            
            st.dataframe(df_deudas_mostrar, use_container_width=True)

            # Log de Abonos específico para Deudas
            st.markdown("---")
            st.subheader("📜 Historial de Abonos a Deudas")
            try:
                df_log_deudas = cargar_datos("SELECT * FROM log_abonos WHERE tipo = 'Deuda' ORDER BY id DESC")
            except:
                df_log_deudas = pd.DataFrame()

            if not df_log_deudas.empty:
                df_ld_mostrar = df_log_deudas.rename(columns={
                    'id': 'ID', 'fecha': 'Fecha', 'referencia': 'Deuda', 'monto': 'Monto Abonado'
                })[['Fecha', 'Deuda', 'Monto Abonado']]
                df_ld_mostrar['Monto Abonado'] = df_ld_mostrar['Monto Abonado'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                st.dataframe(df_ld_mostrar, use_container_width=True)
            else:
                st.info("Aún no hay abonos registrados para deudas.")
        else:
            st.info("No hay deudas pendientes en este momento. ¡Buen trabajo!")
    else:
        st.info("No hay deudas registradas en el sistema.")

with pestana_metas:
    st.subheader("Seguimiento de Metas de Ahorro e Inversiones")
    
    with st.form("form_meta", clear_on_submit=True):
        st.markdown("**Registrar nueva meta de ahorro**")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            nombre_meta = st.text_input("Nombre de la Meta (Ej. Viaje a Europa)")
            estrategia_meta = st.text_input("Estrategia / Plataforma (Ej. Cajitas Nu)")
        with col_m2:
            monto_obj = st.number_input("Monto Objetivo (COP)", min_value=0, value=0, step=100000, format="%d")
            monto_act = st.number_input("Monto Actual Ahorrado (COP)", min_value=0, value=0, step=50000, format="%d")
            
        guardar_m = st.form_submit_button("Guardar Meta de Ahorro")
        if guardar_m and nombre_meta:
            estado_inicial_meta = 'Completada' if monto_act >= monto_obj and monto_obj > 0 else 'En curso'
            ejecutar_sql(
                "INSERT INTO metas_ahorro (nombre_meta, monto_objetivo, monto_actual, estrategia, estado) VALUES (?, ?, ?, ?, ?)",
                (nombre_meta, monto_obj, monto_act, estrategia_meta, estado_inicial_meta)
            )
            st.success(f"¡Meta '{nombre_meta}' registrada con éxito!")
            st.rerun()

    st.markdown("---")
    if not df_metas.empty:
        ver_completadas_m = st.checkbox("Mostrar metas completadas", key="chk_comp_m")
        df_metas_filtradas = df_metas if ver_completadas_m else df_metas[df_metas['estado'] != 'Completada']

        if not df_metas_filtradas.empty:
            st.markdown("### 📥 Registrar Ahorro / Sumar a Meta")
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
                    
                    ejecutar_sql("UPDATE metas_ahorro SET monto_actual = ?, estado = ? WHERE nombre_meta = ?", 
                                 (nuevo_ahorro, nuevo_estado_meta, meta_a_abonar))
                    
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    ejecutar_sql("INSERT INTO log_abonos (fecha, tipo, referencia, monto) VALUES (?, ?, ?, ?)",
                                 (fecha_hoy, 'Meta', meta_a_abonar, monto_ahorro_nuevo))
                    
                    st.success(f"¡Se sumaron $ {monto_ahorro_nuevo:,.0f} a la meta '{meta_a_abonar}'!".replace(",", "."))
                    st.rerun()

            st.markdown("---")
            st.subheader("📊 Progreso de Metas de Ahorro")
            df_metas_melted = df_metas_filtradas.melt(id_vars=['nombre_meta'], value_vars=['monto_objetivo', 'monto_actual'],
                                             var_name='Tipo', value_name='Monto')
            df_metas_melted['Tipo'] = df_metas_melted['Tipo'].replace({
                'monto_objetivo': 'Objetivo', 'monto_actual': 'Ahorrado Actual'
            })
            
            grafico_metas = alt.Chart(df_metas_melted).mark_bar().encode(
                x=alt.X('nombre_meta:N', title='Meta'),
                y=alt.Y('Monto:Q', axis=alt.Axis(format=',.0f', title='COP')),
                color='Tipo:N',
                xOffset='Tipo:N',
                tooltip=['nombre_meta', 'Tipo', alt.Tooltip('Monto:Q', format=',.0f')]
            ).properties(height=350)
            st.altair_chart(grafico_metas, use_container_width=True)

            st.markdown("### Detalle de Metas y Restante por Ahorrar")
            df_metas_mostrar = df_metas_filtradas.copy()
            # Calcular el restante para cumplir la meta
            df_metas_mostrar['Restante por Ahorrar'] = df_metas_mostrar['monto_objetivo'] - df_metas_mostrar['monto_actual']
            df_metas_mostrar['Restante por Ahorrar'] = df_metas_mostrar['Restante por Ahorrar'].apply(lambda x: max(0, x))
            
            df_metas_mostrar['Progreso'] = (df_metas_mostrar['monto_actual'] / df_metas_mostrar['monto_objetivo']) * 100
            df_metas_mostrar['Progreso_Str'] = df_metas_mostrar['Progreso'].apply(lambda x: f"{x:.2f}%")
            
            df_metas_mostrar = df_metas_mostrar.rename(columns={
                'id': 'ID', 'nombre_meta': 'Meta', 'monto_objetivo': 'Objetivo',
                'monto_actual': 'Ahorrado Actual', 'Restante por Ahorrar': 'Restante por Ahorrar', 
                'estrategia': 'Estrategia', 'Progreso_Str': '% Progreso', 'estado': 'Estado'
            })
            
            df_metas_mostrar['Objetivo'] = df_metas_mostrar['Objetivo'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_metas_mostrar['Ahorrado Actual'] = df_metas_mostrar['Ahorrado Actual'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_metas_mostrar['Restante por Ahorrar'] = df_metas_mostrar['Restante por Ahorrar'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            
            st.dataframe(df_metas_mostrar, use_container_width=True)

            # Log de Abonos específico para Metas
            st.markdown("---")
            st.subheader("📜 Historial de Ahorros a Metas")
            try:
                df_log_metas = cargar_datos("SELECT * FROM log_abonos WHERE tipo = 'Meta' ORDER BY id DESC")
            except:
                df_log_metas = pd.DataFrame()

            if not df_log_metas.empty:
                df_lm_mostrar = df_log_metas.rename(columns={
                    'id': 'ID', 'fecha': 'Fecha', 'referencia': 'Meta', 'monto': 'Monto Abonado'
                })[['Fecha', 'Meta', 'Monto Abonado']]
                df_lm_mostrar['Monto Abonado'] = df_lm_mostrar['Monto Abonado'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                st.dataframe(df_lm_mostrar, use_container_width=True)
            else:
                st.info("Aún no hay abonos registrados para metas.")
        else:
            st.info("No hay metas de ahorro en curso en este momento.")
    else:
        st.info("No hay metas de ahorro registradas.")

with pestana_inversiones:
    st.subheader("💎 Patrimonio Neto e Inversiones")
    
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
        st.metric(label="Deudas Totales Pendientes", value=f"$ {total_deudas_pendientes:,.0f}".replace(",", "."))

    st.markdown("---")

    # 2. Formulario para registrar o actualizar activos/inversiones
    with st.form("form_inversion", clear_on_submit=True):
        st.markdown("**Registrar o actualizar valor de un activo / inversión**")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            activo_input = st.text_input("Activo (Ej. S&P 500 VOO, TSMC)")
        with col_i2:
            monto_inv_input = st.number_input("Monto Actual Invertido (COP)", min_value=0, value=0, step=50000, format="%d")
            
        guardar_inv = st.form_submit_button("Guardar Inversión")
        if guardar_inv and activo_input:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            ejecutar_sql(
                "INSERT INTO inversiones (fecha, activo, monto_invertido) VALUES (?, ?, ?)",
                (fecha_hoy, activo_input, monto_inv_input)
            )
            st.success(f"¡Inversión en '{activo_input}' registrada exitosamente!")
            st.rerun()

    st.markdown("---")

    # 3. Visualización y Gráfico
    if not df_inversiones.empty:
        st.subheader("📊 Distribución de tu Portafolio de Inversión")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            df_inv_mostrar = df_inversiones.copy()
            df_inv_mostrar['monto_invertido'] = df_inv_mostrar['monto_invertido'].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
            df_inv_mostrar = df_inv_mostrar.rename(columns={
                'id': 'ID', 'fecha': 'Fecha Registro', 'activo': 'Activo', 'monto_invertido': 'Monto Invertido (COP)'
            })
            st.dataframe(df_inv_mostrar, use_container_width=True)
            
        with col_g2:
            grafico_inversiones = alt.Chart(df_inversiones).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="monto_invertido", type="quantitative"),
                color=alt.Color(field="activo", type="nominal"),
                tooltip=['activo', alt.Tooltip('monto_invertido:Q', format=',.0f')]
            ).properties(height=300)
            st.altair_chart(grafico_inversiones, use_container_width=True)
    else:
        st.info("Aún no tienes inversiones registradas. Usa el formulario de arriba para agregar tu primer activo (ej. VOO o TSMC).")

st.sidebar.title("Navegación")
st.sidebar.info(
    "Panel conectado a `finance_bot.db`. "
    "Logs independientes por pestaña y cálculo dinámico de montos restantes."
)