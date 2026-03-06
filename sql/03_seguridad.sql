-- ============================================================================
-- InsightQL - SEGURIDAD (RLS + Políticas)
-- ============================================================================
-- EJECUTAR EN SUPABASE SQL EDITOR
--
-- Habilita Row Level Security y configura políticas de acceso
-- para la tabla fact_table.
--
-- Última actualización: Marzo 2026
-- ============================================================================


-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Habilitar RLS en fact_table
ALTER TABLE public.fact_table ENABLE ROW LEVEL SECURITY;

-- Política de lectura pública (el catálogo es público)
-- Permite SELECT a todos los roles (anon, authenticated, service_role)
CREATE POLICY IF NOT EXISTS "Lectura publica del catalogo"
ON public.fact_table
FOR SELECT
USING (true);


-- ============================================================================
-- NOTAS DE SEGURIDAD
-- ============================================================================

-- 1. Las funciones RPC tienen SET search_path = public (configurado en
--    02_funciones_rpc.sql) para evitar el warning function_search_path_mutable.
--
-- 2. La tabla solo permite SELECT. INSERT/UPDATE/DELETE están bloqueados
--    por defecto cuando RLS está habilitado sin políticas adicionales.
--
-- 3. El service_role_key BYPASSA RLS. Solo usar desde backend.
--    El anon_key respeta RLS → solo lectura.


-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

-- Confirmar que RLS está habilitado:
-- SELECT relname, relrowsecurity
-- FROM pg_class
-- WHERE relname = 'fact_table';
-- → relrowsecurity = true

-- Ver políticas activas:
-- SELECT policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE tablename = 'fact_table';
