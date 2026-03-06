"""
Supabase Direct Client
Consultas directas a la base de datos de moda sin depender de MCP.
Todas las funciones paginan para obtener el 100% de los registros.
"""

import logging
from typing import Any

from supabase import create_client, Client

from src.config import get_config

logger = logging.getLogger(__name__)

# Singleton
_supabase_client: Client | None = None

# Configuración de paginación
# NOTA: Supabase tiene un límite de 1000 registros por página por defecto.
# Usamos 1000 para asegurar que se obtengan todos los registros.
PAGE_SIZE = 1000
TABLE_NAME = "fact_table"


def get_supabase_client() -> Client:
    """Get Supabase client using service role key (bypasses RLS)."""
    global _supabase_client
    
    if _supabase_client is None:
        config = get_config()
        url = config.supabase.url
        key = config.supabase.service_role_key
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
        
        _supabase_client = create_client(url, key)
        logger.info(f"Supabase client initialized for {url}")
    
    return _supabase_client


# =============================================================================
# Utilidad de paginación
# =============================================================================

# Columnas que SIEMPRE deben usar match exacto (eq) en vez de parcial (ilike '%val%')
# Esto evita que "Vestidos" matchee "Vestidos de baño", o "Ropa" matchee "Ropa exterior" y "Ropa interior"
_EXACT_MATCH_COLUMNS = {"segmento", "subcategoria", "categoria", "disponibilidad"}


def _paginate_query(
    select_columns: str,
    filters: dict[str, Any] | None = None,
    use_eq_for: list[str] | None = None,
    order_by: str = "upc",
) -> list[dict[str, Any]]:
    """
    Pagina una consulta para obtener TODOS los registros.
    
    IMPORTANTE: Usa ORDER BY para garantizar consistencia en la paginación.
    Sin ORDER BY, los registros pueden duplicarse u omitirse entre páginas.
    
    Args:
        select_columns: Columnas a seleccionar (ej: "precio, marca")
        filters: Diccionario de filtros {columna: valor}
        use_eq_for: Lista de columnas que deben usar eq() en vez de ilike()
        order_by: Columna para ordenar (default: upc - clave primaria única)
    
    Returns:
        Lista con todos los registros
    """
    client = get_supabase_client()
    use_eq_for = set(use_eq_for or []) | _EXACT_MATCH_COLUMNS
    filters = filters or {}
    
    # Asegurar que la columna de ordenamiento esté en la selección
    columns_list = [c.strip() for c in select_columns.split(",")]
    if order_by not in columns_list and "*" not in columns_list:
        select_columns = f"{select_columns}, {order_by}"
    
    # Obtener total (con filtro NOT NULL si aplica)
    count_query = client.table(TABLE_NAME).select("*", count="exact", head=True)
    for col, val in filters.items():
        if val:
            if col in use_eq_for:
                count_query = count_query.eq(col, val)
            else:
                count_query = count_query.ilike(col, f"%{val}%")
    
    total = count_query.execute().count or 0
    
    # Paginar con ORDER BY para consistencia
    all_data = []
    offset = 0
    
    while offset < total:
        query = client.table(TABLE_NAME).select(select_columns)
        for col, val in filters.items():
            if val:
                if col in use_eq_for:
                    query = query.eq(col, val)
                else:
                    query = query.ilike(col, f"%{val}%")
        
        # ORDER BY es crítico para paginación consistente
        result = query.order(order_by).range(offset, offset + PAGE_SIZE - 1).execute()
        
        if not result.data:
            break
        
        all_data.extend(result.data)
        offset += PAGE_SIZE
    
    return all_data


def _get_total_count(filters: dict[str, Any] | None = None, use_eq_for: list[str] | None = None) -> int:
    """Obtiene el conteo total con filtros."""
    client = get_supabase_client()
    use_eq_for = set(use_eq_for or []) | _EXACT_MATCH_COLUMNS
    filters = filters or {}
    
    query = client.table(TABLE_NAME).select("*", count="exact", head=True)
    for col, val in filters.items():
        if val:
            if col in use_eq_for:
                query = query.eq(col, val)
            else:
                query = query.ilike(col, f"%{val}%")
    
    return query.execute().count or 0


# =============================================================================
# Funciones RPC optimizadas (agregación en PostgreSQL)
# =============================================================================

def _call_rpc(function_name: str, params: dict[str, Any] | None = None) -> Any:
    """
    Llama a una función RPC de Supabase.
    Las funciones RPC hacen la agregación en PostgreSQL, no en Python.
    Esto es MUCHO más rápido para grandes volúmenes de datos.
    """
    client = get_supabase_client()
    params = params or {}
    # Filtrar parámetros None
    clean_params = {k: v for k, v in params.items() if v is not None}
    
    try:
        result = client.rpc(function_name, clean_params).execute()
        return result.data
    except Exception as e:
        logger.warning(f"RPC {function_name} failed: {e}, falling back to pagination")
        return None


# =============================================================================
# Funciones de consulta con paginación completa
# =============================================================================

async def count_brands() -> dict[str, Any]:
    """Cuenta el número de marcas únicas en TODA la base de datos."""
    # Intentar RPC primero
    rpc_result = _call_rpc("rpc_catalog_summary")
    if rpc_result:
        return {
            "total_registros_analizados": rpc_result.get("total_productos", 0),
            "total_marcas": rpc_result.get("total_marcas", 0),
            "marcas": rpc_result.get("marcas", []),
        }
    
    # Fallback a paginación
    data = _paginate_query("marca")
    marcas = set(row["marca"] for row in data if row.get("marca"))
    
    return {
        "total_registros_analizados": len(data),
        "total_marcas": len(marcas),
        "marcas": sorted(list(marcas)),
    }


async def get_catalog_summary() -> dict[str, Any]:
    """Resumen general del catálogo COMPLETO - OPTIMIZADO con RPC."""
    # Intentar RPC primero (1 query vs 300+)
    rpc_result = _call_rpc("rpc_catalog_summary")
    if rpc_result:
        return {
            "total_registros": rpc_result.get("total_productos", 0),
            "total_marcas": rpc_result.get("total_marcas", 0),
            "marcas": rpc_result.get("marcas", []),
            "total_categorias": rpc_result.get("total_categorias", 0),
            "categorias": rpc_result.get("categorias", []),
            "total_segmentos": rpc_result.get("total_segmentos", 0),
            "segmentos": rpc_result.get("segmentos", []),
            "total_subcategorias": rpc_result.get("total_subcategorias", 0),
            "total_colores": rpc_result.get("total_colores", 0),
            "precio_promedio": rpc_result.get("precio_promedio", 0),
            "productos_disponibles": rpc_result.get("productos_disponibles", 0),
            "productos_agotados": rpc_result.get("productos_agotados", 0),
            "productos_con_descuento": rpc_result.get("productos_con_descuento", 0),
            "_optimized": True,
        }
    
    # Fallback a paginación (lento)
    client = get_supabase_client()
    
    # Total de registros
    total = _get_total_count()
    
    # Obtener todas las columnas de categorización
    data = _paginate_query("marca, categoria, segmento, subcategoria")
    
    marcas = set(row["marca"] for row in data if row.get("marca"))
    categorias = set(row["categoria"] for row in data if row.get("categoria"))
    segmentos = set(row["segmento"] for row in data if row.get("segmento"))
    subcategorias = set(row["subcategoria"] for row in data if row.get("subcategoria"))
    
    # Conteo por segmento
    conteo_segmentos = {}
    for row in data:
        seg = row.get("segmento", "Sin segmento")
        conteo_segmentos[seg] = conteo_segmentos.get(seg, 0) + 1
    
    # Conteo por categoría
    conteo_categorias = {}
    for row in data:
        cat = row.get("categoria", "Sin categoría")
        conteo_categorias[cat] = conteo_categorias.get(cat, 0) + 1
    
    return {
        "total_registros": total,
        "total_marcas": len(marcas),
        "marcas": sorted(list(marcas)),
        "total_categorias": len(categorias),
        "categorias": sorted(list(categorias)),
        "conteo_por_categoria": conteo_categorias,
        "total_segmentos": len(segmentos),
        "segmentos": sorted(list(segmentos)),
        "conteo_por_segmento": conteo_segmentos,
        "total_subcategorias": len(subcategorias),
    }


async def get_products_by_brand(
    marca: str,
    categoria: str | None = None,
    segmento: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Obtiene productos de una marca específica con conteo total."""
    filters = {"marca": marca}
    if categoria:
        filters["categoria"] = categoria
    if segmento:
        filters["segmento"] = segmento
    
    # Conteo total
    total = _get_total_count(filters, use_eq_for=["segmento"] if segmento else [])
    
    # Muestra limitada
    client = get_supabase_client()
    query = client.table(TABLE_NAME).select("*").ilike("marca", f"%{marca}%")
    if categoria:
        query = query.eq("categoria", categoria)
    if segmento:
        query = query.eq("segmento", segmento)
    
    result = query.limit(limit).execute()
    
    return {
        "marca": marca,
        "filtros": {"categoria": categoria, "segmento": segmento},
        "total_encontrados": total,
        "muestra_limit": limit,
        "productos": result.data,
    }


async def get_products_by_category(
    categoria: str,
    subcategoria: str | None = None,
    marca: str | None = None,
    segmento: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Productos por categoría con conteo total."""
    filters = {"categoria": categoria}
    if subcategoria:
        filters["subcategoria"] = subcategoria
    if marca:
        filters["marca"] = marca
    if segmento:
        filters["segmento"] = segmento
    
    total = _get_total_count(filters, use_eq_for=["segmento"] if segmento else [])
    
    client = get_supabase_client()
    query = client.table(TABLE_NAME).select("*").eq("categoria", categoria)
    if subcategoria:
        query = query.eq("subcategoria", subcategoria)
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if segmento:
        query = query.eq("segmento", segmento)
    
    result = query.limit(limit).execute()
    
    return {
        "categoria": categoria,
        "filtros": {"subcategoria": subcategoria, "marca": marca, "segmento": segmento},
        "total_encontrados": total,
        "muestra_limit": limit,
        "productos": result.data,
    }


async def get_price_analysis(
    marca: str | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    subcategoria: str | None = None,
    color: str | None = None,
    talla: str | None = None,
    disponibilidad: str | None = None,
    articulo: str | None = None,
) -> dict[str, Any]:
    """
    Análisis de precios OPTIMIZADO con RPC.
    precio_final = precio - precio*descuento (ya aplicado en la DB)
    """
    # Intentar RPC primero (1 query vs 300+)
    rpc_result = _call_rpc("rpc_price_analysis", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_talla": talla,
        "p_disponibilidad": disponibilidad,
        "p_articulo": articulo,
    })
    
    if rpc_result:
        return {
            "total_registros": rpc_result.get("total_productos", 0),
            "articulos_unicos": rpc_result.get("articulos_unicos", 0),
            "registros_con_precio": rpc_result.get("total_productos", 0),
            "registros_con_precio_final": rpc_result.get("total_productos", 0),
            "registros_con_descuento": rpc_result.get("productos_con_descuento", 0),
            "precio_original": {
                "promedio": rpc_result.get("precio_original_promedio", 0),
                "minimo": rpc_result.get("precio_minimo", 0),
                "maximo": rpc_result.get("precio_maximo", 0),
            },
            "precio_final": {
                "promedio": rpc_result.get("precio_final_promedio", 0),
                "minimo": rpc_result.get("precio_minimo", 0),
                "maximo": rpc_result.get("precio_maximo", 0),
            },
            "descuento_promedio_porcentaje": rpc_result.get("descuento_promedio_pct", 0),
            "ahorro_total_potencial": rpc_result.get("ahorro_total_potencial", 0),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback a paginación (lento)
    filters = {}
    if marca:
        filters["marca"] = marca
    if categoria:
        filters["categoria"] = categoria
    if segmento:
        filters["segmento"] = segmento
    if subcategoria:
        filters["subcategoria"] = subcategoria
    
    use_eq = ["segmento"] if segmento else []
    
    # Obtener TODOS los registros
    data = _paginate_query("precio, precio_final, descuento", filters, use_eq)
    
    precios = []
    precios_finales = []
    con_descuento = 0
    
    for row in data:
        precio = row.get("precio")
        precio_final = row.get("precio_final")
        descuento = row.get("descuento")
        
        if precio:
            precios.append(float(precio))
        if precio_final:
            precios_finales.append(float(precio_final))
            if descuento and str(descuento).strip() not in ["", "0", "0%", "null", "None"]:
                con_descuento += 1
            elif precio and float(precio_final) < float(precio):
                con_descuento += 1
    
    resultado = {
        "total_registros": len(data),
        "registros_con_precio": len(precios),
        "registros_con_precio_final": len(precios_finales),
        "registros_con_descuento": con_descuento,
    }
    
    if precios:
        resultado["precio_original"] = {
            "promedio": round(sum(precios) / len(precios), 2),
            "minimo": min(precios),
            "maximo": max(precios),
        }
    
    if precios_finales:
        resultado["precio_final"] = {
            "promedio": round(sum(precios_finales) / len(precios_finales), 2),
            "minimo": min(precios_finales),
            "maximo": max(precios_finales),
        }
    
    if precios and precios_finales:
        prom_orig = sum(precios) / len(precios)
        prom_final = sum(precios_finales) / len(precios_finales)
        ahorro = prom_orig - prom_final
        pct_ahorro = (ahorro / prom_orig) * 100 if prom_orig > 0 else 0
        resultado["ahorro"] = {
            "promedio": round(ahorro, 2),
            "porcentaje": round(pct_ahorro, 1),
        }
    
    filtros = []
    if marca:
        filtros.append(f"marca={marca}")
    if categoria:
        filtros.append(f"categoria={categoria}")
    if segmento:
        filtros.append(f"segmento={segmento}")
    resultado["filtros_aplicados"] = filtros if filtros else ["ninguno (catálogo completo)"]
    
    return resultado


async def get_available_products(
    marca: str | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    talla: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Productos disponibles con conteo total."""
    client = get_supabase_client()
    
    # Contar todos los disponibles con filtros
    count_query = client.table(TABLE_NAME).select("*", count="exact", head=True).eq("disponibilidad", "available")
    if marca:
        count_query = count_query.ilike("marca", f"%{marca}%")
    if categoria:
        count_query = count_query.eq("categoria", categoria)
    if segmento:
        count_query = count_query.eq("segmento", segmento)
    if talla:
        count_query = count_query.ilike("talla", f"%{talla}%")
    
    total = count_query.execute().count or 0
    
    # Muestra
    query = client.table(TABLE_NAME).select("*").eq("disponibilidad", "available")
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if categoria:
        query = query.eq("categoria", categoria)
    if segmento:
        query = query.eq("segmento", segmento)
    if talla:
        query = query.ilike("talla", f"%{talla}%")
    
    result = query.limit(limit).execute()
    
    return {
        "total_disponibles": total,
        "filtros": {"marca": marca, "categoria": categoria, "segmento": segmento, "talla": talla},
        "muestra_limit": limit,
        "productos": result.data,
    }


async def search_products(
    search_term: str,
    marca: str | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    disponibilidad: str | None = None,
    limit: int = 10,
    subcategoria: str | None = None,
    color: str | None = None,
    talla: str | None = None,
) -> dict[str, Any]:
    """Búsqueda de productos por texto - OPTIMIZADO con RPC."""
    rpc_result = _call_rpc("rpc_search_text", {
        "p_search_term": search_term,
        "p_marca": marca,
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_disponibilidad": disponibilidad,
        "p_limit": limit,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_talla": talla,
    })
    
    if rpc_result:
        return {
            "termino_busqueda": rpc_result.get("termino_busqueda", search_term),
            "total_encontrados": rpc_result.get("total_encontrados", 0),
            "productos": rpc_result.get("productos", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback a REST (sin conteo total)
    client = get_supabase_client()
    query = client.table(TABLE_NAME).select("*").or_(
        f"modelo.ilike.%{search_term}%,articulo.ilike.%{search_term}%,articulo_detalles.ilike.%{search_term}%"
    )
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if categoria:
        query = query.eq("categoria", categoria)
    result = query.limit(limit).execute()
    
    return {
        "termino_busqueda": search_term,
        "total_encontrados": len(result.data),
        "productos": result.data,
    }


# NOTA: get_segment_analysis fue eliminada - usar get_segment_price_comparison() que usa RPC optimizada


async def get_discount_products(
    marca: str | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    subcategoria: str | None = None,
    color: str | None = None,
    limit: int = 10,
    talla: str | None = None,
    disponibilidad: str | None = None,
    articulo: str | None = None,
) -> dict[str, Any]:
    """Productos con descuento - OPTIMIZADO con RPC."""
    rpc_result = _call_rpc("rpc_discount_products", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_limit": limit,
        "p_talla": talla,
        "p_disponibilidad": disponibilidad,
        "p_articulo": articulo,
    })
    
    if rpc_result:
        return {
            "total_con_descuento": rpc_result.get("total_con_descuento", 0),
            "total_registros_analizados": rpc_result.get("total_registros_analizados", 0),
            "porcentaje_con_descuento": rpc_result.get("porcentaje_con_descuento", 0),
            "muestra_limit": limit,
            "productos": rpc_result.get("productos", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"total_con_descuento": 0, "error": "RPC rpc_discount_products no disponible"}


async def get_size_distribution(
    marca: str | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    subcategoria: str | None = None,
    color: str | None = None,
    disponibilidad: str | None = None,
    articulo: str | None = None,
) -> dict[str, Any]:
    """Distribución de tallas - OPTIMIZADO con RPC."""
    rpc_result = _call_rpc("rpc_size_distribution", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_disponibilidad": disponibilidad,
        "p_articulo": articulo,
    })
    
    if rpc_result:
        return {
            "total_registros_analizados": rpc_result.get("total_registros_analizados", 0),
            "total_tallas_unicas": rpc_result.get("total_tallas_unicas", 0),
            "distribucion": rpc_result.get("distribucion", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"total_tallas_unicas": 0, "error": "RPC rpc_size_distribution no disponible"}


async def get_top_priced_products(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    subcategoria: str | None = None,
    color: str | None = None,
    talla: str | None = None,
    disponibilidad: str | None = None,
    orden: str = "desc",
    limit: int = 5,
) -> dict[str, Any]:
    """
    Obtiene los productos más caros o más baratos CON FILTROS AVANZADOS.
    
    Útil para preguntas como:
    - "¿Cuál es la chaqueta más cara para hombre en color azul?"
    - "¿Cuáles son los 5 tenis más baratos para mujer?"
    - "¿Hay camisetas talla M disponibles para hombre?"
    
    Args:
        categoria: Filtrar por categoría (Calzado, Ropa exterior, etc.)
        segmento: Filtrar por segmento (Hombre, Mujer, Unisex, Niño, Niña)
        marca: Filtrar por marca
        subcategoria: Filtrar por subcategoría (Chaquetas, Tenis, Vestidos, etc.)
        color: Filtrar por color
        talla: Filtrar por talla (S, M, L, XL, 38, 40, etc.)
        disponibilidad: Filtrar por disponibilidad ("available" o "sold_out")
        orden: "desc" para más caros, "asc" para más baratos
        limit: Cantidad de productos a retornar
    """
    # Intentar usar RPC optimizada primero
    rpc_result = _call_rpc("rpc_search_products_advanced", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_talla": talla,
        "p_disponibilidad": disponibilidad,
        "p_orden": orden,
        "p_limit": limit,
    })
    
    if rpc_result:
        return {
            "tipo_consulta": rpc_result.get("tipo_consulta", f"Top {limit} productos"),
            "total_encontrados": rpc_result.get("total_encontrados", 0),
            "productos": rpc_result.get("productos", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback a query directo
    client = get_supabase_client()
    
    query = client.table(TABLE_NAME).select(
        "articulo, modelo, marca, precio, precio_final, descuento, talla, sku, categoria, subcategoria, segmento, color, disponibilidad"
    ).not_.is_("precio_final", "null")
    
    if categoria:
        query = query.eq("categoria", categoria)
    if segmento:
        query = query.eq("segmento", segmento)
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if subcategoria:
        query = query.eq("subcategoria", subcategoria)
    if color:
        query = query.ilike("color", f"%{color}%")
    if talla:
        query = query.ilike("talla", f"%{talla}%")
    if disponibilidad:
        query = query.eq("disponibilidad", disponibilidad)
    
    # Ordenar por precio_final
    query = query.order("precio_final", desc=(orden == "desc")).limit(limit)
    
    result = query.execute()
    
    productos = []
    for p in result.data:
        precio = p.get("precio", 0) or 0
        precio_final = p.get("precio_final", 0) or 0
        ahorro = precio - precio_final if precio and precio_final else 0
        descuento = p.get("descuento", 0) or 0
        productos.append({
            "articulo": p.get("articulo"),
            "modelo": p.get("modelo"),
            "marca": p.get("marca"),
            "precio_original": precio,
            "precio_final": precio_final,
            "ahorro": ahorro,
            "descuento_pct": round(float(descuento) * 100, 1) if descuento else 0,
            "talla": p.get("talla"),
            "categoria": p.get("categoria"),
            "subcategoria": p.get("subcategoria"),
            "segmento": p.get("segmento"),
            "color": p.get("color"),
            "disponibilidad": p.get("disponibilidad"),
        })
    
    tipo = "más caros" if orden == "desc" else "más baratos"
    
    return {
        "tipo_consulta": f"Top {limit} productos {tipo}",
        "filtros": {
            "categoria": categoria,
            "segmento": segmento,
            "marca": marca,
            "subcategoria": subcategoria,
            "color": color,
            "talla": talla,
            "disponibilidad": disponibilidad,
        },
        "total_encontrados": len(productos),
        "productos": productos,
    }


# =============================================================================
# NUEVAS FUNCIONES - Análisis de Negocio Avanzado
# =============================================================================

async def get_discount_analysis(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    subcategoria: str | None = None,
    color: str | None = None,
    talla: str | None = None,
    disponibilidad: str | None = None,
    articulo: str | None = None,
) -> dict[str, Any]:
    """
    Análisis completo de descuentos del catálogo - OPTIMIZADO con RPC.
    
    Responde preguntas como:
    - ¿Cuál es el descuento promedio?
    - ¿Cuántos productos tienen descuento?
    - ¿Cuál es el ahorro total potencial?
    """
    # Intentar RPC primero (1 query vs 300+)
    rpc_result = _call_rpc("rpc_discount_analysis", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_subcategoria": subcategoria,
        "p_color": color,
        "p_talla": talla,
        "p_disponibilidad": disponibilidad,
        "p_articulo": articulo,
    })
    
    if rpc_result:
        return {
            "total_registros": rpc_result.get("total_productos", 0),
            "con_descuento": rpc_result.get("productos_con_descuento", 0),
            "sin_descuento": rpc_result.get("productos_sin_descuento", 0),
            "porcentaje_con_descuento": rpc_result.get("porcentaje_con_descuento", 0),
            "descuento_promedio_porcentaje": rpc_result.get("descuento_promedio_pct", 0),
            "descuento_maximo_porcentaje": rpc_result.get("descuento_maximo_pct", 0),
            "ahorro_total_catalogo": rpc_result.get("ahorro_total", 0),
            "ahorro_promedio_por_producto": rpc_result.get("ahorro_promedio", 0),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback a paginación (lento)
    filters = {}
    if categoria:
        filters["categoria"] = categoria
    if segmento:
        filters["segmento"] = segmento
    if marca:
        filters["marca"] = marca
    if subcategoria:
        filters["subcategoria"] = subcategoria
    
    use_eq = ["segmento"] if segmento else []
    data = _paginate_query("precio, precio_final, descuento, articulo", filters, use_eq)
    
    total_registros = len(data)
    con_descuento = 0
    sin_descuento = 0
    descuentos_porcentaje = []
    ahorro_total = 0
    productos_mayor_descuento = []
    
    for row in data:
        precio = row.get("precio")
        precio_final = row.get("precio_final")
        
        if precio and precio_final and float(precio) > 0:
            precio = float(precio)
            precio_final = float(precio_final)
            
            if precio_final < precio:
                con_descuento += 1
                descuento_pct = ((precio - precio_final) / precio) * 100
                descuentos_porcentaje.append(descuento_pct)
                ahorro = precio - precio_final
                ahorro_total += ahorro
                
                productos_mayor_descuento.append({
                    "articulo": row.get("articulo"),
                    "precio_original": precio,
                    "precio_final": precio_final,
                    "descuento_porcentaje": round(descuento_pct, 1),
                    "ahorro": ahorro,
                })
            else:
                sin_descuento += 1
        else:
            sin_descuento += 1
    
    # Top 10 con mayor descuento
    top_descuentos = sorted(productos_mayor_descuento, key=lambda x: x["descuento_porcentaje"], reverse=True)[:10]
    
    return {
        "total_registros": total_registros,
        "con_descuento": con_descuento,
        "sin_descuento": sin_descuento,
        "porcentaje_con_descuento": round(con_descuento / total_registros * 100, 1) if total_registros > 0 else 0,
        "descuento_promedio_porcentaje": round(sum(descuentos_porcentaje) / len(descuentos_porcentaje), 1) if descuentos_porcentaje else 0,
        "descuento_maximo_porcentaje": round(max(descuentos_porcentaje), 1) if descuentos_porcentaje else 0,
        "descuento_minimo_porcentaje": round(min(descuentos_porcentaje), 1) if descuentos_porcentaje else 0,
        "ahorro_total_catalogo": round(ahorro_total, 0),
        "ahorro_promedio_por_producto": round(ahorro_total / con_descuento, 0) if con_descuento > 0 else 0,
        "top_10_mayor_descuento": top_descuentos,
        "filtros": {"categoria": categoria, "segmento": segmento, "marca": marca},
    }


async def get_availability_analysis(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    color: str | None = None,
    subcategoria: str | None = None,
    talla: str | None = None,
) -> dict[str, Any]:
    """
    Análisis de disponibilidad del catálogo - OPTIMIZADO con RPC.
    
    Responde preguntas como:
    - ¿Qué porcentaje está disponible vs agotado?
    - ¿Qué categoría tiene más agotados?
    - ¿Qué disponibilidad hay de tenis talla 42?
    """
    # Intentar RPC primero (1 query vs 300+)
    rpc_result = _call_rpc("rpc_availability_analysis", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_color": color,
        "p_subcategoria": subcategoria,
        "p_talla": talla,
    })
    
    if rpc_result:
        return {
            "total_registros": rpc_result.get("total_productos", 0),
            "disponibles": rpc_result.get("disponibles", 0),
            "agotados": rpc_result.get("agotados", 0),
            "porcentaje_disponible": rpc_result.get("porcentaje_disponible", 0),
            "porcentaje_agotado": rpc_result.get("porcentaje_agotado", 0),
            "por_categoria": rpc_result.get("por_categoria", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback a paginación (lento)
    filters = {}
    if categoria:
        filters["categoria"] = categoria
    if segmento:
        filters["segmento"] = segmento
    if marca:
        filters["marca"] = marca
    
    use_eq = ["segmento"] if segmento else []
    data = _paginate_query("disponibilidad, categoria, segmento", filters, use_eq)
    
    disponibles = 0
    agotados = 0
    por_categoria = {}
    por_segmento = {}
    
    for row in data:
        disp = row.get("disponibilidad", "").lower()
        cat = row.get("categoria", "Sin categoría")
        seg = row.get("segmento", "Sin segmento")
        
        # Inicializar contadores
        if cat not in por_categoria:
            por_categoria[cat] = {"disponibles": 0, "agotados": 0, "total": 0}
        if seg not in por_segmento:
            por_segmento[seg] = {"disponibles": 0, "agotados": 0, "total": 0}
        
        por_categoria[cat]["total"] += 1
        por_segmento[seg]["total"] += 1
        
        if disp == "available":
            disponibles += 1
            por_categoria[cat]["disponibles"] += 1
            por_segmento[seg]["disponibles"] += 1
        else:
            agotados += 1
            por_categoria[cat]["agotados"] += 1
            por_segmento[seg]["agotados"] += 1
    
    # Calcular porcentajes
    resumen_categorias = []
    for cat, d in por_categoria.items():
        resumen_categorias.append({
            "categoria": cat,
            "total": d["total"],
            "disponibles": d["disponibles"],
            "agotados": d["agotados"],
            "porcentaje_disponible": round(d["disponibles"] / d["total"] * 100, 1) if d["total"] > 0 else 0,
            "porcentaje_agotado": round(d["agotados"] / d["total"] * 100, 1) if d["total"] > 0 else 0,
        })
    
    resumen_segmentos = []
    for seg, d in por_segmento.items():
        resumen_segmentos.append({
            "segmento": seg,
            "total": d["total"],
            "disponibles": d["disponibles"],
            "agotados": d["agotados"],
            "porcentaje_disponible": round(d["disponibles"] / d["total"] * 100, 1) if d["total"] > 0 else 0,
        })
    
    total = len(data)
    return {
        "total_registros": total,
        "disponibles": disponibles,
        "agotados": agotados,
        "porcentaje_disponible": round(disponibles / total * 100, 1) if total > 0 else 0,
        "porcentaje_agotado": round(agotados / total * 100, 1) if total > 0 else 0,
        "por_categoria": sorted(resumen_categorias, key=lambda x: x["porcentaje_agotado"], reverse=True),
        "por_segmento": sorted(resumen_segmentos, key=lambda x: x["total"], reverse=True),
        "filtros": {"categoria": categoria, "segmento": segmento, "marca": marca},
    }


async def get_segment_price_comparison(
    marca: str | None = None,
    categoria: str | None = None,
    color: str | None = None,
    subcategoria: str | None = None,
) -> dict[str, Any]:
    """
    Compara precios entre segmentos (Hombre vs Mujer vs Unisex) - OPTIMIZADO con RPC.
    """
    # Usar RPC existente (1 query en vez de 3 paginaciones completas)
    rpc_result = _call_rpc("rpc_segment_price_comparison", {
        "p_categoria": categoria,
        "p_marca": marca,
        "p_color": color,
        "p_subcategoria": subcategoria,
    })
    
    if rpc_result:
        comparacion = rpc_result.get("comparacion_segmentos", [])
        return {
            "comparacion_segmentos": comparacion,
            "segmento_mas_caro": comparacion[0]["segmento"] if comparacion else None,
            "segmento_mas_barato": comparacion[-1]["segmento"] if comparacion else None,
            "diferencia_precio_promedio": (
                comparacion[0].get("precio_final_promedio", 0) - comparacion[-1].get("precio_final_promedio", 0)
            ) if len(comparacion) >= 2 else 0,
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback mínimo (no debería llegar aquí)
    return {"comparacion_segmentos": [], "error": "RPC rpc_segment_price_comparison no disponible"}


async def get_category_price_comparison(
    marca: str | None = None,
    segmento: str | None = None,
    color: str | None = None,
) -> dict[str, Any]:
    """
    Compara precios entre categorías (Calzado vs Ropa, etc.) - OPTIMIZADO con RPC.
    """
    rpc_result = _call_rpc("rpc_category_price_comparison", {
        "p_marca": marca,
        "p_segmento": segmento,
        "p_color": color,
    })
    
    if rpc_result:
        comparacion = rpc_result.get("comparacion_categorias", [])
        return {
            "comparacion_categorias": comparacion,
            "categoria_mas_cara": comparacion[0]["categoria"] if comparacion else None,
            "categoria_mas_barata": comparacion[-1]["categoria"] if comparacion else None,
            "total_categorias": len(comparacion),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"comparacion_categorias": [], "error": "RPC rpc_category_price_comparison no disponible"}


async def get_subcategory_distribution(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    color: str | None = None,
    disponibilidad: str | None = None,
) -> dict[str, Any]:
    """
    Distribución de productos por subcategoría - OPTIMIZADO con RPC.
    """
    rpc_result = _call_rpc("rpc_subcategory_distribution", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_color": color,
        "p_disponibilidad": disponibilidad,
    })
    
    if rpc_result:
        distribucion = rpc_result.get("distribucion", [])
        return {
            "total_registros": rpc_result.get("total_registros", 0),
            "total_subcategorias": len(distribucion),
            "distribucion": distribucion,
            "subcategoria_principal": distribucion[0]["subcategoria"] if distribucion else None,
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"distribucion": [], "error": "RPC rpc_subcategory_distribution no disponible"}


async def get_model_variety_analysis(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    color: str | None = None,
    subcategoria: str | None = None,
    disponibilidad: str | None = None,
) -> dict[str, Any]:
    """
    Análisis de variedad de modelos y colores - OPTIMIZADO con RPC.
    """
    rpc_result = _call_rpc("rpc_model_variety", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_color": color,
        "p_subcategoria": subcategoria,
        "p_disponibilidad": disponibilidad,
    })
    
    if rpc_result:
        return {
            "total_registros": rpc_result.get("total_registros", 0),
            "articulos_unicos": rpc_result.get("articulos_unicos", 0),
            "modelos_colores_unicos": rpc_result.get("modelos_colores_unicos", 0),
            "promedio_variantes_por_articulo": rpc_result.get("promedio_variantes_por_articulo", 0),
            "top_15_articulos_con_mas_variantes": rpc_result.get("top_15_articulos_con_mas_variantes", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"articulos_unicos": 0, "error": "RPC rpc_model_variety no disponible"}


# NOTA: get_price_range_distribution fue eliminada - usar get_price_distribution() que está optimizada


async def get_best_deals(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    disponibilidad: str | None = None,
    color: str | None = None,
    limit: int = 10,
    subcategoria: str | None = None,
    talla: str | None = None,
    articulo: str | None = None,
) -> dict[str, Any]:
    """
    Obtiene los productos con mejor relación descuento/precio.
    Las mejores ofertas del catálogo - OPTIMIZADO con RPC.
    
    Args:
        disponibilidad: "available" para solo disponibles, None para todos
        subcategoria: Filtrar por subcategoría (Tenis, Chaquetas, etc.)
        talla: Filtrar por talla
        articulo: Buscar por nombre de artículo
    """
    # Intentar RPC primero (1 query vs 300+)
    rpc_result = _call_rpc("rpc_best_deals", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_disponibilidad": disponibilidad,
        "p_color": color,
        "p_limit": limit,
        "p_subcategoria": subcategoria,
        "p_talla": talla,
        "p_articulo": articulo,
    })
    
    if rpc_result:
        return {
            "total_productos_con_descuento": rpc_result.get("total_con_descuento", 0),
            "mejores_por_ahorro_absoluto": rpc_result.get("mejores_por_ahorro", []),
            "mejores_por_porcentaje_descuento": rpc_result.get("mejores_por_porcentaje", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    # Fallback ligero: solo REST limitado (NO paginar todo el catálogo)
    client = get_supabase_client()
    query = client.table(TABLE_NAME).select(
        "articulo, modelo, precio, precio_final, descuento, categoria, segmento"
    ).gt("descuento", 0).order("descuento", desc=True).limit(limit)
    if categoria:
        query = query.eq("categoria", categoria)
    if segmento:
        query = query.eq("segmento", segmento)
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if disponibilidad:
        query = query.eq("disponibilidad", disponibilidad)
    result = query.execute()
    data = result.data or []
    
    ofertas = []
    for row in data:
        precio = row.get("precio")
        precio_final = row.get("precio_final")
        if precio and precio_final:
            precio = float(precio)
            precio_final = float(precio_final)
            if precio_final < precio:
                ahorro = precio - precio_final
                ofertas.append({
                    "articulo": row.get("articulo"),
                    "modelo": row.get("modelo"),
                    "categoria": row.get("categoria"),
                    "segmento": row.get("segmento"),
                    "precio_original": precio,
                    "precio_final": precio_final,
                    "ahorro": ahorro,
                    "descuento_porcentaje": round((ahorro / precio) * 100, 1),
                })
    
    return {
        "total_productos_con_descuento": len(ofertas),
        "mejores_por_ahorro_absoluto": ofertas,
        "mejores_por_porcentaje_descuento": sorted(ofertas, key=lambda x: x["descuento_porcentaje"], reverse=True),
        "filtros": {"categoria": categoria, "segmento": segmento, "marca": marca},
        "_note": "Fallback REST limitado, RPC rpc_best_deals no disponible",
    }


async def get_article_available_sizes(
    articulo: str,
    marca: str | None = None,
    color: str | None = None,
) -> dict[str, Any]:
    """
    Tallas disponibles de un artículo específico - OPTIMIZADO con RPC.
    
    Dado un artículo, devuelve qué tallas están disponibles y cuántas
    unidades hay de cada talla con stock.
    
    Responde preguntas como:
    - ¿Qué tallas hay disponibles del Superstar?
    - ¿Cuántas unidades de cada talla quedan del Air Force 1?
    - ¿Qué tallas del Superstar blanco de Adidas hay?
    """
    rpc_result = _call_rpc("rpc_article_available_sizes", {
        "p_articulo": articulo,
        "p_marca": marca,
        "p_color": color,
    })
    
    if rpc_result:
        return {
            "info_articulo": rpc_result.get("info_articulo", {}),
            "total_disponibles": rpc_result.get("total_disponibles", 0),
            "total_agotados": rpc_result.get("total_agotados", 0),
            "tallas_disponibles": rpc_result.get("tallas_disponibles", 0),
            "detalle_tallas": rpc_result.get("detalle_tallas", []),
            "_optimized": True,
        }
    
    # Fallback REST limitado
    client = get_supabase_client()
    query = client.table(TABLE_NAME).select(
        "talla"
    ).ilike(
        "articulo", f"%{articulo}%"
    ).eq(
        "disponibilidad", "available"
    )
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if color:
        query = query.ilike("color", f"%{color}%")
    result = query.execute()
    
    conteo: dict[str, int] = {}
    for row in result.data or []:
        t = row.get("talla")
        if t:
            conteo[t] = conteo.get(t, 0) + 1
    
    detalle = sorted(
        [{"talla": k, "cantidad_disponible": v} for k, v in conteo.items()],
        key=lambda x: x["cantidad_disponible"],
        reverse=True,
    )
    
    return {
        "total_disponibles": sum(conteo.values()),
        "tallas_disponibles": len(conteo),
        "detalle_tallas": detalle,
    }


async def count_products_by_price(
    precio_min: float | None = None,
    precio_max: float | None = None,
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    color: str | None = None,
    subcategoria: str | None = None,
    disponibilidad: str | None = None,
    talla: str | None = None,
    usar_precio_final: bool = True,
) -> dict[str, Any]:
    """
    Cuenta productos con filtros múltiples + estadísticas - OPTIMIZADO con RPC.
    """
    rpc_result = _call_rpc("rpc_count_by_filters", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_color": color,
        "p_subcategoria": subcategoria,
        "p_talla": talla,
        "p_disponibilidad": disponibilidad,
        "p_precio_min": precio_min,
        "p_precio_max": precio_max,
    })
    
    if rpc_result:
        count = rpc_result.get("total_productos", 0)
        return {
            "total_productos": count,
            "articulos_unicos": rpc_result.get("articulos_unicos", 0),
            "precio_promedio": rpc_result.get("precio_promedio", 0),
            "precio_minimo": rpc_result.get("precio_minimo", 0),
            "precio_maximo": rpc_result.get("precio_maximo", 0),
            "filtros": rpc_result.get("filtros", {}),
            "columna_precio": "precio_final",
            "descripcion": f"Se encontraron {count:,} productos que cumplen los criterios",
            "_optimized": True,
        }
    
    # Fallback a REST count
    client = get_supabase_client()
    precio_col = "precio_final" if usar_precio_final else "precio"
    query = client.table(TABLE_NAME).select("*", count="exact", head=True)
    if categoria:
        query = query.eq("categoria", categoria)
    if segmento:
        query = query.eq("segmento", segmento)
    if marca:
        query = query.ilike("marca", f"%{marca}%")
    if color:
        query = query.ilike("color", f"%{color}%")
    if subcategoria:
        query = query.eq("subcategoria", subcategoria)
    if talla:
        query = query.ilike("talla", f"%{talla}%")
    if disponibilidad:
        query = query.eq("disponibilidad", disponibilidad)
    if precio_min is not None:
        query = query.gte(precio_col, precio_min)
    if precio_max is not None:
        query = query.lte(precio_col, precio_max)
    result = query.execute()
    count = result.count or 0
    return {
        "total_productos": count,
        "columna_precio": precio_col,
        "descripcion": f"Se encontraron {count:,} productos que cumplen los criterios",
    }


async def get_price_distribution(
    categoria: str | None = None,
    segmento: str | None = None,
    marca: str | None = None,
    color: str | None = None,
    subcategoria: str | None = None,
    disponibilidad: str | None = None,
) -> dict[str, Any]:
    """
    Distribución de productos por rangos de precio - OPTIMIZADO con RPC.
    1 sola query PostgreSQL en vez de paginar 337k registros.
    """
    rpc_result = _call_rpc("rpc_price_distribution", {
        "p_categoria": categoria,
        "p_segmento": segmento,
        "p_marca": marca,
        "p_color": color,
        "p_subcategoria": subcategoria,
        "p_disponibilidad": disponibilidad,
    })
    
    if rpc_result:
        return {
            "total_productos": rpc_result.get("total_productos", 0),
            "distribucion": rpc_result.get("distribucion", []),
            "filtros": rpc_result.get("filtros", {}),
            "_optimized": True,
        }
    
    return {"total_productos": 0, "distribucion": [], "error": "RPC rpc_price_distribution no disponible"}


# =============================================================================
# Router de consultas
# =============================================================================

async def execute_query(
    function_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta una consulta según el nombre de función.
    Router principal para consultas.
    """
    logger.info(f"Executing Supabase query: {function_name} with params: {parameters}")
    
    try:
        if function_name == "count_brands":
            return await count_brands()
        
        elif function_name == "get_catalog_summary":
            return await get_catalog_summary()
        
        elif function_name == "get_products_by_brand":
            return await get_products_by_brand(
                marca=parameters.get("marca", parameters.get("p_marca", "")),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                limit=parameters.get("limit", 10),
            )
        
        elif function_name == "get_products_by_category":
            return await get_products_by_category(
                categoria=parameters.get("categoria", parameters.get("p_categoria", "")),
                subcategoria=parameters.get("subcategoria"),
                marca=parameters.get("marca"),
                segmento=parameters.get("segmento"),
                limit=parameters.get("limit", 10),
            )
        
        elif function_name == "get_price_analysis":
            return await get_price_analysis(
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                talla=parameters.get("talla"),
                disponibilidad=parameters.get("disponibilidad"),
                articulo=parameters.get("articulo"),
            )
        
        elif function_name == "get_available_products":
            return await get_available_products(
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                talla=parameters.get("talla"),
                limit=parameters.get("limit", 10),
            )
        
        elif function_name == "search_products":
            return await search_products(
                search_term=parameters.get("search_term", parameters.get("p_search_term", "")),
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                disponibilidad=parameters.get("disponibilidad"),
                limit=parameters.get("limit", 10),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                talla=parameters.get("talla"),
            )
        
        elif function_name == "get_product_composition":
            # Reuse search_products targeting composicion/articulo_detalles fields
            return await search_products(
                search_term=parameters.get("modelo", parameters.get("marca", "")),
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                limit=parameters.get("limit", 10),
            )
        
        # get_segment_analysis eliminada - usar get_segment_price_comparison
        
        elif function_name == "get_discount_products":
            return await get_discount_products(
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                limit=parameters.get("limit", 10),
                talla=parameters.get("talla"),
                disponibilidad=parameters.get("disponibilidad"),
                articulo=parameters.get("articulo"),
            )
        
        elif function_name == "get_size_distribution":
            return await get_size_distribution(
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                disponibilidad=parameters.get("disponibilidad"),
                articulo=parameters.get("articulo"),
            )
        
        elif function_name == "get_brand_catalog":
            return await get_catalog_summary()
        
        elif function_name == "count_products_by_price":
            return await count_products_by_price(
                precio_min=parameters.get("precio_min"),
                precio_max=parameters.get("precio_max"),
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
                subcategoria=parameters.get("subcategoria"),
                disponibilidad=parameters.get("disponibilidad"),
                talla=parameters.get("talla"),
                usar_precio_final=parameters.get("usar_precio_final", True),
            )
        
        elif function_name == "get_price_distribution":
            return await get_price_distribution(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
                subcategoria=parameters.get("subcategoria"),
                disponibilidad=parameters.get("disponibilidad"),
            )
        
        elif function_name == "get_top_priced_products":
            return await get_top_priced_products(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                talla=parameters.get("talla"),
                disponibilidad=parameters.get("disponibilidad"),
                orden=parameters.get("orden", "desc"),
                limit=parameters.get("limit", 5),
            )
        
        # ====== NUEVAS FUNCIONES DE ANÁLISIS DE NEGOCIO ======
        
        elif function_name == "get_discount_analysis":
            return await get_discount_analysis(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                subcategoria=parameters.get("subcategoria"),
                color=parameters.get("color"),
                talla=parameters.get("talla"),
                disponibilidad=parameters.get("disponibilidad"),
                articulo=parameters.get("articulo"),
            )
        
        elif function_name == "get_availability_analysis":
            return await get_availability_analysis(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
                subcategoria=parameters.get("subcategoria"),
                talla=parameters.get("talla"),
            )
        
        elif function_name == "get_segment_price_comparison":
            return await get_segment_price_comparison(
                marca=parameters.get("marca"),
                categoria=parameters.get("categoria"),
                color=parameters.get("color"),
                subcategoria=parameters.get("subcategoria"),
            )
        
        elif function_name == "get_category_price_comparison":
            return await get_category_price_comparison(
                marca=parameters.get("marca"),
                segmento=parameters.get("segmento"),
                color=parameters.get("color"),
            )
        
        elif function_name == "get_subcategory_distribution":
            return await get_subcategory_distribution(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
                disponibilidad=parameters.get("disponibilidad"),
            )
        
        elif function_name == "get_model_variety_analysis":
            return await get_model_variety_analysis(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
                subcategoria=parameters.get("subcategoria"),
                disponibilidad=parameters.get("disponibilidad"),
            )
        
        # get_price_range_distribution eliminada - usar get_price_distribution
        
        elif function_name == "get_best_deals":
            return await get_best_deals(
                categoria=parameters.get("categoria"),
                segmento=parameters.get("segmento"),
                marca=parameters.get("marca"),
                disponibilidad=parameters.get("disponibilidad"),
                color=parameters.get("color"),
                limit=parameters.get("limit", 10),
                subcategoria=parameters.get("subcategoria"),
                talla=parameters.get("talla"),
                articulo=parameters.get("articulo"),
            )
        
        elif function_name == "get_article_available_sizes":
            return await get_article_available_sizes(
                articulo=parameters.get("articulo", parameters.get("p_articulo", "")),
                marca=parameters.get("marca"),
                color=parameters.get("color"),
            )
        
        else:
            return {"error": f"Función '{function_name}' no implementada"}
    
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {"error": str(e)}
