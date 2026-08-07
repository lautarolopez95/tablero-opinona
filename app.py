import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Tablero OPINONA", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# DICCIONARIO DE COLUMNAS (Mapeo exacto al Excel/Sheets)
# -----------------------------------------------------------------------------
COLS = {
    "FECHA": "FECHA",
    "LINEA": "Linea",
    "DESGLOSE": "Desglose 1",    # Para los gráficos del 100% y OPINONA
    "NIVEL_1": "Desc_Paro_1",    # Para el árbol de desgloses
    "NIVEL_2": "Desc_Paro_2",    
    "NIVEL_3": "Desc_Paro_3",
    "NIVEL_4": "Desc_Paro_4",
    "TIEMPO": "PROD + PAROS [Min]"
}

# -----------------------------------------------------------------------------
# LOS 6 TIEMPOS DE OPINONA (Colores para gráficos)
# -----------------------------------------------------------------------------
COLORS = {
    "PRODUCCION": "#459345",              # Verde
    "DETENCION PLANEADA": "#0078D7",      # Azul
    "PARADA MAYOR": "#D92121",            # Rojo
    "PARADA MENOR": "#F5A623",            # Amarillo/Naranja
    "PARADA EXTERNA": "#FF7F00",          # Naranja
    "PERDIDA DE VELOCIDAD": "#FF8C69"     # Durazno
}

# -----------------------------------------------------------------------------
# CARGA DE DATOS (Vía Enlace CSV de Google Sheets)
# -----------------------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2800/2800100.png", width=100)
st.sidebar.title("Configuración")

@st.cache_data(ttl=600)
def cargar_datos():
    try:
        url_csv = st.secrets["url_csv"]
    except:
        st.error("Falta configurar el enlace en los secretos. Revisa el Paso 3.")
        st.stop()
        
    df = pd.read_csv(url_csv)
    df.columns = df.columns.str.strip()
    
    columnas_esperadas = list(COLS.values())
    columnas_faltantes = [c for c in columnas_esperadas if c not in df.columns]
    
    if columnas_faltantes:
        raise ValueError(f"Faltan las siguientes columnas: {columnas_faltantes}")
    
    df[COLS["FECHA"]] = pd.to_datetime(df[COLS["FECHA"]], errors='coerce', format="%d/%m/%Y")
    df['AÑO'] = df[COLS["FECHA"]].dt.year
    df['MES'] = df[COLS["FECHA"]].dt.month
    
    # Función robusta para mapear Desglose 1 a las 6 categorías exactas
    # ignorando tildes, mayúsculas o espacios extra.
    def mapear_opinona(x):
        x = str(x).upper()
        if 'PRODUCCI' in x or x == '#': return 'PRODUCCION'
        if 'DETENCI' in x and 'PLANEADA' in x: return 'DETENCION PLANEADA'
        if 'MAYOR' in x: return 'PARADA MAYOR'
        if 'MENOR' in x: return 'PARADA MENOR'
        if 'PARADA' in x and 'EXTERNA' in x: return 'PARADA EXTERNA'
        if 'VELOCIDAD' in x: return 'PERDIDA DE VELOCIDAD'
        return x # Deja intacto NONA u otros para que se excluyan solos
        
    df['CATEGORIA_100'] = df[COLS["DESGLOSE"]].apply(mapear_opinona)
    
    # Limpieza básica para los niveles
    df[COLS["NIVEL_1"]] = df[COLS["NIVEL_1"]].astype(str).str.upper().str.strip()
    df[COLS["NIVEL_2"]] = df[COLS["NIVEL_2"]].astype(str).str.upper().str.strip()
    return df

try:
    with st.spinner("Descargando datos desde Google Sheets..."):
        df_raw = cargar_datos()
    st.sidebar.success("✅ Conectado a Google Sheets")
except Exception as e:
    st.sidebar.error("❌ Error de Conexión o Columnas.")
    st.error(f"⚠️ Error: {e}")
    st.stop()

# --- DICCIONARIOS DE MESES ---
MESES_MAP = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
MESES_ABBR = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}

# --- FILTROS GLOBALES ---
st.sidebar.markdown("### Filtros Globales")

min_date = df_raw[COLS["FECHA"]].min().date()
max_date = df_raw[COLS["FECHA"]].max().date()
rango_fechas = st.sidebar.date_input("Selecciona un periodo", [min_date, max_date], min_value=min_date, max_value=max_date)

años_nums = sorted(df_raw['AÑO'].dropna().unique().tolist())
años = ["Todos"] + [str(int(a)) for a in años_nums]

meses_nums = sorted(df_raw['MES'].dropna().unique().tolist())
meses = ["Todos"] + [MESES_MAP[m] for m in meses_nums]

año_sel = st.sidebar.selectbox("Año", años)
mes_sel = st.sidebar.selectbox("Mes", meses)

df = df_raw.copy()
if len(rango_fechas) == 2:
    df = df[(df[COLS["FECHA"]].dt.date >= rango_fechas[0]) & (df[COLS["FECHA"]].dt.date <= rango_fechas[1])]
if año_sel != "Todos":
    df = df[df['AÑO'] == int(año_sel)]
if mes_sel != "Todos":
    mes_num_seleccionado = list(MESES_MAP.keys())[list(MESES_MAP.values()).index(mes_sel)]
    df = df[df['MES'] == mes_num_seleccionado]

tab1, tab2 = st.tabs(["📊 OPINONA General", "🎯 Pérdida OPINONA por Equipo"])

# =========================================================================
# PÁGINA 1: OPINONA GENERAL
# =========================================================================
with tab1:
    st.title("OPINONA PLANTA")
    
    # 100% EXCLUSIVO: Solo estas 6 categorías, obtenidas de CATEGORIA_100
    CAT_100 = ["PRODUCCION", "DETENCION PLANEADA", "PARADA MAYOR", "PARADA MENOR", "PARADA EXTERNA", "PERDIDA DE VELOCIDAD"]
    df_100 = df[df['CATEGORIA_100'].isin(CAT_100)].copy()
    
    # 1. Gráfico por Línea
    df_linea_cat = df_100.groupby([COLS["LINEA"], 'CATEGORIA_100'])[COLS["TIEMPO"]].sum().reset_index()
    df_linea_cat['TOTAL_LINEA'] = df_linea_cat.groupby(COLS["LINEA"])[COLS["TIEMPO"]].transform('sum')
    df_linea_cat['PORCENTAJE'] = (df_linea_cat[COLS["TIEMPO"]] / df_linea_cat['TOTAL_LINEA']) * 100
    df_linea_cat['TEXTO'] = df_linea_cat['PORCENTAJE'].apply(lambda x: f"{x:.2f}%" if x >= 2.0 else "")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_planta = px.bar(df_linea_cat, x=COLS["LINEA"], y="PORCENTAJE", color='CATEGORIA_100',
                            color_discrete_map=COLORS, text="TEXTO",
                            hover_data={COLS["TIEMPO"]: True, "PORCENTAJE": False, "TOTAL_LINEA": False, "TEXTO": False},
                            title="OPINONA PLANTA POR LÍNEA")
        
        fig_planta.update_layout(yaxis_title="Porcentaje (%)", yaxis_ticksuffix=" %", height=750, legend_title="Tiempos OPINONA")
        fig_planta.update_traces(textposition='inside', insidetextfont=dict(size=16, family="Arial Black"), textangle=0)
        st.plotly_chart(fig_planta, use_container_width=True)
        
    # 2. Gráfico por Año
    with col2:
        df_año_cat = df_100.groupby(['AÑO', 'CATEGORIA_100'])[COLS["TIEMPO"]].sum().reset_index()
        df_año_cat['AÑO'] = df_año_cat['AÑO'].astype(int).astype(str)
        df_año_cat['TOTAL_AÑO'] = df_año_cat.groupby('AÑO')[COLS["TIEMPO"]].transform('sum')
        df_año_cat['PORCENTAJE'] = (df_año_cat[COLS["TIEMPO"]] / df_año_cat['TOTAL_AÑO']) * 100
        df_año_cat['TEXTO'] = df_año_cat['PORCENTAJE'].apply(lambda x: f"{x:.2f}%" if x >= 2.0 else "")
        
        fig_total = px.bar(df_año_cat, x='AÑO', y="PORCENTAJE", color='CATEGORIA_100',
                           color_discrete_map=COLORS, text="TEXTO",
                           hover_data={COLS["TIEMPO"]: True, "PORCENTAJE": False, "TOTAL_AÑO": False, "TEXTO": False},
                           title="OPINONA TOTAL PLANTA (ANUAL)")
                           
        fig_total.update_layout(yaxis_title="Porcentaje (%)", yaxis_ticksuffix=" %", height=750, legend_title="Tiempos OPINONA")
        fig_total.update_traces(textposition='inside', insidetextfont=dict(size=16, family="Arial Black"), textangle=0)
        st.plotly_chart(fig_total, use_container_width=True)

    st.markdown("---")
    st.subheader("Desglose de Paros (Filtros en Cascada)")
    st.info("👆 Haz clic en las barras de un gráfico para filtrar los datos de los siguientes gráficos. Puedes seleccionar múltiples barras manteniendo presionada la tecla Shift en tu teclado.")
    
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    
    # Filtrar Producción y Tiempo No Usado para los desgloses
    df_niveles = df[~df[COLS["NIVEL_1"]].str.contains('PRODUCCI|NO USADO|#', na=False, case=False)].copy()
    
    def plot_top_horizontal_interactive(df_temp, groupby_col, title, key):
        res = df_temp.groupby(groupby_col)[COLS["TIEMPO"]].sum().reset_index()
        res = res.sort_values(by=COLS["TIEMPO"], ascending=True).tail(10)
        fig = px.bar(res, x=COLS["TIEMPO"], y=groupby_col, orientation='h', title=title, text_auto=".0f", color_discrete_sequence=["#5cb85c"])
        fig.update_layout(yaxis_title=None, xaxis_title="Minutos", clickmode="event+select")
        
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=key)
        
        selected = []
        if event and 'selection' in event and 'points' in event['selection']:
            selected = [p['y'] for p in event['selection']['points']]
        return selected

    with c1:
        sel_n1 = plot_top_horizontal_interactive(df_niveles, COLS["NIVEL_1"], "PARO NIVEL 1 (MIN)", key="plot_n1")
    
    df_n2 = df_niveles[df_niveles[COLS["NIVEL_1"]].isin(sel_n1)] if sel_n1 else df_niveles
    with c2:
        sel_n2 = plot_top_horizontal_interactive(df_n2, COLS["NIVEL_2"], "PARO NIVEL 2: MÁQUINAS (MIN)", key="plot_n2")
        
    df_n3 = df_n2[df_n2[COLS["NIVEL_2"]].isin(sel_n2)] if sel_n2 else df_n2
    with c3:
        sel_n3 = plot_top_horizontal_interactive(df_n3, COLS["NIVEL_3"], "PARO NIVEL 3 (MIN)", key="plot_n3")
        
    df_n4 = df_n3[df_n3[COLS["NIVEL_3"]].isin(sel_n3)] if sel_n3 else df_n3
    with c4:
        plot_top_horizontal_interactive(df_n4, COLS["NIVEL_4"], "PARO NIVEL 4 (MIN)", key="plot_n4")

# =========================================================================
# PÁGINA 2: PÉRDIDA OPINONA
# =========================================================================
with tab2:
    st.title("Pérdida de OPINONA")
    
    # El denominador FIJO para el periodo seleccionado (independiente de línea/equipo)
    # Se calcula sobre las 6 categorías principales (df_100)
    TIEMPO_TOTAL_PLANTA = df_100[COLS["TIEMPO"]].sum()
    
    st.markdown("### Filtros de Numerador (Línea y Equipo)")
    l1, l2 = st.columns(2)
    lineas_disp = sorted(df_100[COLS["LINEA"]].dropna().unique().tolist())
    lineas_sel = l1.multiselect("Filtrar por Línea", options=lineas_disp, default=[])
    
    # Filtrar equipos según líneas seleccionadas (si hay)
    df_filtro_linea = df_100 if not lineas_sel else df_100[df_100[COLS["LINEA"]].isin(lineas_sel)]
    equipos_disp = sorted(df_filtro_linea[COLS["NIVEL_2"]].dropna().unique().tolist())
    equipos_sel = l2.multiselect("Filtrar por Equipo", options=equipos_disp, default=[])
    
    st.info(f"**Denominador (Tiempo Total Planta Periodo Seleccionado):** {TIEMPO_TOTAL_PLANTA:,.0f} min")
    
    # Numerador: Filtrado por línea y equipo
    df_num = df_100.copy()
    if lineas_sel:
        df_num = df_num[df_num[COLS["LINEA"]].isin(lineas_sel)]
    if equipos_sel:
        df_num = df_num[df_num[COLS["NIVEL_2"]].isin(equipos_sel)]
        
    # --- 1. Gráficos por Equipo (Paradas Mayores y Menores) ---
    st.subheader("Pérdida de OPINONA por Paradas (Equipos)")
    df_equipos_pmayor = df_num[df_num['CATEGORIA_100'] == "PARADA MAYOR"]
    df_equipos_pmenor = df_num[df_num['CATEGORIA_100'] == "PARADA MENOR"]
    
    def plot_perdida_equipo(df_temp, color_bar, title):
        res = df_temp.groupby(COLS["NIVEL_2"])[COLS["TIEMPO"]].sum().reset_index()
        # Cálculo de porcentaje usando el denominador global del periodo
        res['PORCENTAJE'] = (res[COLS["TIEMPO"]] / TIEMPO_TOTAL_PLANTA) * 100
        res = res[res['PORCENTAJE'] > 0]
        res = res.sort_values(by='PORCENTAJE', ascending=True).tail(15) # Top 15 para no saturar
        
        fig = px.bar(res, x='PORCENTAJE', y=COLS["NIVEL_2"], orientation='h', title=title, text_auto=".2f", color_discrete_sequence=[color_bar])
        fig.update_layout(yaxis_title=None, xaxis_title="% Pérdida OPINONA", xaxis_ticksuffix=" %", height=500)
        st.plotly_chart(fig, use_container_width=True)
        
    col_may, col_men = st.columns(2)
    with col_may:
        plot_perdida_equipo(df_equipos_pmayor, COLORS["PARADA MAYOR"], "Pérdida por Paradas Mayores (Top 15 Equipos)")
    with col_men:
        plot_perdida_equipo(df_equipos_pmenor, COLORS["PARADA MENOR"], "Pérdida por Paradas Menores (Top 15 Equipos)")
        
    st.markdown("---")
    
    # --- 2. Gráfico de Columnas por Mes ---
    st.subheader("Evolución Mensual de Pérdidas de OPINONA")
    
    # Filtrar solo PM, pm, y PV
    cats_mensuales = ["PARADA MAYOR", "PARADA MENOR", "PERDIDA DE VELOCIDAD"]
    df_mensual_num = df_num[df_num['CATEGORIA_100'].isin(cats_mensuales)].copy()
    
    # Denominador mensual (basado en df_100, SIN filtro de equipo/línea, para reflejar % a nivel planta)
    df_den_mes = df_100.groupby(['AÑO', 'MES'])[COLS["TIEMPO"]].sum().reset_index(name='DEN_MES')
    
    # Numerador mensual
    df_num_mes = df_mensual_num.groupby(['AÑO', 'MES', 'CATEGORIA_100'])[COLS["TIEMPO"]].sum().reset_index(name='NUM_MES')
    
    # Unir y calcular %
    if not df_num_mes.empty and not df_den_mes.empty:
        df_plot_mes = pd.merge(df_num_mes, df_den_mes, on=['AÑO', 'MES'])
        df_plot_mes['PORCENTAJE'] = (df_plot_mes['NUM_MES'] / df_plot_mes['DEN_MES']) * 100
        
        df_plot_mes['MES_AÑO_NUM'] = df_plot_mes['AÑO'] * 100 + df_plot_mes['MES']
        df_plot_mes['MES_AÑO_STR'] = df_plot_mes['MES'].map(MESES_ABBR) + " " + df_plot_mes['AÑO'].astype(int).astype(str)
        df_plot_mes = df_plot_mes.sort_values('MES_AÑO_NUM')
        
        fig_col_mes = px.bar(df_plot_mes, x='MES_AÑO_STR', y='PORCENTAJE', color='CATEGORIA_100',
                             color_discrete_map=COLORS, text_auto=".2f",
                             title="% Pérdidas OPINONA a Nivel Planta por Mes")
        fig_col_mes.update_layout(xaxis_title="Mes", yaxis_title="% Pérdida", yaxis_ticksuffix=" %",
                                  xaxis={'categoryorder':'array', 'categoryarray':df_plot_mes['MES_AÑO_STR'].unique()})
        # Mostrar el texto por dentro
        fig_col_mes.update_traces(textposition='inside', insidetextfont=dict(size=14, family="Arial Black"), textangle=0)
        st.plotly_chart(fig_col_mes, use_container_width=True)
        
        # --- 3. Gráfico de Líneas por Mes ---
        st.markdown("---")
        st.subheader("Tendencia de Paradas Mayores y Menores")
        df_linea_mes = df_plot_mes[df_plot_mes['CATEGORIA_100'].isin(["PARADA MAYOR", "PARADA MENOR"])]
        
        if not df_linea_mes.empty:
            fig_line_mes = px.line(df_linea_mes, x='MES_AÑO_STR', y='PORCENTAJE', color='CATEGORIA_100',
                                   color_discrete_map=COLORS, markers=True, text='PORCENTAJE',
                                   title="Tendencia Mensual de Paradas Mayores y Menores (%)")
            fig_line_mes.update_traces(textposition='top center', texttemplate='%{text:.2f}%', textfont=dict(size=12))
            fig_line_mes.update_layout(xaxis_title="Mes", yaxis_title="% Pérdida", yaxis_ticksuffix=" %",
                                       xaxis={'categoryorder':'array', 'categoryarray':df_plot_mes['MES_AÑO_STR'].unique()})
            
            # Ajustar el margen superior para que los textos de la línea no se corten
            fig_line_mes.update_layout(margin=dict(t=50))
            st.plotly_chart(fig_line_mes, use_container_width=True)
        else:
            st.warning("No hay datos de Parada Mayor o Menor para la selección actual.")
    else:
        st.warning("No hay datos suficientes para mostrar la evolución mensual.")
