# 1. Configuración de página (primera línea)
st.set_page_config(...)

# 2. Otras importaciones
import pandas as pd
import plotly.express as px

# 3. Resto del código

import streamlit as st
# Configuración DEBE SER PRIMERO
st.set_page_config(page_title="Panel de Ventas", layout="wide")

import pandas as pd
import altair as alt  # Usando Altair en lugar de Plotly

# Resto de tu código...
# Reemplaza cualquier gráfico de Plotly con Altair:
def grafico_alternativo(df):
    chart = alt.Chart(df).mark_bar().encode(
        x='Producto:N',
        y='Ventas:Q'
    )
    st.altair_chart(chart, use_container_width=True)

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Consulta de Ventas", layout="wide", page_icon="📊")
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
            
        # Convertir tipos de datos - Formato día/mes/año
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df['COD_PROD'] = df['COD_PROD'].astype(str)
        df['VENDEDOR'] = df['VENDEDOR'].astype(str)
        df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce')
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
        
        # Verificar fechas inválidas
        if df['Fecha'].isnull().any():
            st.warning("⚠️ Algunas fechas no pudieron ser interpretadas (se marcaron como nulas)")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return None

# Subir archivo
uploaded_file = st.file_uploader("📁 Sube el archivo Excel", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Sidebar para filtros
        with st.sidebar:
            st.header("🔎 Filtros")
            
            # Búsqueda por código, descripción o cliente
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
            
            # Filtro por rango de fechas
            min_date = df['Fecha'].min().date() if not df['Fecha'].isnull().all() else pd.to_datetime('today').date()
            max_date = df['Fecha'].max().date() if not df['Fecha'].isnull().all() else pd.to_datetime('today').date()
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Desde", min_date)
            with col2:
                fecha_fin = st.date_input("Hasta", max_date)
            
            # Filtro por vendedor
            vendedores = sorted(df['VENDEDOR'].unique())
            vendedores_sel = st.multiselect("Vendedor(es)", vendedores)
            
            # Agrupación opcional
            group_by = st.selectbox("Agrupar por", ["Ninguno", "Vendedor", "Cliente", "Mes", "Año"])

        # Aplicar filtros
        if search_option == "Cliente":
            mask = (
                (df['CLIENTE'] == cliente_sel) &
                (df['Fecha'].dt.date >= fecha_inicio) &
                (df['Fecha'].dt.date <= fecha_fin)
            )
            titulo_resultados = f"Ventas para el cliente: {cliente_sel}"
        else:
            mask = (
                (df['COD_PROD'] == cod_input) &
                (df['Fecha'].dt.date >= fecha_inicio) &
                (df['Fecha'].dt.date <= fecha_fin)
            )
            producto = df[df['COD_PROD'] == cod_input]['Descripcion'].iloc[0]
            titulo_resultados = f"Ventas para: {cod_input} - {producto}"
            
        if vendedores_sel:
            mask &= df['VENDEDOR'].isin(vendedores_sel)
            
        resultado = df[mask].copy()
        
        if not resultado.empty:
            # SOLUCIÓN DEFINITIVA: Ordenar primero el DataFrame completo
            resultado = resultado.sort_values('Fecha')
            
            # Crear columna de fecha formateada para mostrar
            resultado['Fecha_formateada'] = resultado['Fecha'].dt.strftime('%d/%m/%Y')
            
            st.subheader(titulo_resultados)
            
            # Agrupación de datos
            if group_by != "Ninguno":
                if group_by == "Mes":
                    resultado['Grupo'] = resultado['Fecha'].dt.to_period('M').astype(str)
                elif group_by == "Año":
                    resultado['Grupo'] = resultado['Fecha'].dt.year.astype(str)
                elif group_by == "Vendedor":
                    resultado['Grupo'] = resultado['VENDEDOR']
                else:  # Cliente
                    resultado['Grupo'] = resultado['CLIENTE']
                
                grouped = resultado.groupby('Grupo').agg({
                    'Cantidad': 'sum',
                    'MONTO': 'sum',
                    'Documento': 'nunique'
                }).reset_index()
                grouped.rename(columns={'Documento': 'Transacciones'}, inplace=True)
                
                st.subheader(f"📊 Ventas agrupadas por {group_by.lower()}")
                st.dataframe(grouped)
                
                # Gráfico de barras para datos agrupados
                fig = px.bar(grouped, x='Grupo', y='MONTO', text='MONTO',
                            title=f"Ventas por {group_by.lower()}",
                            hover_data=['Cantidad', 'Transacciones'])
                fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar tabla con detalles - CORRECCIÓN DEFINITIVA
            st.subheader("📋 Detalle de transacciones")
            columnas_mostrar = [
                'CLIENTE', 'VENDEDOR', 'Fecha_formateada', 'Documento', 
                'Descripcion', 'Cantidad', 'MONTO'
            ]
            
            # DataFrame ya está ordenado por 'Fecha'
            st.dataframe(
                resultado[columnas_mostrar].rename(columns={
                    'Fecha_formateada': 'Fecha',
                    'MONTO': 'Monto'
                })
            )
            
            # Mostrar métricas
            total_cant = resultado['Cantidad'].sum()
            total_monto = resultado['MONTO'].sum()
            transacciones = resultado['Documento'].nunique()
            avg_price = total_monto / total_cant if total_cant > 0 else 0
            
            st.subheader("📊 Totales")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Unidades", f"{total_cant:,.0f}")
            col2.metric("Total Ventas", f"${total_monto:,.2f}")
            col3.metric("Precio Promedio", f"${avg_price:,.2f}")
            col4.metric("Transacciones", f"{transacciones:,.0f}")
            
            # Gráfico de serie temporal
            if len(resultado) > 1:
                fig = px.line(resultado, x='Fecha', y='MONTO', 
                             title='Evolución de Ventas por Fecha',
                             markers=True,
                             hover_data=['CLIENTE', 'VENDEDOR', 'Cantidad'])
                st.plotly_chart(fig, use_container_width=True)
            
            # Exportar datos
            st.subheader("💾 Exportar Resultados")
            export_format = st.radio("Formato de exportación:", ["Excel", "CSV"])
            
            # Preparar datos para exportación
            resultado_export = resultado.copy()
            resultado_export['Fecha'] = resultado_export['Fecha'].dt.strftime('%d/%m/%Y')
            
            if export_format == "Excel":
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    resultado_export.drop(columns=['Fecha_formateada']).to_excel(
                        writer, index=False, sheet_name='Detalle')
                    if group_by != "Ninguno":
                        grouped.to_excel(writer, index=False, sheet_name='Agrupado')
                st.download_button(
                    label="⬇️ Descargar Excel",
                    data=output.getvalue(),
                    file_name=f"reporte_ventas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.download_button(
                    label="⬇️ Descargar CSV",
                    data=resultado_export.drop(columns=['Fecha_formateada'])
                        .to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8'),
                    file_name=f"reporte_ventas.csv",
                    mime="text/csv"
                )
        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados")
