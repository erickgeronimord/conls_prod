# 1. Importar streamlit primero - ESENCIAL
import streamlit as st

# 2. Configuración de página - DEBE SER LO SIGUIENTE
st.set_page_config(
    page_title="Consulta de Ventas",
    layout="wide",
    page_icon="📊",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# Esta es una aplicación de análisis de ventas"
    }
)

# 3. Ahora el resto de importaciones
import pandas as pd
import plotly.express as px
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 4. Inicio de la aplicación
st.title("📊 Consulta de Ventas por Producto")

# Función para cargar datos con caché
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        
        # Validar columnas requeridas
        required_columns = ['CLIENTE', 'COD_PROD', 'Descripcion', 'Documento', 'Fecha', 
                          'Cantidad', 'VENDEDOR', 'MES', 'YEAR', 'MONTO']
        if not all(col in df.columns for col in required_columns):
            st.error("❌ El archivo no contiene las columnas requeridas")
            st.error(f"Columnas encontradas: {df.columns.tolist()}")
            st.error(f"Columnas esperadas: {required_columns}")
            return None
            
        # Convertir tipos de datos
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df['COD_PROD'] = df['COD_PROD'].astype(str)
        df['VENDEDOR'] = df['VENDEDOR'].astype(str)
        df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce')
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
        
        if df['Fecha'].isnull().any():
            st.warning("⚠️ Algunas fechas no pudieron ser interpretadas")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return None

# Interfaz de usuario
uploaded_file = st.file_uploader("📁 Sube el archivo Excel", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Sidebar para filtros
        with st.sidebar:
            st.header("🔎 Filtros")
            
            search_option = st.radio("Buscar por:", ["Código", "Descripción", "Cliente"])
            
            if search_option == "Código":
                codigos = sorted(df['COD_PROD'].unique())
                cod_input = st.selectbox("Seleccione código de producto", codigos)
            elif search_option == "Descripción":
                descripciones = sorted(df['Descripcion'].unique())
                desc_selected = st.selectbox("Seleccione descripción", descripciones)
                cod_input = df[df['Descripcion'] == desc_selected]['COD_PROD'].iloc[0]
            else:
                clientes = sorted(df['CLIENTE'].unique())
                cliente_sel = st.selectbox("Seleccione cliente", clientes)
                cod_input = None
            
            min_date = df['Fecha'].min().date() if not df['Fecha'].isnull().all() else pd.to_datetime('today').date()
            max_date = df['Fecha'].max().date() if not df['Fecha'].isnull().all() else pd.to_datetime('today').date()
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Desde", min_date)
            with col2:
                fecha_fin = st.date_input("Hasta", max_date)
            
            vendedores = sorted(df['VENDEDOR'].unique())
            vendedores_sel = st.multiselect("Vendedor(es)", vendedores)
            
            group_by = st.selectbox("Agrupar por", ["Ninguno", "Vendedor", "Cliente", "Mes", "Año"])

        # Aplicar filtros
        if search_option == "Cliente":
            mask = (
                (df['CLIENTE'] == cliente_sel) &
                (df['Fecha'].dt.date >= fecha_inicio) &
                (df['Fecha'].dt.date <= fecha_fin)
            )
            titulo = f"Ventas para el cliente: {cliente_sel}"
        else:
            mask = (
                (df['COD_PROD'] == cod_input) &
                (df['Fecha'].dt.date >= fecha_inicio) &
                (df['Fecha'].dt.date <= fecha_fin)
            )
            producto = df[df['COD_PROD'] == cod_input]['Descripcion'].iloc[0]
            titulo = f"Ventas para: {cod_input} - {producto}"
            
        if vendedores_sel:
            mask &= df['VENDEDOR'].isin(vendedores_sel)
            
        resultado = df[mask].copy().sort_values('Fecha')
        
        if not resultado.empty:
            resultado['Fecha_mostrar'] = resultado['Fecha'].dt.strftime('%d/%m/%Y')
            
            st.subheader(titulo)
            
            # [Resto del código de visualización...]
            # ... (mantener el mismo código de visualización de tablas, gráficos y exportación)

        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados")
