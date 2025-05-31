with tab4:
    st.subheader("🔍 Consulta de Ventas por Producto")
    
    # 1. Verificar columnas obligatorias
    columnas_requeridas = ['CANTIDAD', 'MONTO']
    columnas_faltantes = [col for col in columnas_requeridas if col not in datos.columns]
    
    if columnas_faltantes:
        st.error(f"Error: Faltan columnas requeridas: {', '.join(columnas_faltantes)}")
        st.stop()  # Detener ejecución si faltan columnas críticas
    
    # 2. Manejo flexible de fechas (buscar posibles nombres)
    fecha_col = None
    posibles_nombres_fecha = ['FECHA', 'FECHA_VENTA', 'DATE', 'FECHACOMPRA']
    
    for nombre in posibles_nombres_fecha:
        if nombre in datos.columns:
            fecha_col = nombre
            datos['FECHA_DT'] = pd.to_datetime(datos[nombre], errors='coerce')
            break
    
    if fecha_col is None:
        st.error("No se encontró ninguna columna de fecha válida")
        st.stop()
    
    # 3. Manejo de código de producto
    if 'COD_PROD' not in datos.columns:
        alternativas = ['PRODUCTO', 'ITEM', 'SKU', 'CODIGO']
        for alt in alternativas:
            if alt in datos.columns:
                datos['COD_PROD'] = datos[alt].astype(str)
                st.warning(f"Usando columna '{alt}' como identificador de producto")
                break
        else:
            datos['COD_PROD'] = "Sin código"
            st.warning("No se encontró columna de código de producto")
    
    # 4. Manejo de vendedor
    if 'VENDEDOR' not in datos.columns:
        alternativas = ['VENDEDOR_NOMBRE', 'EMPLEADO', 'ASESOR']
        for alt in alternativas:
            if alt in datos.columns:
                datos['VENDEDOR'] = datos[alt].astype(str)
                break
        else:
            datos['VENDEDOR'] = "No especificado"
    
    # Filtros en sidebar
    with st.sidebar:
        st.header("🔎 Filtros de Producto")
        
        # Selector de código de producto
        codigos = sorted(datos['COD_PROD'].unique())
        cod_input = st.selectbox("Código de producto", codigos, key="cod_prod")
        
        # Rango de fechas
        min_fecha = datos['FECHA_DT'].min().date()
        max_fecha = datos['FECHA_DT'].max().date()
        fecha_inicio = st.date_input("Desde", min_fecha, key="fecha_ini")
        fecha_fin = st.date_input("Hasta", max_fecha, key="fecha_fin")
        
        # Filtro por vendedor
        vendedores = sorted(datos['VENDEDOR'].unique())
        vendedor_sel = st.selectbox("Vendedor", ["Todos"] + vendedores, key="vendedor")
    
    # Aplicar filtros
    mask = (
        (datos['COD_PROD'] == cod_input) &
        (datos['FECHA_DT'].dt.date >= fecha_inicio) &
        (datos['FECHA_DT'].dt.date <= fecha_fin)
    )
    resultado = datos[mask].copy()
    
    if vendedor_sel != "Todos":
        resultado = resultado[resultado['VENDEDOR'] == vendedor_sel]
    
    # Mostrar resultados
    if not resultado.empty:
        resultado['FECHA'] = resultado['FECHA_DT'].dt.strftime('%d/%m/%Y')
        
        # Columnas a mostrar (solo las existentes)
        columnas_posibles = ['VENDEDOR', 'FECHA', 'PRECIO', 'COD_PROD', 
                            'DESCRIPCION', 'CANTIDAD', 'MONTO']
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No se encontraron resultados con los filtros aplicados")
