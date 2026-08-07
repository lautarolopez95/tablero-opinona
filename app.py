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
    "FECHA": "FECHA REAL",
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
    # Intenta leer el enlace CSV desde los secretos, si no existe, muestra un error amigable
    try:
        url_csv = st.secrets["url_csv"]
    except:
        st.error("Falta configurar el enlace en los secretos. Revisa el Paso 3.")
        st.stop()
        
    # Leer el CSV directamente con Pandas (evita el Error 400 de la API de Google)
    df = pd.read_csv(url_csv, usecols=list(COLS.values()))
    
    # Limpieza básica
    df[COLS["FECHA"]] = pd.to_datetime(df[COLS["FECHA"]], errors='coerce')
    df['AÑO'] = df[COLS["FECHA"]].dt.year
    df['MES'] = df[COLS["FECHA"]].dt.month
    
    # Estandarizar los nombres de las categorías a MAYÚSCULAS sin tildes para evitar errores
    df[COLS["CATEGORIA"]] = df[COLS["CATEGORIA"]].astype(str).str.upper().str.strip()
    df[COLS["CATEGORIA"]] = df[COLS["CATEGORIA"]].str.replace('Ó', 'O', regex=False).str.replace('É', 'E', regex=False).str.replace('Í', 'I', regex=False)
    
    df[COLS["EQUIPO"]] = df[COLS["EQUIPO"]].astype(str).str.upper().str.strip()
    return df

try:
    with st.spinner("Descargando datos desde Google Sheets..."):
        df_raw = cargar_datos()
    st.sidebar.success("✅ Conectado a Google Sheets")
except Exception as e:
    st.sidebar.error("❌ Error de Conexión.")
    st.error(f"Error al leer los datos. Asegúrate de que los nombres de las columnas en el Sheets coincidan con el código. Detalle: {e}")
    st.stop()

# --- FILTROS GLOBALES ---
st.sidebar.markdown("### Filtros Globales (Afectan a toda la planta)")

# Filtro Rango de Fechas
min_date = df_raw[COLS["FECHA"]].min().date()
max_date = df_raw[COLS["FECHA"]].max().date()
rango_fechas = st.sidebar.date_input("Selecciona un periodo", [min_date, max_date], min_value=min_date, max_value=max_date)

# Filtro Año y Mes
años = ["Todos"] + sorted(df_raw['AÑO'].dropna().unique().tolist())
meses = ["Todos"] + sorted(df_raw['MES'].dropna().unique().tolist())

año_sel = st.sidebar.selectbox("Año", años)
mes_sel = st.sidebar.selectbox("Mes", meses)

# APLICAR FILTROS GLOBALES
df = df_raw.copy()
if len(rango_fechas) == 2:
    df = df[(df[COLS["FECHA"]].dt.date >= rango_fechas[0]) & (df[COLS["FECHA"]].dt.date <= rango_fechas[1])]
if año_sel != "Todos":
    df = df[df['AÑO'] == año_sel]
if mes_sel != "Todos":
    df = df[df['MES'] == mes_sel]

# --- TABS PARA NAVEGACIÓN (Páginas) ---
tab1, tab2 = st.tabs(["📊 OPINONA General", "🎯 Pérdida OPINONA por Equipo"])

# =========================================================================
# PÁGINA 1: OPINONA GENERAL
# =========================================================================
with tab1:
    st.title("OPINONA PLANTA")
    
    # Agrupación por Línea y Categoría
    df_linea_cat = df.groupby([COLS["LINEA"], COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    
    # Gráfico OPINONA PLANTA (100% Apilado)
    col1, col2 = st.columns(2)
    with col1:
        fig_planta = px.bar(df_linea_cat, x=COLS["LINEA"], y=COLS["TIEMPO"], color=COLS["CATEGORIA"],
                            color_discrete_map=COLORS, barmode="relative", text_auto=".1%",
                            title="OPINONA PLANTA POR LÍNEA")
        # Convertir a 100%
        fig_planta.update_layout(barnorm="percent", yaxis_title="Porcentaje (%)")
        st.plotly_chart(fig_planta, use_container_width=True)
        
    with col2:
        # Agrupación por Año y Categoría para "OPINONA TOTAL PLANTA"
        df_año_cat = df.groupby(['AÑO', COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
        fig_total = px.bar(df_año_cat, x='AÑO', y=COLS["TIEMPO"], color=COLS["CATEGORIA"],
                           color_discrete_map=COLORS, barmode="relative", text_auto=".1%",
                           title="OPINONA TOTAL PLANTA (ANUAL)")
        fig_total.update_layout(barnorm="percent", yaxis_title="Porcentaje (%)")
        st.plotly_chart(fig_total, use_container_width=True)

    st.markdown("---")
    st.subheader("Desglose de Paros (Top Acumuladores)")
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    
    # Función auxiliar para top horizontales
    def plot_top_horizontal(df_temp, groupby_col, title):
        res = df_temp.groupby(groupby_col)[COLS["TIEMPO"]].sum().reset_index()
        res = res.sort_values(by=COLS["TIEMPO"], ascending=True).tail(10) # Top 10
        fig = px.bar(res, x=COLS["TIEMPO"], y=groupby_col, orientation='h', title=title, text_auto=".0f", color_discrete_sequence=["#5cb85c"])
        fig.update_layout(yaxis_title=None, xaxis_title="Minutos")
        return fig

    with c1: st.plotly_chart(plot_top_horizontal(df, COLS["CATEGORIA"], "PARO NIVEL 1 (MIN)"), use_container_width=True)
    with c2: st.plotly_chart(plot_top_horizontal(df, COLS["EQUIPO"], "PARO NIVEL 2: MAQUINAS (MIN)"), use_container_width=True)
    with c3: st.plotly_chart(plot_top_horizontal(df, COLS["NIVEL_3"], "PARO NIVEL 3 (MIN)"), use_container_width=True)
    with c4: st.plotly_chart(plot_top_horizontal(df, COLS["NIVEL_4"], "PARO NIVEL 4 (MIN)"), use_container_width=True)

# =========================================================================
# PÁGINA 2: PÉRDIDA OPINONA POR EQUIPO (La Magia Matemática)
# =========================================================================
with tab2:
    st.title("Desgloses de Pérdida OPINONA por Paros (Equipos)")
    
    # Filtros específicos para esta vista (SOLO AFECTAN AL NUMERADOR)
    st.markdown("### Selecciona el Filtro de Numerador")
    l1, l2 = st.columns(2)
    lineas_disp = ["Todas"] + sorted(df[COLS["LINEA"]].dropna().unique().tolist())
    linea_filtro = l1.selectbox("Filtrar por Línea", lineas_disp)
    
    # MATEMÁTICA L.O.D (Level of Detail)
    # 1. Denominador (Fijo al rango de fechas global seleccionado en el sidebar)
    TIEMPO_TOTAL_PLANTA = df[COLS["TIEMPO"]].sum()
    
    # 2. Numerador (Afectado por la Línea seleccionada aquí)
    df_numerador = df.copy()
    if linea_filtro != "Todas":
        df_numerador = df_numerador[df_numerador[COLS["LINEA"]] == linea_filtro]
        
    st.info(f"**Denominador (Tiempo Total Planta Filtrada por Fechas):** {TIEMPO_TOTAL_PLANTA:,.0f} min")

    # Preparar data para Paradas Menores y Mayores por equipo
    df_equipos = df_numerador.groupby([COLS["EQUIPO"], COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    
    # Separar en mayores y menores
    df_mayores = df_equipos[df_equipos[COLS["CATEGORIA"]].str.contains("MAYOR", na=False)].copy()
    df_menores = df_equipos[df_equipos[COLS["CATEGORIA"]].str.contains("MENOR", na=False)].copy()
    
    # 3. Calcular % de Pérdida Real
    df_mayores['%_Perdida'] = (df_mayores[COLS["TIEMPO"]] / TIEMPO_TOTAL_PLANTA) * 100
    df_menores['%_Perdida'] = (df_menores[COLS["TIEMPO"]] / TIEMPO_TOTAL_PLANTA) * 100
    
    # Graficar Top Equipos
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

    # Gráfico Histórico de Líneas (Mayores vs Menores)
    st.markdown("---")
    # Para el histórico, necesitamos recalcular el denominador por MES (no el global)
    df_mensual = df_numerador.groupby(['AÑO', 'MES', COLS["CATEGORIA"]])[COLS["TIEMPO"]].sum().reset_index()
    # Denominador mensual
    df_total_mensual = df.groupby(['AÑO', 'MES'])[COLS["TIEMPO"]].sum().reset_index().rename(columns={COLS["TIEMPO"]: "TOTAL_MES"})
    
    df_hist = pd.merge(df_mensual, df_total_mensual, on=['AÑO', 'MES'])
    df_hist['%_Perdida'] = (df_hist[COLS["TIEMPO"]] / df_hist['TOTAL_MES']) * 100
    df_hist['PERIODO'] = df_hist['AÑO'].astype(str) + "-" + df_hist['MES'].astype(str).str.zfill(2)
    
    # Filtrar solo Mayores y Menores
    df_hist_filtrado = df_hist[df_hist[COLS["CATEGORIA"]].str.contains("MAYOR|MENOR", regex=True)]
    
    fig_linea = px.line(df_hist_filtrado, x='PERIODO', y='%_Perdida', color=COLS["CATEGORIA"],
                        title="TENDENCIA: % PÉRDIDA OPINONA PAROS MENORES VS MAYORES", markers=True)
    fig_linea.update_layout(yaxis_ticksuffix=" %")
    st.plotly_chart(fig_linea, use_container_width=True)
