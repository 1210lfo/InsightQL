-- ============================================================================
-- InsightQL - Schema de Base de Datos
-- ============================================================================
-- Este archivo documenta la estructura de la tabla fact_table
-- La tabla ya existe en Supabase con datos importados
-- ============================================================================

-- NOTA: La tabla fact_table ya fue creada con los datos del catálogo.
-- Este archivo es solo documentación del schema.

-- ============================================================================
-- ESTRUCTURA DE LA TABLA
-- ============================================================================

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

SUBCATEGORÍAS POR CATEGORÍA:
  Calzado: Tenis, Sandalias, Botas, Mocasines, Botines, Zapatillas, Alpargatas
  Ropa exterior: Chaquetas, Vestidos, Camisas, Pantalones, Sudaderas, Camisetas, 
                 Blusas, Shorts, Faldas, Jeans, Buzos, Blazers, Chalecos, Cardigans
  Ropa interior: Medias, Boxers, Brassieres, Pijamas, Bodies
  Accesorios: Gorras, Cinturones, Bolsos, Billeteras, Bufandas, Gafas

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
