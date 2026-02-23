-- ============================================================================
-- InsightQL - ELIMINAR FUNCIONES RPC NO UTILIZADAS
-- ============================================================================
-- EJECUTAR EN SUPABASE SQL EDITOR
--
-- Estas funciones existen en la base de datos pero NO son llamadas
-- desde el codigo Python. Se reemplazan por funciones mas optimizadas.
--
-- Fecha: Febrero 2026
-- ============================================================================

-- rpc_catalog_dimensions: No tiene caller en Python.
-- Los valores unicos se obtienen via rpc_catalog_summary + consultas directas.
DROP FUNCTION IF EXISTS public.rpc_catalog_dimensions();

-- rpc_count_products: Reemplazada por rpc_count_by_filters (misma logica, nombre consistente).
DROP FUNCTION IF EXISTS public.rpc_count_products(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);

-- rpc_get_subcategorias: No tiene caller en Python.
-- La distribucion de subcategorias se obtiene via rpc_subcategory_distribution.
DROP FUNCTION IF EXISTS public.rpc_get_subcategorias();

-- rpc_get_tallas: No tiene caller en Python.
-- La distribucion de tallas se obtiene via rpc_size_distribution.
DROP FUNCTION IF EXISTS public.rpc_get_tallas(TEXT, TEXT, TEXT);


-- ============================================================================
-- VERIFICACION: Listar funciones restantes
-- ============================================================================
-- SELECT routine_name
-- FROM information_schema.routines
-- WHERE routine_schema = 'public'
--   AND routine_name LIKE 'rpc_%'
-- ORDER BY routine_name;
--
-- Deberia devolver exactamente 15 funciones:
--   rpc_availability_analysis
--   rpc_best_deals
--   rpc_catalog_summary
--   rpc_category_price_comparison
--   rpc_count_by_filters
--   rpc_discount_analysis
--   rpc_discount_products
--   rpc_model_variety
--   rpc_price_analysis
--   rpc_price_distribution
--   rpc_search_products_advanced
--   rpc_search_text
--   rpc_segment_price_comparison
--   rpc_size_distribution
--   rpc_subcategory_distribution
