import streamlit as st
# Configuración DEBE SER LA PRIMERA LÍNEA de Streamlit
st.set_page_config(page_title="Panel de Ventas", layout="wide", page_icon="📊")

# Importaciones después de la configuración
import pandas as pd
import altair as alt
from io import BytesIO
from fpdf import FPDF
import tempfile
import os

# Función principal
def main():
    st.title("📊 Panel de Ventas")
    
    # Carga de archivo
    archivo_subido = st.file_uploader("📤 Sube tu archivo Excel", type=["xlsx"])

    if archivo_subido is not None:
        try:
            datos = pd.read_excel(archivo_subido)

            # Normalización de columnas
            datos.columns = datos.columns.str.strip().str.upper()

            # Verificar columnas mínimas
            columnas_requeridas = {'FECHA', 'MONTO', 'CANTIDAD'}
            faltantes = columnas_requeridas - set(datos.columns)
            
            if faltantes:
                st.error(f"Error: Faltan columnas requeridas: {', '.join(faltantes)}")
                st.stop()

            # Procesamiento de fechas
            datos['FECHA_DT'] = pd.to_datetime(datos['FECHA'], errors='coerce')
            datos['AÑO'] = datos['FECHA_DT'].dt.year
            datos['MES_NUM'] = datos['FECHA_DT'].dt.month
            datos['MES'] = datos['FECHA_DT'].dt.strftime('%b')

            # Pestañas de navegación
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Ventas por Fecha", 
                "👥 Análisis por Cliente", 
                "📊 Métricas Mensuales",
                "🔍 Consulta por Producto"
            ])

            with tab1:
                st.subheader("📈 Evolución de Ventas")
                ventas_por_fecha = datos.groupby('FECHA_DT')['MONTO'].sum().reset_index()

                grafico = alt.Chart(ventas_por_fecha).mark_line(point=True).encode(
                    x=alt.X('FECHA_DT:T', title='Fecha'),
                    y=alt.Y('MONTO:Q', title='Monto ($)'),
                    tooltip=['FECHA_DT:T', 'MONTO']
                ).properties(width=700, height=400)

                st.altair_chart(grafico, use_container_width=True)

            with tab2:
                st.subheader("👥 Desempeño por Cliente")
                if 'CLIENTE' in datos.columns:
                    ventas_cliente = datos.groupby('CLIENTE').agg({
                        'MONTO': 'sum',
                        'CANTIDAD': 'sum'
                    }).reset_index().sort_values(by='MONTO', ascending=False)

                    st.dataframe(ventas_cliente.style.format({'MONTO': '${:,.2f}', 'CANTIDAD': '{:,.0f}'}))

                    top_clientes = ventas_cliente.head(10)
                    grafico_clientes = alt.Chart(top_clientes).mark_bar().encode(
                        x=alt.X('CLIENTE:N', sort='-y', title='Cliente'),
                        y=alt.Y('MONTO:Q', title='Monto ($)'),
                        tooltip=['CLIENTE', 'MONTO']
                    ).properties(width=700, height=400)

                    st.altair_chart(grafico_clientes, use_container_width=True)
                else:
                    st.warning("El archivo no contiene la columna 'CLIENTE'")

            with tab3:
                st.subheader("📊 Análisis Mensual")

                años_disponibles = sorted(datos['AÑO'].dropna().unique(), reverse=True)
                años_seleccionados = st.multiselect("Selecciona año(s):", años_disponibles, default=años_disponibles[:2], key="anios_mes")

                datos_filtrados = datos[datos['AÑO'].isin(años_seleccionados)]

                ventas_anuales = datos_filtrados.groupby(['AÑO', 'MES_NUM', 'MES']).agg({
                    'MONTO': 'sum',
                    'CANTIDAD': 'sum'
                }).reset_index().sort_values(by='MES_NUM')

                st.dataframe(ventas_anuales.style.format({
                    'MONTO': '${:,.2f}',
                    'CANTIDAD': '{:,.0f}'
                }))

                st.subheader("📈 Comparativa Interanual")
                grafico_anual = alt.Chart(ventas_anuales).mark_line(point=True).encode(
                    x=alt.X('MES:N', sort=['Ene','Feb','Mar','Abr','May','Jun',
                                          'Jul','Ago','Sep','Oct','Nov','Dic']),
                    y=alt.Y('MONTO:Q', title='Monto ($)'),
                    color='AÑO:N',
                    tooltip=['AÑO', 'MES', 'MONTO']
                ).properties(width=700, height=400)

                st.altair_chart(grafico_anual, use_container_width=True)

                # Exportar a Excel
                try:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        ventas_anuales.to_excel(writer, index=False, sheet_name='Ventas_Anuales')
                        writer._save()
                    
                    st.download_button(
                        label="📥 Descargar Excel",
                        data=output.getvalue(),
                        file_name="reporte_ventas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="excel_mes"
                    )
                except Exception as e:
                    st.error(f"Error al exportar: {str(e)}")

            with tab4:
                st.subheader("🔍 Consulta por Producto")
                
                # Manejo flexible de columnas
                if 'COD_PROD' not in datos.columns:
                    alternativas = ['PRODUCTO', 'ITEM', 'SKU', 'CODIGO']
                    for alt_col in alternativas:
                        if alt_col in datos.columns:
                            datos['COD_PROD'] = datos[alt_col].astype(str)
                            st.warning(f"Usando columna '{alt_col}' como identificador")
                            break
                    else:
                        datos['COD_PROD'] = "Sin código"
                
                if 'VENDEDOR' not in datos.columns:
                    datos['VENDEDOR'] = "No especificado"

                with st.sidebar:
                    st.header("🔎 Filtros")
                    codigos = sorted(datos['COD_PROD'].unique())
                    cod_input = st.selectbox("Código de producto", codigos, key="cod_prod")
                    
                    min_fecha = datos['FECHA_DT'].min().date()
                    max_fecha = datos['FECHA_DT'].max().date()
                    fecha_inicio = st.date_input("Desde", min_fecha, key="fecha_ini")
                    fecha_fin = st.date_input("Hasta", max_fecha, key="fecha_fin")
                    
                    vendedores = sorted(datos['VENDEDOR'].unique())
                    vendedor_sel = st.selectbox("Vendedor", ["Todos"] + vendedores, key="vendedor")

                # Aplicar filtros
                resultado = datos[
                    (datos['COD_PROD'] == cod_input) &
                    (datos['FECHA_DT'].dt.date >= fecha_inicio) &
                    (datos['FECHA_DT'].dt.date <= fecha_fin)
                ]
                
                if vendedor_sel != "Todos":
                    resultado = resultado[resultado['VENDEDOR'] == vendedor_sel]

                if not resultado.empty:
                    resultado['FECHA'] = resultado['FECHA_DT'].dt.strftime('%d/%m/%Y')
                    
                    columnas_posibles = ['VENDEDOR', 'FECHA', 'PRECIO', 'COD_PROD', 'DESCRIPCION', 'CANTIDAD', 'MONTO']
                    columnas_mostrar = [col for col in columnas_posibles if col in resultado.columns]
                    
                    st.success(f"🔍 {len(resultado)} registros encontrados")
                    st.dataframe(resultado[columnas_mostrar].sort_values('FECHA_DT'))
                    
                    # Totales
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Unidades", f"{resultado['CANTIDAD'].sum():,.0f}")
                    with col2:
                        st.metric("Total Vendido", f"${resultado['MONTO'].sum():,.2f}")
                    
                    # Descarga
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        resultado[columnas_mostrar].to_excel(writer, index=False)
                    st.download_button(
                        label="📥 Descargar resultados",
                        data=output.getvalue(),
                        file_name=f"ventas_{cod_input}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="excel_prod"
                    )
                else:
                    st.warning("No se encontraron resultados")

        except Exception as e:
            st.error(f"Error al procesar: {str(e)}")
    else:
        st.info("ℹ️ Sube un archivo Excel para comenzar")

if __name__ == "__main__":
    main()
