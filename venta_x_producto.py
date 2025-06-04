# 1. IMPORTACIONES
import streamlit as st
from datetime import datetime, timedelta
import hashlib
import sqlite3
import os
import pandas as pd
import plotly.express as px
from io import BytesIO
import xlsxwriter
import time
import numpy as np

# 2. CONFIGURACIÓN INICIAL
# Configuración de rutas y base de datos
script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
db_path = os.path.join(script_dir, 'auth.db')

# Configuración de página (se establecerá después de la autenticación)

# 3. FUNCIONES DE BASE DE DATOS Y AUTENTICACIÓN
def init_auth_db():
    """Inicializa la base de datos de autenticación"""
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                name TEXT,
                role TEXT,
                last_login TEXT
            )
        ''')
        
        # Insertar usuario admin inicial si no existe
        c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
            c.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                ('admin', admin_pass, 'Administrador', 'admin', None)
            )
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar la base de datos: {str(e)}")
        return False

def validate_user(username, password):
    """Valida las credenciales del usuario"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT name, role, password FROM users WHERE username = ?",
            (username,)
        )
        result = c.fetchone()
        conn.close()
        
        if result and result[2] == hashlib.sha256(password.encode()).hexdigest():
            return {
                'name': result[0],
                'role': result[1],
                'authenticated': True
            }
        return None
    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")
        return None

def update_last_login(username):
    """Actualiza la fecha del último login"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error al actualizar último login: {str(e)}")

# 4. FUNCIONES PARA CARGAR DATOS
@st.cache_data(ttl=3600)
def load_data_from_drive():
    try:
        file_id = "104573iwthllgXVuY6C7N4q6xBrjwMlu7"
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx&t={timestamp}"
        
        df = pd.read_excel(url, engine='openpyxl')
        
        required_columns = ['CLIENTE', 'COD_PROD', 'Descripcion', 'Documento', 'Fecha', 
                          'Cantidad', 'VENDEDOR', 'MES', 'YEAR', 'MONTO']
        if not all(col in df.columns for col in required_columns):
            st.error("❌ El archivo no contiene las columnas requeridas")
            return None
            
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

@st.cache_data(ttl=3600)
def load_metas():
    try:
        file_id = "1XCTQWTBOZoEyhIOu5flg5gT2ZTT51SOr"
        url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
        
        df_metas = pd.read_excel(url, engine='openpyxl')
        
        # Limpieza y preparación de datos
        df_metas['CANTIDAD'] = df_metas['CANTIDAD'].astype(str).str.replace(',', '').astype(float)
        df_metas['MONTO'] = df_metas['MONTO'].astype(str).str.replace(',', '').astype(float)
        
        return df_metas
        
    except Exception as e:
        st.error(f"Error al cargar las metas: {str(e)}")
        return None

# 5. INTERFAZ DE LOGIN
def login_section():
    """Muestra la sección de login"""
    st.title("🔒 Acceso al Sistema de Ventas")
    
    with st.form("login_form"):
        username = st.text_input("Nombre de usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar sesión")
        
        if submitted:
            user = validate_user(username, password)
            if user:
                update_last_login(username)
                st.session_state.update(user)
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

# 6. VERIFICAR AUTENTICACIÓN
if not init_auth_db():
    st.error("No se pudo inicializar el sistema de autenticación")
    st.stop()

if 'authenticated' not in st.session_state:
    login_section()
    st.stop()

# 7. CONFIGURACIÓN DE PÁGINA PARA USUARIOS AUTENTICADOS
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

# 8. BARRA DE ESTADO DEL USUARIO
def user_status_bar():
    """Muestra la barra de estado del usuario"""
    cols = st.columns([8, 1, 1])
    with cols[0]:
        st.write(f"👤 Usuario: {st.session_state.get('name', '')} ({st.session_state.get('role', '')})")
    with cols[1]:
        if st.button("🔄 Recargar"):
            st.rerun()
    with cols[2]:
        if st.button("🚪 Salir"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

user_status_bar()

# 9. DEFINICIÓN DE PESTAÑAS
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Consulta de Ventas", 
    "🎯 Metas por Vendedor", 
    "📈 Comparación Ventas vs Metas",
    "🔧 Administración", 
    "📚 Manual de Usuario"
])

# 10. PESTAÑA 1: CONSULTA DE VENTAS
with tab1:
    st.title("📊 Consulta de Ventas por Producto")
    
    df = load_data_from_drive()
    
    if df is not None:
        # Extraer mes y año para filtros
        df['Mes'] = df['Fecha'].dt.month
        df['Año'] = df['Fecha'].dt.year
        
        with st.sidebar:
            st.header("🔎 Filtros")
            
            # Filtro por mes
            meses_disponibles = sorted(df['Mes'].unique())
            mes_sel = st.selectbox("Mes", ['Todos'] + meses_disponibles)
            
            # Filtro por año
            años_disponibles = sorted(df['Año'].unique())
            año_sel = st.selectbox("Año", ['Todos'] + años_disponibles)
            
            # Aplicar filtros de fecha
            if mes_sel != 'Todos':
                df = df[df['Mes'] == mes_sel]
            if año_sel != 'Todos':
                df = df[df['Año'] == año_sel]
            
            # Resto de filtros
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

        # Aplicar filtros adicionales
        if search_option == "Cliente":
            mask = (
                (df['CLIENTE'] == cliente_sel) &
                (df['Fecha'].dt.date >= fecha_inicio) &
                (df['Fecha'].dt.date <= fecha_fin)
            )  # <-- Aquí se cerró el paréntesis que faltaba
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
                
        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados")
    else:
        st.error("No se pudieron cargar los datos. Por favor intente más tarde o verifique la conexión.")

# 11. PESTAÑA 2: METAS POR VENDEDOR
with tab2:
    st.title("🎯 Metas por Vendedor")
    
    df_metas = load_metas()
    
    if df_metas is not None:
        with st.sidebar:
            st.header("Filtros de Metas")
            vendedores_metas = sorted(df_metas['VDI'].unique())
            vendedor_meta_sel = st.selectbox("Seleccionar Vendedor", ['Todos'] + vendedores_metas)
            
            categorias = sorted(df_metas['CATEGORIA'].unique())
            categoria_sel = st.selectbox("Filtrar por Categoría", ['Todas'] + categorias)
            
            nivel_agregacion = st.radio("Nivel de detalle", ["Categoría", "Subcategoría", "Producto"])
        
        # Aplicar filtros
        if vendedor_meta_sel != 'Todos':
            df_filtrado = df_metas[df_metas['VDI'] == vendedor_meta_sel].copy()
        else:
            df_filtrado = df_metas.copy()
            
        if categoria_sel != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['CATEGORIA'] == categoria_sel]
        
        # Agrupar según nivel seleccionado
        if nivel_agregacion == "Categoría":
            df_agrupado = df_filtrado.groupby(['VDI', 'CATEGORIA']).agg({
                'CANTIDAD': 'sum',
                'MONTO': 'sum'
            }).reset_index()
            df_agrupado['ITEM'] = df_agrupado['CATEGORIA']
        elif nivel_agregacion == "Subcategoría":
            df_agrupado = df_filtrado.groupby(['VDI', 'CATEGORIA', 'SUBCATEGORIA']).agg({
                'CANTIDAD': 'sum',
                'MONTO': 'sum'
            }).reset_index()
            df_agrupado['ITEM'] = df_agrupado['SUBCATEGORIA']
        else:
            df_agrupado = df_filtrado.copy()
            df_agrupado['ITEM'] = df_agrupado['nombre']
        
        # Mostrar resultados
        st.subheader(f"Metas {'por ' + vendedor_meta_sel if vendedor_meta_sel != 'Todos' else 'Totales'}")
        
        total_cantidad = df_agrupado['CANTIDAD'].sum()
        total_monto = df_agrupado['MONTO'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Total Cantidad Meta", f"{total_cantidad:,.0f}")
        col2.metric("Total Monto Meta", f"${total_monto:,.2f}")
        
        st.dataframe(df_agrupado.sort_values('MONTO', ascending=False))
        
        if len(df_agrupado) > 0:
            fig = px.bar(
                df_agrupado,
                x='ITEM',
                y='MONTO',
                color='VDI',
                title=f"Metas por {nivel_agregacion.lower()}",
                labels={'MONTO': 'Monto Meta', 'ITEM': nivel_agregacion},
                hover_data=['CANTIDAD']
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("No se pudieron cargar los datos de metas")

# 12. PESTAÑA 3: COMPARACIÓN VENTAS VS METAS
with tab3:
    st.title("📈 Comparación Ventas vs Metas")
    
    df_ventas = load_data_from_drive()
    df_metas = load_metas()
    
    if df_ventas is not None and df_metas is not None:
        # Agregar filtros por mes
        with st.sidebar:
            st.header("Filtros de Comparación")
            
            # Filtro por mes
            df_ventas['Mes'] = df_ventas['Fecha'].dt.month
            meses = sorted(df_ventas['Mes'].unique())
            mes_sel = st.selectbox("Mes para Comparar", meses)
            
            # Filtro por vendedor
            vendedores_comparar = sorted(df_metas['VDI'].unique())
            vendedor_comparar_sel = st.selectbox("Vendedor a Comparar", vendedores_comparar)
            
            mostrar_solo_faltantes = st.checkbox("Mostrar solo productos con meta no alcanzada")
        
        # Filtrar ventas por mes seleccionado
        df_ventas_filtrado = df_ventas[df_ventas['Mes'] == mes_sel]
        
        # Preparar datos de ventas para comparación
        df_ventas_agrupado = df_ventas_filtrado.groupby(['VENDEDOR', 'Descripcion']).agg({
            'Cantidad': 'sum',
            'MONTO': 'sum'
        }).reset_index()
        
        # Unir ambos datasets
        df_comparacion = pd.merge(
            df_metas,
            df_ventas_agrupado,
            left_on=['VDI', 'nombre'],
            right_on=['VENDEDOR', 'Descripcion'],
            how='left'
        )
        
        # Limpiar y calcular diferencias
        df_comparacion['Cantidad'] = df_comparacion['Cantidad'].fillna(0)
        df_comparacion['MONTO_y'] = df_comparacion['MONTO_y'].fillna(0)
        
        df_comparacion['Diferencia_Cantidad'] = df_comparacion['CANTIDAD'] - df_comparacion['Cantidad']
        df_comparacion['Diferencia_Monto'] = df_comparacion['MONTO_x'] - df_comparacion['MONTO_y']
        
        df_comparacion['%_Avance_Cantidad'] = (df_comparacion['Cantidad'] / df_comparacion['CANTIDAD']) * 100
        df_comparacion['%_Avance_Monto'] = (df_comparacion['MONTO_y'] / df_comparacion['MONTO_x']) * 100
        
        # Filtrar por vendedor seleccionado
        df_comparacion_filtrado = df_comparacion[df_comparacion['VDI'] == vendedor_comparar_sel]
        
        if mostrar_solo_faltantes:
            df_comparacion_filtrado = df_comparacion_filtrado[
                (df_comparacion_filtrado['Diferencia_Cantidad'] > 0) | 
                (df_comparacion_filtrado['Diferencia_Monto'] > 0)
            ]
        
        # Mostrar métricas resumen
        st.subheader(f"Comparación para: {vendedor_comparar_sel} - Mes {mes_sel}")
        
        total_meta_cant = df_comparacion_filtrado['CANTIDAD'].sum()
        total_venta_cant = df_comparacion_filtrado['Cantidad'].sum()
        total_meta_monto = df_comparacion_filtrado['MONTO_x'].sum()
        total_venta_monto = df_comparacion_filtrado['MONTO_y'].sum()
        
        avance_cant = (total_venta_cant / total_meta_cant) * 100 if total_meta_cant > 0 else 0
        avance_monto = (total_venta_monto / total_meta_monto) * 100 if total_meta_monto > 0 else 0
        
        col1, col2 = st.columns(2)
        col1.metric("Avance Cantidad", f"{avance_cant:.1f}%", 
                   f"{total_venta_cant:,.0f} de {total_meta_cant:,.0f}")
        col2.metric("Avance Monto", f"{avance_monto:.1f}%", 
                   f"${total_venta_monto:,.2f} de ${total_meta_monto:,.2f}")
        
        # Calcular proyección de fecha para alcanzar meta (si aplica)
        dias_transcurridos = (datetime.now() - datetime(datetime.now().year, mes_sel, 1)).days
        if dias_transcurridos > 0 and total_venta_monto > 0:
            dias_restantes = 30 - dias_transcurridos  # Asumiendo meses de 30 días
            monto_restante = total_meta_monto - total_venta_monto
            velocidad_necesaria = monto_restante / dias_restantes if dias_restantes > 0 else 0
            
            col3, col4 = st.columns(2)
            col3.metric("Velocidad Actual", f"${(total_venta_monto/dias_transcurridos):,.2f}/día")
            col4.metric("Velocidad Necesaria", f"${velocidad_necesaria:,.2f}/día")
        
        # Mostrar tabla comparativa
        st.subheader("Detalle por Producto")
        
        columnas_mostrar = [
            'CATEGORIA', 'SUBCATEGORIA', 'nombre', 
            'CANTIDAD', 'Cantidad', 'Diferencia_Cantidad', '%_Avance_Cantidad',
            'MONTO_x', 'MONTO_y', 'Diferencia_Monto', '%_Avance_Monto'
        ]
        
        df_mostrar = df_comparacion_filtrado[columnas_mostrar].rename(columns={
            'CANTIDAD': 'Meta_Cantidad',
            'Cantidad': 'Venta_Cantidad',
            'MONTO_x': 'Meta_Monto',
            'MONTO_y': 'Venta_Monto',
            'nombre': 'Producto'
        })
        
        st.dataframe(df_mostrar.style.format({
            'Meta_Cantidad': '{:,.0f}',
            'Venta_Cantidad': '{:,.0f}',
            'Diferencia_Cantidad': '{:,.0f}',
            '%_Avance_Cantidad': '{:.1f}%',
            'Meta_Monto': '${:,.2f}',
            'Venta_Monto': '${:,.2f}',
            'Diferencia_Monto': '${:,.2f}',
            '%_Avance_Monto': '{:.1f}%'
        }))
        
        # Gráficos comparativos
        st.subheader("Análisis Visual")
        
        fig1 = px.bar(
            df_comparacion_filtrado.nlargest(10, 'Diferencia_Monto'),
            x='nombre',
            y=['MONTO_x', 'MONTO_y'],
            title=f'Top 10 Productos con Mayor Diferencia (Mes {mes_sel})',
            labels={'value': 'Monto', 'variable': 'Tipo', 'nombre': 'Producto'},
            barmode='group'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.pie(
            df_comparacion_filtrado,
            names='CATEGORIA',
            values='Diferencia_Monto',
            title='Diferencia por Categoría',
            hole=0.3
        )
        st.plotly_chart(fig2, use_container_width=True)
        
    else:
        st.error("No se pudieron cargar los datos necesarios para la comparación")

# 13. PESTAÑA 4: ADMINISTRACIÓN
with tab4:
    if st.session_state.get('role') == 'admin':
        st.title("🔧 Panel de Administración")
        
        try:
            conn = sqlite3.connect(db_path)
            users_df = pd.read_sql("SELECT username, name, role, last_login FROM users", conn)
            
            # Gestión de usuarios
            st.subheader("Usuarios Registrados")
            st.dataframe(users_df)
            
            # Formulario para agregar/actualizar usuarios
            with st.expander("Agregar/Editar Usuario", expanded=True):
                with st.form("user_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_username = st.text_input("Nombre de usuario")
                        new_name = st.text_input("Nombre completo")
                    with col2:
                        new_role = st.selectbox("Rol", ["user", "admin"])
                        new_password = st.text_input("Contraseña", type="password")
                    
                    submitted = st.form_submit_button("Guardar Usuario")
                    
                    if submitted:
                        if not new_username or not new_password:
                            st.error("Usuario y contraseña son requeridos")
                        else:
                            try:
                                hashed_pass = hashlib.sha256(new_password.encode()).hexdigest()
                                conn.execute(
                                    "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)",
                                    (new_username, hashed_pass, new_name, new_role, None)
                                )
                                conn.commit()
                                st.success("Usuario guardado correctamente")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
            
            # Eliminar usuarios
            with st.expander("Eliminar Usuario", expanded=False):
                with st.form("delete_form"):
                    del_user = st.selectbox(
                        "Seleccionar usuario a eliminar",
                        users_df['username'].tolist()
                    )
                    submitted_delete = st.form_submit_button("Eliminar Usuario")
                    if submitted_delete and del_user != "admin":
                        conn.execute("DELETE FROM users WHERE username = ?", (del_user,))
                        conn.commit()
                        st.success(f"Usuario {del_user} eliminado")
                        st.rerun()
            
        except Exception as e:
            st.error(f"Error en panel de administración: {str(e)}")
        finally:
            conn.close()
    else:
        st.warning("⛔ Solo usuarios administradores pueden acceder a esta sección")

# 14. PESTAÑA 5: MANUAL DE USUARIO
with tab5:
    st.title("📚 Manual de Usuario")
    
    st.header("🔍 Instrucciones Básicas")
    with st.expander("🔹 Cómo usar la aplicación", expanded=True):
        st.markdown("""
        1. **Inicie sesión** con sus credenciales asignadas
        2. Navegue entre las diferentes pestañas usando el menú superior
        3. Use los filtros en el panel izquierdo para ajustar los resultados
        4. Los datos se actualizan automáticamente desde Google Drive
        """)
    
    st.header("📊 Pestañas Disponibles")
    with st.expander("🔹 Consulta de Ventas"):
        st.markdown("""
        - Visualice las ventas por producto, cliente o vendedor
        - Filtre por fechas, meses o años específicos
        - Exporte los resultados a Excel o CSV
        """)
    
    with st.expander("🔹 Metas por Vendedor"):
        st.markdown("""
        - Consulte las metas asignadas a cada vendedor
        - Vea el desglose por categoría, subcategoría o producto
        - Filtre por vendedor específico o vea todos
        """)
    
    with st.expander("🔹 Comparación Ventas vs Metas"):
        st.markdown("""
        - Compare el desempeño real con las metas establecidas
        - Vea el porcentaje de avance por producto
        - Identifique oportunidades de mejora
        """)
    
    with st.expander("🔹 Panel de Administración"):
        st.markdown("""
        - Gestiona usuarios y permisos (solo para administradores)
        - Agregue, edite o elimine usuarios del sistema
        """)
    
    st.markdown("---")
    st.info("ℹ️ Para más ayuda, contacte al administrador: hmorel@bptrack.net")
