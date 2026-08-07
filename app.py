import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Tablero OPINONA", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1, h2, h3 {color: #1b4f3e;}
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DICCIONARIO DE COLUMNAS (Mapeo exacto al Excel/Sheets)
# -----------------------------------------------------------------------------
COLS = {
    "FECHA": "FECHA",
    "LINEA": "Linea",
    "CATEGORIA": "Desc_Paro_1",  # Categoría principal de los 6 tiempos
    "EQUIPO": "Desc_Paro_2",     # Equipo afectado
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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2800/2800100.png", width=100) # Logo placeholder
st.sidebar.title("Configuración")

# Para máxima estabilidad, usaremos el enlace de "Publicar en la web" en formato CSV
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
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
        raise ValueError(f"Faltan las siguientes columnas: {columnas_faltantes}. \nColumnas que SI encontró en tu archivo: {list(df.columns)}")
    
    df[COLS["FECHA"]] = pd.to_datetime(df[COLS["FECHA"]], errors='coerce')
    df['AÑO'] = df[COLS["FECHA"]].dt.year
    df['MES'] = df[COLS["FECHA"]].dt.month
    
    df[COLS["CATEGORIA"]] = df[COLS["CATEGORIA"]].astype(str).str.upper().str.strip()
    df[COLS["CATEGORIA"]] = df[COLS["CATEGORIA"]].str.replace('Ó', 'O', regex=False).str.replace('É', 'E', regex=False).str.replace('Í', 'I', regex=False)
    # Reemplazar el hashtag por PRODUCCION
    df[COLS["CATEGORIA"]] = df[COLS["CATEGORIA"]].replace("#", "PRODUCCION")
    
    df[COLS["EQUIPO"]] = df[COLS["EQUIPO"]].astype(str).str.upper().str.strip()
    return df

try:
    with st.spinner("Descargando datos desde Google Sheets..."):
        df_raw = cargar_datos()
    st.sidebar.success("✅ Conectado a Google Sheets")
except Exception as e:
    st.sidebar.error("❌ Error de Conexión o Columnas.")
    st.error(f"⚠️ Error: {e}")
    st.info("💡 CONSEJO: Revisa que `COLS` coincida exactamente.")
    st.stop()

# --- DICCIONARIOS DE MESES ---
MESES_MAP = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
MESES_ABBR = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}

# --- FILTROS GLOBALES ---
st.sidebar.markdown("### Filtros Globales (Afectan a toda la planta)")

min_date = df_raw[COLS["FECHA"]].min().date()
max_date = df_raw[COLS["FECHA"]].max().date()
rango_fechas = st.sidebar.date_input("Selecciona un periodo", [min_date, max_date], min_value=min_date, max_value=max_date)

# Años sin decimales
años_nums = sorted(df_raw['AÑO'].dropna().unique().tolist())
años = ["Todos"] + [str(int(a)) for a in años_nums]

# Meses como nombres
meses_nums = sorted(df_raw['MES'].dropna().unique().tolist())
meses = ["Todos"] + [MESES_MAP[m] for m in meses_nums]

año_sel = st.sidebar.selectbox("Año", años)
mes_sel = st.sidebar.selectbox("Mes", meses)

# APLICAR FILTROS GLOBALES
df = df_raw.copy()
if len(rango_fechas) == 2:
    df = df[(df[COLS["FECHA"]].dt.date >= rango_fechas[0]) & (df[COLS["FECHA"]].dt.date <= rango_fechas[1])]
if año_sel != "Todos":
    df = df[df['AÑO'] == int(año_sel)]
if mes_sel != "Todos":
    mes_num_seleccionado = list(MESES_MAP.keys())[list(MESES_MAP.values()).index(mes_sel)]
    df = df[df['MES'] == mes_num_seleccionado]

# --- TABS PARA NAVEGACIÓN (Páginas) ---
tab1, tab2 = st.tabs(["📊 OPINONA General", "🎯 Pérdida OPINONA por Equipo"])

# =========================================================================
# PÁGINA 1: OPINONA GENERAL
# =========================================================================
with tab1:
    st.title("OPINONA PLANTA")
    
    # 100% EXCLUSIVO: Solo estas 6 categorías
    CAT_100 = ["PRODUCCION", "DETENCION PLANEADA", "PARADA MAYOR", "PARADA MENOR", "PARADA EXTERNA", "PERDIDA DE VELOCIDAD"]
    df_100 = df[df[COLS["CATEGORIA"]].isin(CAT_100)].copy()
    
    # 1. Gráfico por Línea
    df_linea_cat = df_100.groupby([COLS["LINEA"], COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    # Calcular Porcentaje real matemáticamente
    df_linea_cat['TOTAL_LINEA'] = df_linea_cat.groupby(COLS["LINEA"])[COLS["TIEMPO"]].transform('sum')
    df_linea_cat['PORCENTAJE'] = (df_linea_cat[COLS["TIEMPO"]] / df_linea_cat['TOTAL_LINEA']) * 100
    
    col1, col2 = st.columns(2)
    with col1:
        fig_planta = px.bar(df_linea_cat, x=COLS["LINEA"], y="PORCENTAJE", color=COLS["CATEGORIA"],
                            color_discrete_map=COLORS, text_auto=".2f",
                            hover_data={COLS["TIEMPO"]: True, "PORCENTAJE": False, "TOTAL_LINEA": False},
                            title="OPINONA PLANTA POR LÍNEA")
        fig_planta.update_layout(yaxis_title="Porcentaje (%)", yaxis_ticksuffix=" %")
        fig_planta.update_traces(texttemplate='%{y:.2f}%') # Mostrar % en el texto
        st.plotly_chart(fig_planta, use_container_width=True)
        
    # 2. Gráfico por Año
    with col2:
        df_año_cat = df_100.groupby(['AÑO', COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
        # Formatear el año para el gráfico también
        df_año_cat['AÑO'] = df_año_cat['AÑO'].astype(int).astype(str)
        # Calcular Porcentaje real matemáticamente
        df_año_cat['TOTAL_AÑO'] = df_año_cat.groupby('AÑO')[COLS["TIEMPO"]].transform('sum')
        df_año_cat['PORCENTAJE'] = (df_año_cat[COLS["TIEMPO"]] / df_año_cat['TOTAL_AÑO']) * 100
        
        fig_total = px.bar(df_año_cat, x='AÑO', y="PORCENTAJE", color=COLS["CATEGORIA"],
                           color_discrete_map=COLORS, text_auto=".2f",
                           hover_data={COLS["TIEMPO"]: True, "PORCENTAJE": False, "TOTAL_AÑO": False},
                           title="OPINONA TOTAL PLANTA (ANUAL)")
        fig_total.update_layout(yaxis_title="Porcentaje (%)", yaxis_ticksuffix=" %")
        fig_total.update_traces(texttemplate='%{y:.2f}%') # Mostrar % en el texto
        st.plotly_chart(fig_total, use_container_width=True)

    st.markdown("---")
    st.subheader("Desglose de Paros (Filtros en Cascada)")
    st.info("👆 Haz clic en las barras de un gráfico para filtrar los datos de los siguientes gráficos. Puedes seleccionar múltiples barras manteniendo presionada la tecla Shift en tu teclado.")
    
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    
    def plot_top_horizontal_interactive(df_temp, groupby_col, title, key):
        res = df_temp.groupby(groupby_col)[COLS["TIEMPO"]].sum().reset_index()
        res = res.sort_values(by=COLS["TIEMPO"], ascending=True).tail(10)
        fig = px.bar(res, x=COLS["TIEMPO"], y=groupby_col, orientation='h', title=title, text_auto=".0f", color_discrete_sequence=["#5cb85c"])
        fig.update_layout(yaxis_title=None, xaxis_title="Minutos", clickmode="event+select")
        
        # Activar el evento on_select (quitamos selection_mode="multi" que causa el error)
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=key)
        
        # Extraer las selecciones del usuario
        selected = []
        if event and 'selection' in event and 'points' in event['selection']:
            selected = [p['y'] for p in event['selection']['points']]
        return selected

    # NIVEL 1
    with c1: 
        sel_n1 = plot_top_horizontal_interactive(df, COLS["CATEGORIA"], "PARO NIVEL 1 (MIN)", key="plot_n1")
    
    # Filtrar Nivel 2
    df_n2 = df[df[COLS["CATEGORIA"]].isin(sel_n1)] if sel_n1 else df
    with c2: 
        sel_n2 = plot_top_horizontal_interactive(df_n2, COLS["EQUIPO"], "PARO NIVEL 2: MAQUINAS (MIN)", key="plot_n2")

    # Filtrar Nivel 3
    df_n3 = df_n2[df_n2[COLS["EQUIPO"]].isin(sel_n2)] if sel_n2 else df_n2
    with c3: 
        sel_n3 = plot_top_horizontal_interactive(df_n3, COLS["NIVEL_3"], "PARO NIVEL 3 (MIN)", key="plot_n3")

    # Filtrar Nivel 4
    df_n4 = df_n3[df_n3[COLS["NIVEL_3"]].isin(sel_n3)] if sel_n3 else df_n3
    with c4: 
        _ = plot_top_horizontal_interactive(df_n4, COLS["NIVEL_4"], "PARO NIVEL 4 (MIN)", key="plot_n4")

# =========================================================================
# PÁGINA 2: PÉRDIDA OPINONA POR EQUIPO
# =========================================================================
with tab2:
    st.title("Desgloses de Pérdida OPINONA por Paros (Equipos)")
    
    st.markdown("### Selecciona el Filtro de Numerador")
    l1, l2 = st.columns(2)
    lineas_disp = ["Todas"] + sorted(df[COLS["LINEA"]].dropna().unique().tolist())
    linea_filtro = l1.selectbox("Filtrar por Línea", lineas_disp)
    
    TIEMPO_TOTAL_PLANTA = df[COLS["TIEMPO"]].sum()
    
    df_numerador = df.copy()
    if linea_filtro != "Todas":
        df_numerador = df_numerador[df_numerador[COLS["LINEA"]] == linea_filtro]
        
    st.info(f"**Denominador (Tiempo Total Planta Filtrada por Fechas):** {TIEMPO_TOTAL_PLANTA:,.0f} min")

    df_equipos = df_numerador.groupby([COLS["EQUIPO"], COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    
    df_mayores = df_equipos[df_equipos[COLS["CATEGORIA"]].str.contains("MAYOR", na=False)].copy()
    df_menores = df_equipos[df_equipos[COLS["CATEGORIA"]].str.contains("MENOR", na=False)].copy()
    
    df_mayores['%_Perdida'] = (df_mayores[COLS["TIEMPO"]] / TIEMPO_TOTAL_PLANTA) * 100
    df_menores['%_Perdida'] = (df_menores[COLS["TIEMPO"]] / TIEMPO_TOTAL_PLANTA) * 100
    
    c_maj, c_min = st.columns(2)
    with c_min:
        res_min = df_menores.sort_values(by='%_Perdida', ascending=True).tail(10)
        fig_min = px.bar(res_min, x='%_Perdida', y=COLS["EQUIPO"], orientation='h', 
                         title="% PÉRDIDA DE OPINONA POR PARADAS MENORES", text_auto=".2f", color_discrete_sequence=["#5cb85c"])
        fig_min.update_layout(xaxis_ticksuffix=" %")
        st.plotly_chart(fig_min, use_container_width=True)

    with c_maj:
        res_maj = df_mayores.sort_values(by='%_Perdida', ascending=True).tail(10)
        fig_maj = px.bar(res_maj, x='%_Perdida', y=COLS["EQUIPO"], orientation='h', 
                         title="% PÉRDIDA DE OPINONA POR PARADAS MAYORES", text_auto=".2f", color_discrete_sequence=["#5cb85c"])
        fig_maj.update_layout(xaxis_ticksuffix=" %")
        st.plotly_chart(fig_maj, use_container_width=True)

    st.markdown("---")
    
    df_mensual = df_numerador.groupby(['AÑO', 'MES', COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    df_total_mensual = df.groupby(['AÑO', 'MES'])[COLS["TIEMPO"]].sum().reset_index().rename(columns={COLS["TIEMPO"]: "TOTAL_MES"})
    
    df_hist = pd.merge(df_mensual, df_total_mensual, on=['AÑO', 'MES'])
    df_hist['%_Perdida'] = (df_hist[COLS["TIEMPO"]] / df_hist['TOTAL_MES']) * 100
    
    # Ordenar cronológicamente y formatear a "Ene 2024"
    df_hist = df_hist.sort_values(['AÑO', 'MES'])
    df_hist['PERIODO'] = df_hist['MES'].map(MESES_ABBR) + " " + df_hist['AÑO'].astype(int).astype(str)
    
    df_hist_filtrado = df_hist[df_hist[COLS["CATEGORIA"]].str.contains("MAYOR|MENOR", regex=True)]
    
    fig_linea = px.line(df_hist_filtrado, x='PERIODO', y='%_Perdida', color=COLS["CATEGORIA"],
                        title="TENDENCIA: % PÉRDIDA OPINONA PAROS MENORES VS MAYORES", markers=True)
    fig_linea.update_layout(yaxis_ticksuffix=" %")
    # Forzar el orden del eje X para que respete la cronología y no el orden alfabético
    fig_linea.update_xaxes(categoryorder='array', categoryarray=df_hist['PERIODO'].unique())
    
    st.plotly_chart(fig_linea, use_container_width=True)
