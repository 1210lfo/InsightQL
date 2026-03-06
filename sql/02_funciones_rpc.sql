-- ============================================================================
-- InsightQL - TODAS LAS FUNCIONES RPC (versión final consolidada)
-- ============================================================================
-- EJECUTAR COMPLETO EN SUPABASE SQL EDITOR
--
-- Este archivo contiene las 16 funciones RPC activas del proyecto.
-- Incluye SET search_path = public en cada función.
-- Todas usan CREATE OR REPLACE (seguro para re-ejecutar).
--
-- TOTAL: 16 funciones RPC
--
-- ANTES de ejecutar, limpia overloads antiguos:
--   DROP FUNCTION IF EXISTS public.rpc_article_available_sizes(TEXT);
--   (ver sección LIMPIEZA al final)
--
-- Última actualización: Marzo 2026
-- ============================================================================


-- ============================================================================
-- 1. rpc_catalog_summary - Resumen general del catálogo (sin params)
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
            'descuento_promedio_pct', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento ELSE NULL END)::numeric * 100, 1),
            '_optimizado', true
        )
        FROM fact_table
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_catalog_summary() SET search_path = public;


-- ============================================================================
-- 2. rpc_price_analysis - Análisis de precios
--    Params: p_categoria, p_segmento, p_marca, p_subcategoria, p_color,
--            p_talla, p_disponibilidad, p_articulo
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_price_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_articulo TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_productos', COUNT(*),
            'articulos_unicos', COUNT(DISTINCT articulo),
            'precio_original_promedio', ROUND(AVG(precio)::numeric, 0),
            'precio_final_promedio', ROUND(AVG(precio_final)::numeric, 0),
            'precio_minimo', MIN(precio_final),
            'precio_maximo', MAX(precio_final),
            'descuento_promedio_pct', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento ELSE NULL END)::numeric * 100, 1),
            'productos_con_descuento', COUNT(*) FILTER (WHERE descuento > 0),
            'ahorro_total_potencial', ROUND(SUM(CASE WHEN precio > precio_final THEN precio - precio_final ELSE 0 END)::numeric, 0),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'subcategoria', p_subcategoria,
                'color', p_color, 'talla', p_talla,
                'disponibilidad', p_disponibilidad, 'articulo', p_articulo
            ),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
          AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
          AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%')
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_price_analysis(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 3. rpc_discount_analysis - Análisis de descuentos
--    Params: p_categoria, p_segmento, p_marca, p_subcategoria, p_color,
--            p_talla, p_disponibilidad, p_articulo
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_discount_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_articulo TEXT DEFAULT NULL
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
            'ahorro_total', ROUND(SUM(CASE WHEN precio > precio_final THEN precio - precio_final ELSE 0 END)::numeric, 0),
            'ahorro_promedio', ROUND(AVG(CASE WHEN precio > precio_final AND precio_final > 0 THEN precio - precio_final ELSE NULL END)::numeric, 0),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'subcategoria', p_subcategoria,
                'color', p_color, 'talla', p_talla,
                'disponibilidad', p_disponibilidad, 'articulo', p_articulo
            ),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
          AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
          AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%')
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_discount_analysis(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 4. rpc_availability_analysis - Análisis de disponibilidad
--    Params: p_categoria, p_segmento, p_marca, p_color, p_subcategoria, p_talla
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_availability_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH base_data AS (
            SELECT categoria, disponibilidad, COUNT(*) as cnt
            FROM fact_table
            WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
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
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'color', p_color,
                'subcategoria', p_subcategoria, 'talla', p_talla
            ),
            '_optimizado', true
        )
        FROM totals t, por_cat pc
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_availability_analysis(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 5. rpc_segment_price_comparison - Comparación de precios por segmento
--    Params: p_categoria, p_marca, p_color, p_subcategoria
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_segment_price_comparison(
    p_categoria TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL
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
                        'descuento_promedio', ROUND(AVG(CASE WHEN descuento > 0 THEN descuento * 100 ELSE NULL END)::numeric, 1)
                    ) as seg_data, ROUND(AVG(precio_final)::numeric, 0) as precio_final_promedio
                    FROM fact_table
                    WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
                      AND (p_categoria IS NULL OR categoria = p_categoria)
                      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
                      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
                    GROUP BY segmento
                ) sub
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 'marca', p_marca,
                'color', p_color, 'subcategoria', p_subcategoria
            ),
            '_optimizado', true
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_segment_price_comparison(TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 6. rpc_category_price_comparison - Comparación de precios por categoría
--    Params: p_marca, p_segmento, p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_category_price_comparison(
    p_marca TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'comparacion_categorias', (
                SELECT COALESCE(json_agg(cat_data ORDER BY precio_final_promedio DESC), '[]'::json)
                FROM (
                    SELECT json_build_object(
                        'categoria', categoria,
                        'total_productos', COUNT(*),
                        'precio_promedio_original', ROUND(AVG(precio)::numeric, 0),
                        'precio_promedio_final', ROUND(AVG(precio_final)::numeric, 0),
                        'precio_minimo', MIN(precio_final),
                        'precio_maximo', MAX(precio_final),
                        'descuento_promedio_pct', ROUND(
                            AVG(CASE WHEN descuento > 0 THEN descuento * 100 ELSE NULL END)::numeric, 1
                        )
                    ) AS cat_data,
                    ROUND(AVG(precio_final)::numeric, 0) AS precio_final_promedio
                    FROM fact_table
                    WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
                      AND (p_segmento IS NULL OR segmento = p_segmento)
                      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
                    GROUP BY categoria
                ) sub
            ),
            'filtros', json_build_object('marca', p_marca, 'segmento', p_segmento, 'color', p_color),
            '_optimizado', true
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_category_price_comparison(TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 7. rpc_subcategory_distribution - Distribución por subcategoría
--    Params: p_categoria, p_segmento, p_marca, p_color, p_disponibilidad
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_subcategory_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH filtered AS (
            SELECT subcategoria, precio_final FROM fact_table
            WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
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
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'color', p_color,
                'disponibilidad', p_disponibilidad
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_subcategory_distribution(TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 8. rpc_model_variety - Análisis de variedad de modelos
--    Params: p_categoria, p_segmento, p_marca, p_color,
--            p_subcategoria, p_disponibilidad
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_model_variety(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH filtered AS (
            SELECT articulo, modelo, color, talla
            FROM fact_table
            WHERE (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
        ),
        totals AS (
            SELECT COUNT(*) AS total_registros,
                   COUNT(DISTINCT articulo) AS articulos_unicos,
                   COUNT(DISTINCT modelo) AS modelos_unicos,
                   COUNT(DISTINCT color) AS colores_unicos
            FROM filtered
        ),
        top_articulos AS (
            SELECT articulo,
                   COUNT(*) AS total_variantes,
                   COUNT(DISTINCT modelo) AS colores_unicos
            FROM filtered
            WHERE articulo IS NOT NULL
            GROUP BY articulo
            ORDER BY total_variantes DESC
            LIMIT 15
        )
        SELECT json_build_object(
            'total_registros', t.total_registros,
            'articulos_unicos', t.articulos_unicos,
            'modelos_colores_unicos', t.modelos_unicos,
            'colores_unicos', t.colores_unicos,
            'promedio_variantes_por_articulo', ROUND(
                t.total_registros::numeric / NULLIF(t.articulos_unicos, 0), 1
            ),
            'top_15_articulos_con_mas_variantes', (
                SELECT COALESCE(json_agg(json_build_object(
                    'articulo', articulo,
                    'total_variantes', total_variantes,
                    'colores_unicos', colores_unicos
                ) ORDER BY total_variantes DESC), '[]'::json)
                FROM top_articulos
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'color', p_color,
                'subcategoria', p_subcategoria, 'disponibilidad', p_disponibilidad
            ),
            '_optimizado', true
        )
        FROM totals t
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_model_variety(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 9. rpc_price_distribution - Distribución de precios por rango
--    Params: p_categoria, p_segmento, p_marca, p_color,
--            p_subcategoria, p_disponibilidad
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_price_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH filtered AS (
            SELECT precio_final
            FROM fact_table
            WHERE precio_final IS NOT NULL
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
        ),
        total AS (SELECT COUNT(*) AS cnt FROM filtered),
        rangos AS (
            SELECT
                CASE
                    WHEN precio_final < 100000 THEN '0-100k'
                    WHEN precio_final < 200000 THEN '100k-200k'
                    WHEN precio_final < 300000 THEN '200k-300k'
                    WHEN precio_final < 400000 THEN '300k-400k'
                    WHEN precio_final < 500000 THEN '400k-500k'
                    WHEN precio_final < 750000 THEN '500k-750k'
                    WHEN precio_final < 1000000 THEN '750k-1M'
                    ELSE '>1M'
                END AS rango,
                CASE
                    WHEN precio_final < 100000 THEN 1
                    WHEN precio_final < 200000 THEN 2
                    WHEN precio_final < 300000 THEN 3
                    WHEN precio_final < 400000 THEN 4
                    WHEN precio_final < 500000 THEN 5
                    WHEN precio_final < 750000 THEN 6
                    WHEN precio_final < 1000000 THEN 7
                    ELSE 8
                END AS orden,
                CASE
                    WHEN precio_final < 100000 THEN 0
                    WHEN precio_final < 200000 THEN 100000
                    WHEN precio_final < 300000 THEN 200000
                    WHEN precio_final < 400000 THEN 300000
                    WHEN precio_final < 500000 THEN 400000
                    WHEN precio_final < 750000 THEN 500000
                    WHEN precio_final < 1000000 THEN 750000
                    ELSE 1000000
                END AS precio_min,
                CASE
                    WHEN precio_final < 100000 THEN 100000
                    WHEN precio_final < 200000 THEN 200000
                    WHEN precio_final < 300000 THEN 300000
                    WHEN precio_final < 400000 THEN 400000
                    WHEN precio_final < 500000 THEN 500000
                    WHEN precio_final < 750000 THEN 750000
                    WHEN precio_final < 1000000 THEN 1000000
                    ELSE NULL
                END AS precio_max
            FROM filtered
        )
        SELECT json_build_object(
            'total_productos', t.cnt,
            'distribucion', (
                SELECT COALESCE(json_agg(json_build_object(
                    'rango', rango,
                    'precio_min', precio_min,
                    'precio_max', precio_max,
                    'cantidad', cantidad,
                    'porcentaje', ROUND(cantidad::numeric / NULLIF(t.cnt, 0) * 100, 1)
                ) ORDER BY orden), '[]'::json)
                FROM (
                    SELECT rango, orden, MIN(precio_min) AS precio_min, MIN(precio_max) AS precio_max,
                           COUNT(*) AS cantidad
                    FROM rangos
                    GROUP BY rango, orden
                ) agg
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'color', p_color,
                'subcategoria', p_subcategoria, 'disponibilidad', p_disponibilidad
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_price_distribution(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 10. rpc_size_distribution - Distribución de tallas
--     Params: p_categoria, p_segmento, p_marca, p_subcategoria, p_color,
--             p_disponibilidad, p_articulo
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_size_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_articulo TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH filtered AS (
            SELECT talla, disponibilidad
            FROM fact_table
            WHERE talla IS NOT NULL
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
              AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%')
        ),
        total AS (SELECT COUNT(*) AS cnt FROM filtered)
        SELECT json_build_object(
            'total_registros_analizados', t.cnt,
            'total_tallas_unicas', (SELECT COUNT(DISTINCT talla) FROM filtered),
            'distribucion', (
                SELECT COALESCE(json_agg(json_build_object(
                    'talla', talla,
                    'total', total,
                    'disponibles', disponibles,
                    'porcentaje_disponible', ROUND(disponibles::numeric / NULLIF(total, 0) * 100, 2)
                ) ORDER BY total DESC), '[]'::json)
                FROM (
                    SELECT talla,
                           COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE disponibilidad = 'available') AS disponibles
                    FROM filtered
                    GROUP BY talla
                ) sub
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'subcategoria', p_subcategoria,
                'color', p_color, 'disponibilidad', p_disponibilidad,
                'articulo', p_articulo
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_size_distribution(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 11. rpc_best_deals - Mejores ofertas (por ahorro absoluto y porcentaje)
--     Params: p_categoria, p_segmento, p_marca, p_disponibilidad, p_color,
--             p_limit, p_subcategoria, p_talla, p_articulo
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_best_deals(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10,
    p_subcategoria TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_articulo TEXT DEFAULT NULL
)
RETURNS JSON AS $$
BEGIN
    RETURN (
        WITH deals AS (
            SELECT articulo, modelo, marca, categoria, segmento, color, precio, precio_final, disponibilidad, talla,
                   (precio - precio_final) as ahorro,
                   ROUND(((precio - precio_final) / NULLIF(precio, 0) * 100)::numeric, 1) as descuento_pct,
                   ROW_NUMBER() OVER (ORDER BY (precio - precio_final) DESC) as rank_ahorro,
                   ROW_NUMBER() OVER (ORDER BY ((precio - precio_final) / NULLIF(precio, 0)) DESC) as rank_pct
            FROM fact_table
            WHERE precio > precio_final
              AND precio_final > 0
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
              AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%')
        ),
        total AS (SELECT COUNT(*) as cnt FROM deals)
        SELECT json_build_object(
            'total_con_descuento', t.cnt,
            'mejores_por_ahorro', (
                SELECT COALESCE(json_agg(json_build_object(
                    'articulo', articulo, 'modelo', modelo, 'marca', marca,
                    'categoria', categoria, 'segmento', segmento, 'color', color, 'talla', talla,
                    'precio_original', precio, 'precio_final', precio_final,
                    'ahorro', ahorro, 'descuento_pct', descuento_pct,
                    'disponibilidad', disponibilidad
                )), '[]'::json) FROM deals WHERE rank_ahorro <= p_limit
            ),
            'mejores_por_porcentaje', (
                SELECT COALESCE(json_agg(json_build_object(
                    'articulo', articulo, 'modelo', modelo, 'marca', marca,
                    'categoria', categoria, 'segmento', segmento, 'color', color, 'talla', talla,
                    'precio_original', precio, 'precio_final', precio_final,
                    'ahorro', ahorro, 'descuento_pct', descuento_pct,
                    'disponibilidad', disponibilidad
                )), '[]'::json) FROM deals WHERE rank_pct <= p_limit
            ),
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'disponibilidad', p_disponibilidad,
                'color', p_color, 'subcategoria', p_subcategoria,
                'talla', p_talla, 'articulo', p_articulo
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_best_deals(TEXT,TEXT,TEXT,TEXT,TEXT,INT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 12. rpc_discount_products - Productos con descuento (listado)
--     Params: p_categoria, p_segmento, p_marca, p_subcategoria, p_color,
--             p_limit, p_talla, p_disponibilidad, p_articulo
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_discount_products(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10,
    p_talla TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_articulo TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    total_con_descuento BIGINT;
    total_registros BIGINT;
    productos_json JSON;
BEGIN
    SELECT COUNT(*),
           (SELECT COUNT(*) FROM fact_table
            WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_categoria IS NULL OR categoria = p_categoria)
              AND (p_segmento IS NULL OR segmento = p_segmento)
              AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
              AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
              AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
              AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%'))
    INTO total_con_descuento, total_registros
    FROM fact_table
    WHERE precio > precio_final
      AND precio_final > 0
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
      AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%');

    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo, 'modelo', modelo, 'marca', marca,
            'categoria', categoria, 'segmento', segmento, 'color', color,
            'talla', talla,
            'precio_original', precio, 'precio_final', precio_final,
            'ahorro', precio - precio_final,
            'descuento_pct', ROUND(((precio - precio_final)::numeric / NULLIF(precio, 0) * 100), 1),
            'disponibilidad', disponibilidad
        ) AS row_data
        FROM fact_table
        WHERE precio > precio_final
          AND precio_final > 0
          AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
          AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
          AND (p_articulo IS NULL OR articulo ILIKE '%' || p_articulo || '%')
        ORDER BY (precio - precio_final) DESC
        LIMIT p_limit
    ) sub;

    RETURN json_build_object(
        'total_con_descuento', total_con_descuento,
        'total_registros_analizados', total_registros,
        'porcentaje_con_descuento', ROUND(
            total_con_descuento::numeric / NULLIF(total_registros, 0) * 100, 1
        ),
        'productos', productos_json,
        'filtros', json_build_object(
            'categoria', p_categoria, 'segmento', p_segmento,
            'marca', p_marca, 'subcategoria', p_subcategoria,
            'color', p_color, 'talla', p_talla,
            'disponibilidad', p_disponibilidad, 'articulo', p_articulo
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_discount_products(TEXT,TEXT,TEXT,TEXT,TEXT,INT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 13. rpc_count_by_filters - Conteo con filtros múltiples + estadísticas
--     Params: p_categoria, p_segmento, p_marca, p_color, p_subcategoria,
--             p_talla, p_disponibilidad, p_precio_min, p_precio_max
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_count_by_filters(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_precio_min NUMERIC DEFAULT NULL,
    p_precio_max NUMERIC DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_count BIGINT;
    v_precio_prom NUMERIC;
    v_precio_min NUMERIC;
    v_precio_max NUMERIC;
    v_articulos BIGINT;
BEGIN
    SELECT COUNT(*),
           ROUND(AVG(precio_final)::numeric, 0),
           MIN(precio_final),
           MAX(precio_final),
           COUNT(DISTINCT articulo)
    INTO v_count, v_precio_prom, v_precio_min, v_precio_max, v_articulos
    FROM fact_table
    WHERE (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
      AND (p_precio_min IS NULL OR precio_final >= p_precio_min)
      AND (p_precio_max IS NULL OR precio_final <= p_precio_max);

    RETURN json_build_object(
        'total_productos', v_count,
        'articulos_unicos', v_articulos,
        'precio_promedio', v_precio_prom,
        'precio_minimo', v_precio_min,
        'precio_maximo', v_precio_max,
        'filtros', json_build_object(
            'categoria', p_categoria, 'segmento', p_segmento,
            'marca', p_marca, 'color', p_color,
            'subcategoria', p_subcategoria, 'talla', p_talla,
            'disponibilidad', p_disponibilidad,
            'precio_min', p_precio_min, 'precio_max', p_precio_max
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_count_by_filters(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC) SET search_path = public;


-- ============================================================================
-- 14. rpc_search_text - Búsqueda por texto libre
--     Params: p_search_term, p_marca, p_categoria, p_segmento,
--             p_disponibilidad, p_limit, p_subcategoria, p_color, p_talla
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_search_text(
    p_search_term TEXT,
    p_marca TEXT DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_talla TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_total BIGINT;
    productos_json JSON;
    v_term TEXT;
BEGIN
    v_term := '%' || p_search_term || '%';

    SELECT COUNT(*) INTO v_total
    FROM fact_table
    WHERE (modelo ILIKE v_term OR articulo ILIKE v_term OR articulo_detalles ILIKE v_term)
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%');

    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo, 'modelo', modelo, 'marca', marca,
            'categoria', categoria, 'subcategoria', subcategoria,
            'segmento', segmento, 'color', color, 'talla', talla,
            'precio_original', precio, 'precio_final', precio_final,
            'disponibilidad', disponibilidad
        ) AS row_data
        FROM fact_table
        WHERE (modelo ILIKE v_term OR articulo ILIKE v_term OR articulo_detalles ILIKE v_term)
          AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
          AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
        ORDER BY precio_final DESC
        LIMIT p_limit
    ) sub;

    RETURN json_build_object(
        'termino_busqueda', p_search_term,
        'total_encontrados', v_total,
        'productos', productos_json,
        'filtros', json_build_object(
            'marca', p_marca, 'categoria', p_categoria,
            'segmento', p_segmento, 'disponibilidad', p_disponibilidad,
            'subcategoria', p_subcategoria, 'color', p_color, 'talla', p_talla
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_search_text(TEXT,TEXT,TEXT,TEXT,TEXT,INT,TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- 15. rpc_search_products_advanced - Búsqueda avanzada con todos los filtros
--     Params: p_subcategoria, p_categoria, p_segmento, p_color, p_marca,
--             p_talla, p_precio_min, p_precio_max, p_disponibilidad,
--             p_orden, p_limit
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
    SELECT COUNT(*) INTO total_count
    FROM fact_table
    WHERE precio_final IS NOT NULL
      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_talla IS NULL OR talla ILIKE '%' || p_talla || '%')
      AND (p_precio_min IS NULL OR precio_final >= p_precio_min)
      AND (p_precio_max IS NULL OR precio_final <= p_precio_max)
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad);

    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo, 'modelo', modelo, 'marca', marca,
            'precio_original', precio, 'precio_final', precio_final,
            'ahorro', precio - precio_final,
            'descuento_pct', ROUND(COALESCE(descuento, 0)::numeric * 100, 1),
            'talla', talla, 'categoria', categoria, 'subcategoria', subcategoria,
            'segmento', segmento, 'color', color, 'disponibilidad', disponibilidad
        ) as row_data
        FROM fact_table
        WHERE precio_final IS NOT NULL
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_categoria IS NULL OR categoria = p_categoria)
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
            'subcategoria', p_subcategoria, 'categoria', p_categoria,
            'segmento', p_segmento, 'color', p_color, 'marca', p_marca,
            'talla', p_talla, 'precio_min', p_precio_min, 'precio_max', p_precio_max,
            'disponibilidad', p_disponibilidad
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_search_products_advanced(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,TEXT,TEXT,INT) SET search_path = public;


-- ============================================================================
-- 16. rpc_article_available_sizes - Tallas disponibles de un artículo
--     Params: p_articulo, p_marca, p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_article_available_sizes(
    p_articulo TEXT,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_total_disponibles BIGINT;
    v_total_agotados BIGINT;
    tallas_json JSON;
    info_json JSON;
BEGIN
    -- Info básica del artículo
    SELECT json_build_object(
        'articulo', MIN(articulo),
        'marca', MIN(marca),
        'categoria', MIN(categoria),
        'subcategoria', MIN(subcategoria),
        'segmento', MIN(segmento),
        'precio_min', MIN(precio_final),
        'precio_max', MAX(precio_final)
    ) INTO info_json
    FROM fact_table
    WHERE articulo ILIKE '%' || p_articulo || '%'
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%');

    -- Conteos globales
    SELECT
        COUNT(*) FILTER (WHERE disponibilidad = 'available'),
        COUNT(*) FILTER (WHERE disponibilidad != 'available')
    INTO v_total_disponibles, v_total_agotados
    FROM fact_table
    WHERE articulo ILIKE '%' || p_articulo || '%'
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%');

    -- Tallas disponibles con conteo
    SELECT COALESCE(json_agg(json_build_object(
        'talla', talla,
        'cantidad_disponible', cnt
    ) ORDER BY cnt DESC), '[]'::json)
    INTO tallas_json
    FROM (
        SELECT talla, COUNT(*) AS cnt
        FROM fact_table
        WHERE articulo ILIKE '%' || p_articulo || '%'
          AND disponibilidad = 'available'
          AND talla IS NOT NULL
          AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
        GROUP BY talla
    ) sub;

    RETURN json_build_object(
        'info_articulo', info_json,
        'total_disponibles', v_total_disponibles,
        'total_agotados', v_total_agotados,
        'tallas_disponibles', (SELECT COUNT(DISTINCT talla) FROM fact_table
            WHERE articulo ILIKE '%' || p_articulo || '%'
              AND disponibilidad = 'available' AND talla IS NOT NULL
              AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')),
        'detalle_tallas', tallas_json,
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION public.rpc_article_available_sizes(TEXT,TEXT,TEXT) SET search_path = public;


-- ============================================================================
-- LIMPIEZA: Eliminar overloads antiguos (ejecutar ANTES de este script)
-- ============================================================================
-- Si vienes de una versión anterior, ejecuta estos DROP primero para
-- eliminar versiones viejas con menos parámetros:
--
-- DROP FUNCTION IF EXISTS public.rpc_article_available_sizes(TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_price_analysis(TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_price_analysis(TEXT,TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_discount_analysis(TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_discount_analysis(TEXT,TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_availability_analysis(TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_availability_analysis(TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_segment_price_comparison(TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_segment_price_comparison(TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_subcategory_distribution(TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_subcategory_distribution(TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_model_variety(TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_price_distribution(TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_size_distribution(TEXT,TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_best_deals(TEXT,TEXT,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_best_deals(TEXT,TEXT,TEXT,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_best_deals(TEXT,TEXT,TEXT,TEXT,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_discount_products(TEXT,TEXT,TEXT,TEXT,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_search_text(TEXT,TEXT,TEXT,TEXT,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_search_products_advanced(TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,TEXT,INT);
-- DROP FUNCTION IF EXISTS public.rpc_count_products(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,TEXT);
-- DROP FUNCTION IF EXISTS public.rpc_catalog_dimensions();
-- DROP FUNCTION IF EXISTS public.rpc_get_subcategorias();
-- DROP FUNCTION IF EXISTS public.rpc_get_tallas(TEXT,TEXT,TEXT);


-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

-- Confirmar que hay exactamente 16 funciones:
-- SELECT routine_name,
--        string_agg(p.data_type, ', ' ORDER BY p.ordinal_position) AS param_types,
--        COUNT(p.parameter_name) AS num_params
-- FROM information_schema.routines r
-- LEFT JOIN information_schema.parameters p
--   ON r.specific_name = p.specific_name AND p.parameter_mode = 'IN'
-- WHERE r.routine_schema = 'public' AND r.routine_name LIKE 'rpc_%'
-- GROUP BY r.routine_name, r.specific_name
-- ORDER BY r.routine_name;

-- Pruebas rápidas:
-- SELECT rpc_catalog_summary();
-- SELECT rpc_price_analysis(p_marca := 'Nike', p_talla := '42', p_disponibilidad := 'available');
-- SELECT rpc_discount_analysis(p_subcategoria := 'Tenis', p_articulo := 'Superstar');
-- SELECT rpc_availability_analysis(p_subcategoria := 'Tenis', p_talla := '42');
-- SELECT rpc_segment_price_comparison(p_subcategoria := 'Tenis');
-- SELECT rpc_category_price_comparison(p_color := 'Rojo');
-- SELECT rpc_subcategory_distribution(p_disponibilidad := 'available');
-- SELECT rpc_model_variety(p_subcategoria := 'Tenis', p_disponibilidad := 'available');
-- SELECT rpc_price_distribution(p_subcategoria := 'Tenis', p_disponibilidad := 'available');
-- SELECT rpc_size_distribution(p_disponibilidad := 'available', p_articulo := 'Superstar');
-- SELECT rpc_best_deals(p_subcategoria := 'Tenis', p_talla := '42', p_articulo := 'Air Max');
-- SELECT rpc_discount_products(p_talla := 'M', p_disponibilidad := 'available', p_articulo := 'Superstar');
-- SELECT rpc_count_by_filters(p_subcategoria := 'Tenis', p_color := 'Negro', p_segmento := 'Hombre');
-- SELECT rpc_search_text('Air Max', p_subcategoria := 'Tenis', p_color := 'Negro', p_talla := '42');
-- SELECT rpc_search_products_advanced(p_subcategoria := 'Tenis', p_color := 'Negro', p_segmento := 'Hombre', p_limit := 3);
-- SELECT rpc_article_available_sizes('Superstar', p_marca := 'Adidas', p_color := 'Blanco');
