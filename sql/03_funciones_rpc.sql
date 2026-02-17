-- ============================================================================
-- InsightQL - Funciones RPC Finales
-- ============================================================================
-- EJECUTAR EN SUPABASE SQL EDITOR
-- Versión final optimizada para 337k+ registros
-- Fecha: Febrero 2026
-- ============================================================================

-- ============================================================================
-- 1. RESUMEN DEL CATÁLOGO
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_catalog_summary()
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_productos', COUNT(*),
            'total_marcas', COUNT(DISTINCT marca),
            'total_categorias', COUNT(DISTINCT categoria),
            'total_subcategorias', COUNT(DISTINCT subcategoria),
            'total_segmentos', COUNT(DISTINCT segmento),
            'total_colores', COUNT(DISTINCT color),
            'total_tallas', COUNT(DISTINCT talla),
            'precio_promedio', ROUND(AVG(precio_final)::numeric, 0),
            'precio_minimo', MIN(precio_final),
            'precio_maximo', MAX(precio_final),
            'productos_disponibles', COUNT(*) FILTER (WHERE disponibilidad = 'available'),
            'productos_agotados', COUNT(*) FILTER (WHERE disponibilidad != 'available'),
            'productos_con_descuento', COUNT(*) FILTER (WHERE descuento > 0),
            'descuento_promedio_pct', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento ELSE 0 END)::numeric * 100, 1),
            '_optimizado', true
        )
        FROM fact_table
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 2. DIMENSIONES DEL CATÁLOGO (valores únicos)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_catalog_dimensions()
RETURNS JSON AS $$
BEGIN
    RETURN json_build_object(
        'marcas', (SELECT COALESCE(json_agg(m), '[]'::json) FROM (SELECT DISTINCT marca as m FROM fact_table WHERE marca IS NOT NULL ORDER BY marca LIMIT 50) sub),
        'categorias', (SELECT COALESCE(json_agg(c), '[]'::json) FROM (SELECT DISTINCT categoria as c FROM fact_table WHERE categoria IS NOT NULL ORDER BY categoria) sub),
        'segmentos', (SELECT COALESCE(json_agg(s), '[]'::json) FROM (SELECT DISTINCT segmento as s FROM fact_table WHERE segmento IS NOT NULL ORDER BY segmento) sub),
        'colores', (SELECT COALESCE(json_agg(c), '[]'::json) FROM (SELECT DISTINCT color as c FROM fact_table WHERE color IS NOT NULL ORDER BY color LIMIT 30) sub),
        'tallas', (SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT DISTINCT talla as t FROM fact_table WHERE talla IS NOT NULL ORDER BY talla LIMIT 50) sub)
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 3. CONTEO DE PRODUCTOS CON FILTROS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_count_products(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_precio_min NUMERIC DEFAULT NULL,
    p_precio_max NUMERIC DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    total_count BIGINT;
    precio_prom NUMERIC;
    precio_min_result NUMERIC;
    precio_max_result NUMERIC;
BEGIN
    SELECT COUNT(*), ROUND(AVG(precio_final)::numeric, 0), MIN(precio_final), MAX(precio_final)
    INTO total_count, precio_prom, precio_min_result, precio_max_result
    FROM fact_table
    WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_subcategoria IS NULL OR subcategoria ILIKE '%' || p_subcategoria || '%')
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
      AND (p_precio_min IS NULL OR precio_final >= p_precio_min)
      AND (p_precio_max IS NULL OR precio_final <= p_precio_max)
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad);

    RETURN json_build_object(
        'total_productos', total_count,
        'precio_promedio', precio_prom,
        'precio_minimo', precio_min_result,
        'precio_maximo', precio_max_result,
        'filtros', json_build_object(
            'categoria', p_categoria, 'segmento', p_segmento, 'color', p_color,
            'subcategoria', p_subcategoria, 'marca', p_marca, 'talla', p_talla,
            'precio_min', p_precio_min, 'precio_max', p_precio_max, 'disponibilidad', p_disponibilidad
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 4. ANÁLISIS DE PRECIOS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_price_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_productos', COUNT(*),
            'precio_original_promedio', ROUND(AVG(precio)::numeric, 0),
            'precio_final_promedio', ROUND(AVG(precio_final)::numeric, 0),
            'precio_minimo', MIN(precio_final),
            'precio_maximo', MAX(precio_final),
            'descuento_promedio_pct', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento ELSE 0 END)::numeric * 100, 1),
            'productos_con_descuento', COUNT(*) FILTER (WHERE descuento > 0),
            'ahorro_total_potencial', ROUND(SUM(precio - precio_final)::numeric, 0),
            'filtros', json_build_object('categoria', p_categoria, 'segmento', p_segmento, 'marca', p_marca),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
          AND (p_segmento IS NULL OR segmento = p_segmento)
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 5. ANÁLISIS DE DESCUENTOS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_discount_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_productos', COUNT(*),
            'productos_con_descuento', COUNT(*) FILTER (WHERE descuento > 0),
            'productos_sin_descuento', COUNT(*) FILTER (WHERE descuento = 0 OR descuento IS NULL),
            'porcentaje_con_descuento', ROUND(COUNT(*) FILTER (WHERE descuento > 0)::numeric / NULLIF(COUNT(*), 0) * 100, 1),
            'descuento_promedio_pct', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento * 100 ELSE NULL END)::numeric, 1),
            'descuento_maximo_pct', ROUND(MAX(descuento)::numeric * 100, 1),
            'ahorro_total', ROUND(SUM(precio - precio_final)::numeric, 0),
            'ahorro_promedio', ROUND(AVG(precio - precio_final)::numeric, 0),
            'filtros', json_build_object('categoria', p_categoria, 'segmento', p_segmento, 'marca', p_marca),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
          AND (p_segmento IS NULL OR segmento = p_segmento)
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 6. ANÁLISIS DE DISPONIBILIDAD
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_availability_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH base_data AS (
            SELECT categoria, disponibilidad, COUNT(*) as cnt
            FROM fact_table
            WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
              AND (p_segmento IS NULL OR segmento = p_segmento)
            GROUP BY categoria, disponibilidad
        ),
        totals AS (
            SELECT SUM(cnt) as total,
                   SUM(cnt) FILTER (WHERE disponibilidad = 'available') as disponibles,
                   SUM(cnt) FILTER (WHERE disponibilidad != 'available') as agotados
            FROM base_data
        ),
        por_cat AS (
            SELECT json_agg(json_build_object(
                'categoria', categoria, 'total', total, 'disponibles', disp, 'agotados', agot,
                'porcentaje_disponible', ROUND(disp::numeric / NULLIF(total, 0) * 100, 1)
            ) ORDER BY total DESC) as data
            FROM (
                SELECT categoria, SUM(cnt) as total,
                       SUM(cnt) FILTER (WHERE disponibilidad = 'available') as disp,
                       SUM(cnt) FILTER (WHERE disponibilidad != 'available') as agot
                FROM base_data GROUP BY categoria
            ) sub
        )
        SELECT json_build_object(
            'total_productos', t.total, 'disponibles', t.disponibles, 'agotados', t.agotados,
            'porcentaje_disponible', ROUND(t.disponibles::numeric / NULLIF(t.total, 0) * 100, 1),
            'porcentaje_agotado', ROUND(t.agotados::numeric / NULLIF(t.total, 0) * 100, 1),
            'por_categoria', pc.data,
            'filtros', json_build_object('categoria', p_categoria, 'segmento', p_segmento, 'marca', p_marca),
            '_optimizado', true
        )
        FROM totals t, por_cat pc
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 7. COMPARACIÓN DE PRECIOS POR SEGMENTO
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_segment_price_comparison(
    p_categoria TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'comparacion_segmentos', (
                SELECT json_agg(seg_data ORDER BY precio_final_promedio DESC)
                FROM (
                    SELECT json_build_object(
                        'segmento', segmento, 'total_productos', COUNT(*),
                        'precio_promedio', ROUND(AVG(precio)::numeric, 0),
                        'precio_final_promedio', ROUND(AVG(precio_final)::numeric, 0),
                        'precio_minimo', MIN(precio_final), 'precio_maximo', MAX(precio_final),
                        'descuento_promedio', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento * 100 ELSE 0 END)::numeric, 1)
                    ) as seg_data, ROUND(AVG(precio_final)::numeric, 0) as precio_final_promedio
                    FROM fact_table
                    WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%') 
                      AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
                    GROUP BY segmento
                ) sub
            ),
            'filtros', json_build_object('categoria', p_categoria, 'marca', p_marca),
            '_optimizado', true
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 8. DISTRIBUCIÓN POR SUBCATEGORÍA
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_subcategory_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH filtered AS (
            SELECT subcategoria, precio_final FROM fact_table
            WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
              AND (p_segmento IS NULL OR segmento = p_segmento)
        ),
        total AS (SELECT COUNT(*) as cnt FROM filtered),
        distribution AS (
            SELECT subcategoria, COUNT(*) as total_productos, ROUND(AVG(precio_final)::numeric, 0) as precio_promedio
            FROM filtered GROUP BY subcategoria
        )
        SELECT json_build_object(
            'total_registros', t.cnt,
            'distribucion', (
                SELECT json_agg(json_build_object(
                    'subcategoria', d.subcategoria, 'total_productos', d.total_productos,
                    'porcentaje_catalogo', ROUND(d.total_productos::numeric / NULLIF(t.cnt, 0) * 100, 1),
                    'precio_promedio', d.precio_promedio
                ) ORDER BY d.total_productos DESC) FROM distribution d
            ),
            'filtros', json_build_object('categoria', p_categoria, 'segmento', p_segmento, 'marca', p_marca),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 9. MEJORES OFERTAS (con filtro de disponibilidad)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_best_deals(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH deals AS (
            SELECT articulo, modelo, marca, categoria, segmento, precio, precio_final, disponibilidad, talla,
                   (precio - precio_final) as ahorro, 
                   ROUND(((precio - precio_final) / NULLIF(precio, 0) * 100)::numeric, 1) as descuento_pct,
                   ROW_NUMBER() OVER (ORDER BY (precio - precio_final) DESC) as rank_ahorro,
                   ROW_NUMBER() OVER (ORDER BY ((precio - precio_final) / NULLIF(precio, 0)) DESC) as rank_pct
            FROM fact_table
            WHERE precio > precio_final
              AND precio_final > 0
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
        ),
        total AS (SELECT COUNT(*) as cnt FROM deals)
        SELECT json_build_object(
            'total_con_descuento', t.cnt,
            'mejores_por_ahorro', (
                SELECT COALESCE(json_agg(json_build_object(
                    'articulo', articulo, 'modelo', modelo, 'marca', marca,
                    'categoria', categoria, 'segmento', segmento, 'talla', talla,
                    'precio_original', precio, 'precio_final', precio_final, 
                    'ahorro', ahorro, 'descuento_pct', descuento_pct,
                    'disponibilidad', disponibilidad
                )), '[]'::json) FROM deals WHERE rank_ahorro <= p_limit
            ),
            'mejores_por_porcentaje', (
                SELECT COALESCE(json_agg(json_build_object(
                    'articulo', articulo, 'modelo', modelo, 'marca', marca,
                    'categoria', categoria, 'segmento', segmento, 'talla', talla,
                    'precio_original', precio, 'precio_final', precio_final, 
                    'ahorro', ahorro, 'descuento_pct', descuento_pct,
                    'disponibilidad', disponibilidad
                )), '[]'::json) FROM deals WHERE rank_pct <= p_limit
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 
                'segmento', p_segmento, 
                'marca', p_marca,
                'disponibilidad', p_disponibilidad
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 10. BÚSQUEDA AVANZADA DE PRODUCTOS (con filtro de talla)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_search_products_advanced(
    p_subcategoria TEXT DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_precio_min NUMERIC DEFAULT NULL,
    p_precio_max NUMERIC DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_orden TEXT DEFAULT 'desc',
    p_limit INT DEFAULT 5
)
RETURNS JSON AS $$
DECLARE
    total_count BIGINT;
    productos_json JSON;
BEGIN
    -- Contar total (query simple, usa índices)
    SELECT COUNT(*) INTO total_count
    FROM fact_table
    WHERE precio_final IS NOT NULL
      AND (p_subcategoria IS NULL OR subcategoria ILIKE '%' || p_subcategoria || '%')
      AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
      AND (p_precio_min IS NULL OR precio_final >= p_precio_min)
      AND (p_precio_max IS NULL OR precio_final <= p_precio_max)
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad);

    -- Obtener productos con LIMIT
    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo,
            'modelo', modelo,
            'marca', marca,
            'precio_original', precio,
            'precio_final', precio_final,
            'ahorro', precio - precio_final,
            'descuento_pct', ROUND(COALESCE(descuento, 0)::numeric * 100, 1),
            'talla', talla,
            'categoria', categoria,
            'subcategoria', subcategoria,
            'segmento', segmento,
            'color', color,
            'disponibilidad', disponibilidad
        ) as row_data
        FROM fact_table
        WHERE precio_final IS NOT NULL
          AND (p_subcategoria IS NULL OR subcategoria ILIKE '%' || p_subcategoria || '%')
          AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
          AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
          AND (p_precio_min IS NULL OR precio_final >= p_precio_min)
          AND (p_precio_max IS NULL OR precio_final <= p_precio_max)
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
        ORDER BY 
            CASE WHEN p_orden = 'asc' THEN precio_final END ASC,
            CASE WHEN p_orden != 'asc' THEN precio_final END DESC
        LIMIT p_limit
    ) sub;

    RETURN json_build_object(
        'total_encontrados', total_count,
        'tipo_consulta', CASE WHEN p_orden = 'desc' THEN 'mas caros' ELSE 'mas baratos' END,
        'productos', productos_json,
        'filtros', json_build_object(
            'subcategoria', p_subcategoria,
            'categoria', p_categoria,
            'segmento', p_segmento,
            'color', p_color,
            'marca', p_marca,
            'talla', p_talla,
            'precio_min', p_precio_min,
            'precio_max', p_precio_max,
            'disponibilidad', p_disponibilidad
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 11. OBTENER SUBCATEGORÍAS
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_get_subcategorias()
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'subcategorias', (
                SELECT COALESCE(json_agg(json_build_object(
                    'subcategoria', subcategoria,
                    'categoria', categoria,
                    'total', cnt
                ) ORDER BY cnt DESC), '[]'::json)
                FROM (
                    SELECT subcategoria, categoria, COUNT(*) as cnt
                    FROM fact_table
                    WHERE subcategoria IS NOT NULL
                    GROUP BY subcategoria, categoria
                ) sub
            )
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 12. OBTENER TALLAS DISPONIBLES
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_get_tallas(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'tallas', (
                SELECT COALESCE(json_agg(json_build_object(
                    'talla', talla,
                    'total', cnt,
                    'disponibles', disp
                ) ORDER BY cnt DESC), '[]'::json)
                FROM (
                    SELECT talla, 
                           COUNT(*) as cnt,
                           COUNT(*) FILTER (WHERE disponibilidad = 'available') as disp
                    FROM fact_table
                    WHERE talla IS NOT NULL
                      AND (p_categoria IS NULL OR categoria ILIKE '%' || p_categoria || '%')
                      AND (p_segmento IS NULL OR segmento = p_segmento)
                      AND (p_subcategoria IS NULL OR subcategoria ILIKE '%' || p_subcategoria || '%')
                    GROUP BY talla
                ) sub
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 
                'segmento', p_segmento, 
                'subcategoria', p_subcategoria
            )
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- SELECT rpc_catalog_summary();
-- SELECT rpc_catalog_dimensions();
-- SELECT rpc_count_products(p_talla := 'M');
-- SELECT rpc_price_analysis(p_marca := 'Adidas');
-- SELECT rpc_discount_analysis(p_categoria := 'Calzado');
-- SELECT rpc_availability_analysis();
-- SELECT rpc_segment_price_comparison();
-- SELECT rpc_subcategory_distribution(p_categoria := 'Ropa exterior');
-- SELECT rpc_best_deals(p_disponibilidad := 'available', p_limit := 5);
-- SELECT rpc_search_products_advanced(p_subcategoria := 'Chaqueta', p_segmento := 'Hombre', p_color := 'Azul', p_talla := 'M');
-- SELECT rpc_get_subcategorias();
-- SELECT rpc_get_tallas(p_categoria := 'Calzado', p_segmento := 'Hombre');
