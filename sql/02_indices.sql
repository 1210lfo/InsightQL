-- ============================================================================
-- InsightQL - Índices Optimizados
-- ============================================================================
-- EJECUTAR EN SUPABASE SQL EDITOR
-- Estos índices optimizan queries para 300k+ registros
-- ============================================================================

-- ============================================================================
-- ÍNDICES SIMPLES (columnas de filtro frecuente)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_fact_marca ON fact_table(marca);
CREATE INDEX IF NOT EXISTS idx_fact_categoria ON fact_table(categoria);
CREATE INDEX IF NOT EXISTS idx_fact_segmento ON fact_table(segmento);
CREATE INDEX IF NOT EXISTS idx_fact_color ON fact_table(color);
CREATE INDEX IF NOT EXISTS idx_fact_subcategoria ON fact_table(subcategoria);
CREATE INDEX IF NOT EXISTS idx_fact_disponibilidad ON fact_table(disponibilidad);
CREATE INDEX IF NOT EXISTS idx_fact_talla ON fact_table(talla);

-- ============================================================================
-- ÍNDICES PARA PRECIOS Y DESCUENTOS
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_fact_precio_final ON fact_table(precio_final);
CREATE INDEX IF NOT EXISTS idx_fact_precio ON fact_table(precio);
CREATE INDEX IF NOT EXISTS idx_fact_descuento ON fact_table(descuento);

-- ============================================================================
-- ÍNDICES COMPUESTOS (queries comunes)
-- ============================================================================

-- Filtros básicos combinados
CREATE INDEX IF NOT EXISTS idx_fact_cat_seg ON fact_table(categoria, segmento);
CREATE INDEX IF NOT EXISTS idx_fact_cat_seg_color ON fact_table(categoria, segmento, color);
CREATE INDEX IF NOT EXISTS idx_fact_cat_seg_desc ON fact_table(categoria, segmento, descuento);
CREATE INDEX IF NOT EXISTS idx_fact_seg_precio ON fact_table(segmento, precio_final);
CREATE INDEX IF NOT EXISTS idx_fact_cat_subcat ON fact_table(categoria, subcategoria);
CREATE INDEX IF NOT EXISTS idx_fact_marca_cat_seg ON fact_table(marca, categoria, segmento);

-- Búsqueda avanzada por subcategoría
CREATE INDEX IF NOT EXISTS idx_fact_subcat_seg_precio ON fact_table(subcategoria, segmento, precio_final DESC);

-- Búsqueda por talla
CREATE INDEX IF NOT EXISTS idx_fact_cat_talla ON fact_table(categoria, talla);
CREATE INDEX IF NOT EXISTS idx_fact_seg_talla ON fact_table(segmento, talla);

-- ============================================================================
-- ÍNDICES PARCIALES (muy eficientes para filtros comunes)
-- ============================================================================

-- Solo productos con descuento
CREATE INDEX IF NOT EXISTS idx_fact_con_descuento 
ON fact_table(categoria, segmento, descuento) 
WHERE descuento > 0;

-- Solo productos disponibles
CREATE INDEX IF NOT EXISTS idx_fact_disponibles 
ON fact_table(categoria, segmento) 
WHERE disponibilidad = 'available';

-- Solo productos disponibles con precio
CREATE INDEX IF NOT EXISTS idx_fact_disponibles_precio 
ON fact_table(categoria, segmento, precio_final DESC) 
WHERE disponibilidad = 'available';

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'fact_table';
