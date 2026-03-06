-- ============================================================================
-- InsightQL - SCHEMA DE BASE DE DATOS E ÍNDICES
-- ============================================================================
-- Archivo consolidado: estructura de fact_table + índices optimizados
-- Última actualización: Marzo 2026
-- ============================================================================


-- ============================================================================
-- ESTRUCTURA DE LA TABLA
-- ============================================================================

-- NOTA: La tabla fact_table ya fue creada con los datos del catálogo.
-- Este bloque es documentación del schema.

/*
CREATE TABLE IF NOT EXISTS public.fact_table (
    -- Identificadores
    upc TEXT PRIMARY KEY,                    -- Código único del producto
    sku TEXT,                                -- SKU interno

    -- Información del producto
    articulo TEXT,                           -- Nombre del artículo
    modelo TEXT,                             -- Modelo específico
    articulo_detalles TEXT,                  -- Descripción detallada

    -- Categorización
    marca TEXT NOT NULL,                     -- Marca (Adidas, Nike, etc.)
    categoria TEXT NOT NULL,                 -- Categoría principal (Calzado, Ropa exterior, etc.)
    subcategoria TEXT,                       -- Subcategoría (Tenis, Chaquetas, etc.)
    segmento TEXT NOT NULL,                  -- Público objetivo (Hombre, Mujer, Unisex, Niño, Niña)

    -- Atributos
    color TEXT,                              -- Color del producto
    talla TEXT,                              -- Talla disponible

    -- Precios
    precio NUMERIC(12,2),                    -- Precio original (sin descuento)
    precio_final NUMERIC(12,2),              -- Precio con descuento aplicado
    descuento NUMERIC(5,4),                  -- Porcentaje de descuento (0.00 - 1.00)

    -- Disponibilidad
    disponibilidad TEXT DEFAULT 'available', -- 'available' o 'sold_out'

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
*/


-- ============================================================================
-- VALORES VÁLIDOS POR COLUMNA
-- ============================================================================

/*
CATEGORÍAS:
  - Calzado
  - Ropa exterior
  - Ropa interior
  - Accesorios

SUBCATEGORÍAS POR CATEGORÍA (46 valores reales en BD):
  Calzado: Tenis, Sandalias, Botas, Zapatos
  Ropa exterior: Bermudas, Buzo, Camisa, Camisas, Camiseta, Camisetas, Chaquetas,
                 Conjunto, Crop tops, Crop Tops, Faldas, Jeans, Joggers, Leggins,
                 Overol, Pantalon, Pantalonetas, Polo, Shorts, Sudadera, Top,
                 Vestidos, Vestidos de baño, Bata
  Ropa interior: Bodys, Boxer, Brassier, Calcetines, Panties, Pijamas
  Accesorios: Accesorios, Billeteras, Bisuteria, Bolsos, Bufanda, Cinturon,
              Cinturones, Gorras, Marroquineria, Mochila, Perfumes

SEGMENTOS:
  - Hombre
  - Mujer
  - Unisex
  - Niño
  - Niña

DISPONIBILIDAD:
  - available (disponible)
  - sold_out (agotado)

COLORES COMUNES:
  Blanco, Negro, Azul, Rojo, Verde, Gris, Naranja, Rosa, Café, Amarillo, Morado, Beige

MARCAS (29 en total):
  Adidas, Nike, Puma, Reebok, Under Armour, New Balance, Converse, Vans, Fila,
  Lacoste, Tommy Hilfiger, Guess, Levi's, Diesel, Calvin Klein, Ralph Lauren,
  Michael Kors, Coach, DKNY, Fossil, Swatch, Casio, Ray-Ban, Oakley, Timberland,
  Cat, Skechers, Crocs, Birkenstock
*/

-- ============================================================================
-- ESTADÍSTICAS DEL CATÁLOGO (Febrero 2026)
-- ============================================================================

/*
Total de productos: 337,714
Total de marcas: 29
Productos disponibles: ~179,781
Productos con descuento: ~117,234
Precio promedio: $199,597 COP
*/


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

CREATE INDEX IF NOT EXISTS idx_fact_cat_seg ON fact_table(categoria, segmento);
CREATE INDEX IF NOT EXISTS idx_fact_cat_seg_color ON fact_table(categoria, segmento, color);
CREATE INDEX IF NOT EXISTS idx_fact_cat_seg_desc ON fact_table(categoria, segmento, descuento);
CREATE INDEX IF NOT EXISTS idx_fact_seg_precio ON fact_table(segmento, precio_final);
CREATE INDEX IF NOT EXISTS idx_fact_cat_subcat ON fact_table(categoria, subcategoria);
CREATE INDEX IF NOT EXISTS idx_fact_marca_cat_seg ON fact_table(marca, categoria, segmento);
CREATE INDEX IF NOT EXISTS idx_fact_subcat_seg_precio ON fact_table(subcategoria, segmento, precio_final DESC);
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
-- ÍNDICES TRIGRAM (para búsquedas ILIKE '%texto%' eficientes)
-- ============================================================================
-- Requiere: CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- Ejecutar primero en Supabase SQL Editor.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_fact_articulo_trgm
ON fact_table USING gin (articulo gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_fact_marca_trgm
ON fact_table USING gin (marca gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_fact_color_trgm
ON fact_table USING gin (color gin_trgm_ops);


-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'fact_table';
