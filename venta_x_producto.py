# 1. Importar streamlit primero
import streamlit as st
from datetime import datetime

# 2. Configuración de página
st.set_page_config(
    page_title="Consulta de Ventas",
    layout="wide",
    page_icon="📊",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# Aplicación de análisis de ventas"
    }
)

# 3. Otras importaciones con manejo de errores
try:
    import pandas as pd
    import plotly.express as px
    from io import BytesIO
    import xlsxwriter
    import time
    
except ImportError as e:
    st.error(f"❌ Error: Faltan dependencias requeridas. Por favor instale: {str(e)}")
    st.stop()  # Detiene la ejecución si faltan paquetes

# Función para cargar datos desde Google Drive (archivo público) con caché temporal
@st.cache_data(ttl=3600)  # Actualiza cada hora (3600 segundos)
def load_data_from_drive():
    try:
        # ID del archivo en Google Drive (extraído de la URL)
        file_id = "104573iwthllgXVuY6C7N4q6xBrjwMlu7"
        
        # URL de exportación directa como Excel con timestamp para evitar caché
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx&t={timestamp}"
        
        # Leer el archivo Excel directamente
        df = pd.read_excel(url, engine='openpyxl')
        
        required_columns = ['CLIENTE', 'COD_PROD', 'Descripcion', 'Documento', 'Fecha', 
                          'Cantidad', 'VENDEDOR', 'MES', 'YEAR', 'MONTO']
        if not all(col in df.columns for col in required_columns):
            st.error("❌ El archivo no contiene las columnas requeridas")
            return None
            
        # Conversión de tipos
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df['COD_PROD'] = df['COD_PROD'].astype(str)
        df['VENDEDOR'] = df['VENDEDOR'].astype(str)
        df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce')
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
        
        if df['Fecha'].isnull().any():
            st.warning("⚠️ Algunas fechas no pudieron ser interpretadas")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo desde Google Drive: {str(e)}")
        return None

# 4. Crear pestañas
tab1, tab2 = st.tabs(["📊 Consulta de Ventas", "📚 Manual de Usuario"])

with tab1:  # Pestaña principal de la aplicación
    st.title("📊 Consulta de Ventas por Producto")

    # Barra superior con controles de actualización
    col1, col2, col3 = st.columns([6, 1, 1])
    with col1:
        st.write("")  # Espacio para alinear
    with col2:
        if st.button("🔄 Recargar Datos", help="Actualizar datos desde Google Drive"):
            st.cache_data.clear()  # Limpiar caché para forzar recarga
    with col3:
        last_update = st.empty()  # Espacio reservado para mostrar última actualización

    # Cargar datos con manejo de estado
    status = st.empty()
    status.info("⏳ Cargando datos desde Google Drive...")
    df = load_data_from_drive()
    status.empty()

    if df is not None:
        # Mostrar última actualización
        last_update.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
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
                
                # Gráfico de barras
                if not grouped.empty:
                    fig = px.bar(
                        grouped,
                        x='Grupo',
                        y='MONTO',
                        text='MONTO',
                        title=f"Ventas por {group_by.lower()}",
                        labels={'MONTO': 'Monto Total', 'Grupo': group_by},
                        hover_data=['Cantidad', 'Transacciones']
                    )
                    fig.update_traces(
                        texttemplate='%{text:,.2f}',
                        textposition='outside',
                        marker_color='#4CAF50'
                    )
                    fig.update_layout(
                        xaxis_title=group_by,
                        yaxis_title="Monto Total",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # Detalle de transacciones
            st.subheader("📋 Detalle de transacciones")
            columnas_mostrar = [
                'CLIENTE', 'VENDEDOR', 'Fecha_mostrar', 'Documento', 
                'Descripcion', 'Cantidad', 'MONTO'
            ]
            st.dataframe(
                resultado[columnas_mostrar].rename(columns={
                    'Fecha_mostrar': 'Fecha',
                    'MONTO': 'Monto'
                })
            )
            
            # Métricas
            total_cant = resultado['Cantidad'].sum()
            total_monto = resultado['MONTO'].sum()
            transacciones = resultado['Documento'].nunique()
            avg_price = total_monto / total_cant if total_cant > 0 else 0
            ticket_promedio = total_monto / transacciones if transacciones > 0 else 0
            
            st.subheader("📊 Totales")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            col1.metric("Total Unidades", f"{total_cant:,.0f}")
            col2.metric("Total Ventas", f"${total_monto:,.2f}")
            col3.metric("Precio Promedio", f"${avg_price:,.2f}")
            col4.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")
            col5.metric("Transacciones", f"{transacciones:,.0f}")
            
            # Gráfico de línea
            if len(resultado) > 1:
                fig = px.line(
                    resultado,
                    x='Fecha',
                    y='MONTO',
                    title='Evolución de Ventas por Fecha',
                    markers=True,
                    labels={'MONTO': 'Monto', 'Fecha': 'Fecha'},
                    hover_data=['CLIENTE', 'VENDEDOR', 'Cantidad']
                )
                fig.update_layout(
                    xaxis_title="Fecha",
                    yaxis_title="Monto",
                    height=500
                )
                fig.update_traces(line_color='#FF4B4B', marker_color='#FF4B4B')
                st.plotly_chart(fig, use_container_width=True)
            
            # Exportación
            st.subheader("💾 Exportar Resultados")
            export_format = st.radio("Formato de exportación:", ["Excel", "CSV"])
            
            try:
                if export_format == "Excel":
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        resultado.drop(columns=['Fecha_mostrar']).to_excel(
                            writer, index=False, sheet_name='Detalle')
                        if group_by != "Ninguno":
                            grouped.to_excel(writer, index=False, sheet_name='Agrupado')
                    st.download_button(
                        label="⬇️ Descargar Excel",
                        data=output.getvalue(),
                        file_name="reporte_ventas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.download_button(
                        label="⬇️ Descargar CSV",
                        data=resultado.drop(columns=['Fecha_mostrar'])
                            .to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8'),
                        file_name="reporte_ventas.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"Error al exportar: {str(e)}")
                st.info("ℹ️ Si el error persiste, intente exportar como CSV o instale xlsxwriter manualmente")
                
        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados")
    else:
        st.error("No se pudieron cargar los datos. Por favor intente más tarde o verifique la conexión.")

with tab2:  # Pestaña del manual de usuario
    st.title("📚 Manual de Usuario")
    
    st.header("🔍 Instrucciones Básicas")
    with st.expander("🔹 Cómo usar la aplicación", expanded=True):
        st.markdown("""
        1. **La aplicación carga automáticamente** los datos al iniciar desde Google Drive
        2. Usa el botón 🔄 en la esquina superior derecha para **forzar una actualización** cuando necesites datos frescos
        3. Los datos se actualizan automáticamente **cada hora**
        4. Siempre podrás ver cuándo fue la **última actualización** en la parte superior
        """)
    
    st.header("🎛️ Panel de Filtros")
    with st.expander("🔹 Cómo filtrar los datos"):
        st.markdown("""
        - **Buscar por**: Selecciona si quieres filtrar por código de producto, descripción o cliente
        - **Rango de fechas**: Define el período que deseas analizar
        - **Vendedor(es)**: Selecciona uno o múltiples vendedores (opcional)
        - **Agrupar por**: Elige cómo deseas agrupar los resultados para los resúmenes
        """)
    
    st.header("📊 Visualización de Datos")
    with st.expander("🔹 Cómo interpretar los resultados"):
        st.markdown("""
        - **Ventas agrupadas**: Tabla resumen con los totales según tu agrupación seleccionada
        - **Gráfico de barras**: Muestra visualmente los montos por grupo
        - **Detalle de transacciones**: Listado completo de todas las ventas que cumplen con los filtros
        - **Métricas clave**: Total unidades, ventas, precios promedios y más
        - **Gráfico de evolución**: Muestra cómo han variado las ventas en el tiempo
        """)
    
    st.header("💾 Exportación de Resultados")
    with st.expander("🔹 Cómo exportar los datos"):
        st.markdown("""
        - Selecciona el formato de exportación (Excel o CSV)
        - Haz clic en el botón de descarga
        - El archivo se guardará en tu dispositivo con todos los datos filtrados
        - **Excel** incluye dos hojas: Detalle y Datos agrupados
        """)
    
    st.header("❓ Preguntas Frecuentes")
    with st.expander("🔹 ¿Qué hago si no veo datos?"):
        st.markdown("""
        - Verifica que los filtros no sean demasiado restrictivos
        - Prueba ampliar el rango de fechas
        - Haz clic en el botón 🔄 para recargar los datos
        - Si el problema persiste, contacta al administrador
        """)
    
    with st.expander("🔹 ¿Cómo sé que estoy viendo datos actualizados?"):
        st.markdown("""
        - La aplicación muestra la **hora de última actualización** en la parte superior
        - Los datos se actualizan automáticamente cada hora
        - Puedes forzar una actualización manual con el botón 🔄
        """)
    
    st.markdown("---")
    st.info("ℹ️ Para más ayuda, contacta al equipo de soporte: soporte@empresa.com")

# Nota: Para ejecutar esta aplicación usa el comando: streamlit run nombre_del_archivo.py
