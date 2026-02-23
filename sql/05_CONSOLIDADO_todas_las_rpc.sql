-- ============================================================================
-- InsightQL - ARCHIVO CONSOLIDADO DE TODAS LAS FUNCIONES RPC
-- ============================================================================
-- EJECUTAR COMPLETO EN SUPABASE SQL EDITOR
--
-- Este archivo reemplaza: 03_funciones_rpc.sql, FIX_ejecutar_en_supabase.sql,
-- y 04_rpc_optimizadas_v2.sql
--
-- TOTAL: 15 funciones RPC activas
-- MEJORAS en esta version:
--   - Filtro p_color agregado a TODAS las funciones de analisis (promedios/sumas)
--   - categoria/subcategoria siempre usan match EXACTO (=)
--   - marca/color/talla usan ILIKE para match parcial
--
-- Fecha: Febrero 2026
-- ============================================================================


-- ============================================================================
-- 1. rpc_catalog_summary - Resumen general del catalogo
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
-- 2. rpc_price_analysis - Analisis de precios (promedios, sumas, descuentos)
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_price_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'subcategoria', p_subcategoria, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 3. rpc_discount_analysis - Analisis de descuentos (promedios, sumas, ahorro)
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_discount_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
            'filtros', json_build_object(
                'categoria', p_categoria, 'segmento', p_segmento,
                'marca', p_marca, 'subcategoria', p_subcategoria, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM fact_table
        WHERE (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
          AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 4. rpc_availability_analysis - Analisis de disponibilidad
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_availability_analysis(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                'marca', p_marca, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM totals t, por_cat pc
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 5. rpc_segment_price_comparison - Comparacion de precios por segmento
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_segment_price_comparison(
    p_categoria TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                      AND (p_categoria IS NULL OR categoria = p_categoria)
                      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%')
                    GROUP BY segmento
                ) sub
            ),
            'filtros', json_build_object('categoria', p_categoria, 'marca', p_marca, 'color', p_color),
            '_optimizado', true
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 6. rpc_category_price_comparison - Comparacion de precios por categoria
--    MEJORADO: + p_color
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
                            AVG(CASE WHEN descuento > 0 THEN descuento * 100 ELSE 0 END)::numeric, 1
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


-- ============================================================================
-- 7. rpc_subcategory_distribution - Distribucion por subcategoria
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_subcategory_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                'marca', p_marca, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 8. rpc_model_variety - Variedad de modelos, colores, articulos
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_model_variety(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                'marca', p_marca, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM totals t
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 9. rpc_price_distribution - Distribucion por rangos de precio
--    MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_price_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                'marca', p_marca, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 10. rpc_size_distribution - Distribucion de tallas con disponibilidad
--     MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_size_distribution(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL
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
                'marca', p_marca, 'subcategoria', p_subcategoria, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 11. rpc_best_deals - Mejores ofertas del catalogo
--     MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_best_deals(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
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
                'marca', p_marca, 'disponibilidad', p_disponibilidad, 'color', p_color
            ),
            '_optimizado', true
        )
        FROM total t
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 12. rpc_discount_products - Productos con descuento (muestra limitada)
--     MEJORADO: + p_color
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_discount_products(
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_marca TEXT DEFAULT NULL,
    p_subcategoria TEXT DEFAULT NULL,
    p_color TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
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
              AND (p_color IS NULL OR color ILIKE '%' || p_color || '%'))
    INTO total_con_descuento, total_registros
    FROM fact_table
    WHERE precio > precio_final
      AND precio_final > 0
      AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_segmento IS NULL OR segmento = p_segmento)
      AND (p_subcategoria IS NULL OR subcategoria = p_subcategoria)
      AND (p_color IS NULL OR color ILIKE '%' || p_color || '%');

    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo, 'modelo', modelo, 'marca', marca,
            'categoria', categoria, 'segmento', segmento, 'color', color,
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
            'marca', p_marca, 'subcategoria', p_subcategoria, 'color', p_color
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 13. rpc_count_by_filters - Conteo con filtros multiples + estadisticas
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
BEGIN
    SELECT COUNT(*),
           ROUND(AVG(precio_final)::numeric, 0),
           MIN(precio_final),
           MAX(precio_final)
    INTO v_count, v_precio_prom, v_precio_min, v_precio_max
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


-- ============================================================================
-- 14. rpc_search_text - Busqueda por texto libre
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_search_text(
    p_search_term TEXT,
    p_marca TEXT DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_segmento TEXT DEFAULT NULL,
    p_disponibilidad TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
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
      AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad);

    SELECT COALESCE(json_agg(row_data), '[]'::json) INTO productos_json
    FROM (
        SELECT json_build_object(
            'articulo', articulo, 'modelo', modelo, 'marca', marca,
            'categoria', categoria, 'subcategoria', subcategoria,
            'segmento', segmento, 'color', color,
            'precio_original', precio, 'precio_final', precio_final,
            'talla', talla, 'disponibilidad', disponibilidad
        ) AS row_data
        FROM fact_table
        WHERE (modelo ILIKE v_term OR articulo ILIKE v_term OR articulo_detalles ILIKE v_term)
          AND (p_marca IS NULL OR marca ILIKE '%' || p_marca || '%')
          AND (p_categoria IS NULL OR categoria = p_categoria)
          AND (p_segmento IS NULL OR segmento = p_segmento)
          AND (p_disponibilidad IS NULL OR disponibilidad = p_disponibilidad)
        ORDER BY precio_final DESC
        LIMIT p_limit
    ) sub;

    RETURN json_build_object(
        'termino_busqueda', p_search_term,
        'total_encontrados', v_total,
        'productos', productos_json,
        'filtros', json_build_object(
            'marca', p_marca, 'categoria', p_categoria,
            'segmento', p_segmento, 'disponibilidad', p_disponibilidad
        ),
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- 15. rpc_search_products_advanced - Busqueda avanzada con todos los filtros
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


-- ============================================================================
-- 16. rpc_article_available_sizes - Tallas disponibles de un articulo especifico
--     Dado un articulo exacto, devuelve las tallas con stock y cuantas
--     unidades (filas) hay de cada talla disponible.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rpc_article_available_sizes(
    p_articulo TEXT
)
RETURNS JSON AS $$
DECLARE
    v_total_disponibles BIGINT;
    v_total_agotados BIGINT;
    tallas_json JSON;
    info_json JSON;
BEGIN
    -- Info basica del articulo (1 scan)
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
    WHERE articulo ILIKE '%' || p_articulo || '%';

    -- Conteos globales
    SELECT
        COUNT(*) FILTER (WHERE disponibilidad = 'available'),
        COUNT(*) FILTER (WHERE disponibilidad != 'available')
    INTO v_total_disponibles, v_total_agotados
    FROM fact_table
    WHERE articulo ILIKE '%' || p_articulo || '%';

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
        GROUP BY talla
    ) sub;

    RETURN json_build_object(
        'info_articulo', info_json,
        'total_disponibles', v_total_disponibles,
        'total_agotados', v_total_agotados,
        'tallas_disponibles', (SELECT COUNT(DISTINCT talla) FROM fact_table
            WHERE articulo ILIKE '%' || p_articulo || '%'
              AND disponibilidad = 'available' AND talla IS NOT NULL),
        'detalle_tallas', tallas_json,
        '_optimizado', true
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- VERIFICACION - Ejecutar para confirmar
-- ============================================================================

-- SELECT rpc_catalog_summary();
-- SELECT rpc_price_analysis(p_marca := 'Nike', p_color := 'Negro');
-- SELECT rpc_discount_analysis(p_categoria := 'Calzado', p_color := 'Blanco');
-- SELECT rpc_availability_analysis(p_color := 'Azul');
-- SELECT rpc_segment_price_comparison(p_color := 'Negro');
-- SELECT rpc_category_price_comparison(p_color := 'Rojo');
-- SELECT rpc_subcategory_distribution(p_categoria := 'Calzado', p_color := 'Negro');
-- SELECT rpc_model_variety(p_marca := 'Nike', p_color := 'Negro');
-- SELECT rpc_price_distribution(p_categoria := 'Calzado', p_color := 'Blanco');
-- SELECT rpc_size_distribution(p_categoria := 'Calzado', p_color := 'Negro');
-- SELECT rpc_best_deals(p_color := 'Negro', p_disponibilidad := 'available', p_limit := 5);
-- SELECT rpc_discount_products(p_marca := 'Adidas', p_color := 'Blanco', p_limit := 5);
-- SELECT rpc_count_by_filters(p_subcategoria := 'Tenis', p_color := 'Negro', p_segmento := 'Hombre');
-- SELECT rpc_search_text('Air Max');
-- SELECT rpc_search_products_advanced(p_subcategoria := 'Tenis', p_color := 'Negro', p_segmento := 'Hombre', p_limit := 3);
-- SELECT rpc_article_available_sizes(p_articulo := 'Superstar');
