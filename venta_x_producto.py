# 1. Configuración de página DEBE SER PRIMERO (incluso antes de imports)
import streamlit as st
st.set_page_config(
    page_title="Consulta de Ventas por Producto",
    layout="wide",
    page_icon="📊",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# Esta es una aplicación de análisis de ventas"
    }
)

# 2. Luego los demás imports
import pandas as pd
from io import BytesIO
import tempfile
import os

# 3. Función principal
def main():
    st.title("📊 Consulta de Ventas por Producto")
    
    uploaded_file = st.file_uploader("📁 Sube el archivo Excel", type=["xlsx"])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip().str.upper()

            # Verificar columnas obligatorias
            required_columns = {'FECHA', 'COD_PROD', 'CANTIDAD', 'MONTO'}
            missing = required_columns - set(df.columns)
            
            if missing:
                st.error(f"Faltan columnas requeridas: {', '.join(missing)}")
                st.stop()

            # Procesamiento de fechas
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], errors='coerce')

            # Sidebar para filtros
            with st.sidebar:
                st.header("🔎 Filtros")

                # Selector de código de producto
                codigos = sorted(df['COD_PROD'].unique())
                cod_input = st.selectbox("Código de producto", codigos)

                # Filtro por rango de fechas
                min_date = df['FECHA_DT'].min().date()
                max_date = df['FECHA_DT'].max().date()
                start_date = st.date_input("Desde", min_date)
                end_date = st.date_input("Hasta", max_date)

                # Filtro por vendedor (si existe)
                if 'VENDEDOR' in df.columns:
                    vendedores = ["Todos"] + sorted(df['VENDEDOR'].unique())
                    vendedor_sel = st.selectbox("Vendedor", vendedores)
                else:
                    vendedor_sel = "Todos"

            # Aplicar filtros
            filtered = df[
                (df['COD_PROD'].astype(str) == str(cod_input)) &
                (df['FECHA_DT'].dt.date >= start_date) &
                (df['FECHA_DT'].dt.date <= end_date)
            ]

            if vendedor_sel != "Todos" and 'VENDEDOR' in df.columns:
                filtered = filtered[filtered['VENDEDOR'].astype(str) == str(vendedor_sel)]

            if not filtered.empty:
                filtered['FECHA'] = filtered['FECHA_DT'].dt.strftime('%d/%m/%Y')
                
                # Columnas a mostrar
                cols_to_show = ['VENDEDOR', 'FECHA', 'COD_PROD', 'DESCRIPCION', 'CANTIDAD', 'MONTO']
                cols_to_show = [col for col in cols_to_show if col in filtered.columns]
                
                st.success(f"📊 {len(filtered)} registros encontrados")
                st.dataframe(filtered[cols_to_show].sort_values('FECHA_DT'))

                # Totales
                total_qty = filtered['CANTIDAD'].sum()
                total_amount = filtered['MONTO'].sum()
                
                st.markdown(f"**Total unidades:** {total_qty:,}")
                st.markdown(f"**Total vendido:** ${total_amount:,.2f}")

                # Botón de descarga
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered.to_excel(writer, index=False)
                
                st.download_button(
                    label="⬇️ Descargar resultados",
                    data=output.getvalue(),
                    file_name=f"ventas_{cod_input}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("No se encontraron resultados")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")

if __name__ == "__main__":
    main()
