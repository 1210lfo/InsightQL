"""
MCP Tools Implementation - Fashion Analytics
Herramientas específicas para análisis de catálogo de moda.
"""

import logging
import time
import uuid
from typing import Any

from src.config import get_config
from .client import get_mcp_client, MCPClient
from .supabase_client import execute_query as execute_supabase_query

logger = logging.getLogger(__name__)


# =============================================================================
# Cache para metadata
# =============================================================================

_schema_cache: dict[str, Any] = {}
_schema_cache_time: float = 0


# =============================================================================
# Tool 1: get_schema_metadata
# =============================================================================

async def get_schema_metadata(
    scope: str = "all",
    client: MCPClient | None = None,
) -> dict[str, Any]:
    """
    Obtiene el esquema de la base de datos de productos de moda.
    Usa directamente el schema local (MCP deshabilitado).
    
    Args:
        scope: "tables", "metrics", "functions" o "all"
        client: Cliente MCP opcional (no usado)
        
    Returns:
        Metadata del esquema incluyendo columnas y funciones disponibles
    """
    global _schema_cache, _schema_cache_time
    
    config = get_config()
    cache_ttl = config.agent.cache_ttl_seconds
    
    cache_key = f"fashion_schema_{scope}"
    if cache_key in _schema_cache:
        if time.time() - _schema_cache_time < cache_ttl:
            return _schema_cache[cache_key]
    
    # Usar schema local directamente (MCP deshabilitado por errores 400)
    result = _get_fashion_schema(scope)
    _schema_cache[cache_key] = result
    _schema_cache_time = time.time()
    return result


def _get_fashion_schema(scope: str) -> dict[str, Any]:
    """Schema de la base de datos de moda - fact_table."""
    
    tables = [
        {
            "table_name": "fact_table",
            "description": "Catálogo de productos de moda multi-marca (~337,714 registros a nivel SKU-Talla, 29 marcas)",
            "columns": [
                {"name": "upc", "type": "TEXT", "description": "Universal Product Code - PRIMARY KEY (formato: SKU_Color_Talla)"},
                {"name": "canal", "type": "TEXT", "description": "Canal de venta"},
                {"name": "segmento", "type": "TEXT", "description": "Público objetivo: Mujer, Hombre, Unisex"},
                {"name": "categoria", "type": "TEXT", "description": "Categoría principal (ej: Calzado, Ropa)"},
                {"name": "subcategoria", "type": "TEXT", "description": "Subcategoría (ej: Zapatos, Tenis, Camisetas)"},
                {"name": "marca", "type": "TEXT", "description": "Marca del producto (ej: Adidas)"},
                {"name": "modelo", "type": "TEXT", "description": "Nombre/descripción del modelo o color"},
                {"name": "color", "type": "TEXT", "description": "Color del producto"},
                {"name": "sku", "type": "TEXT", "description": "Stock Keeping Unit"},
                {"name": "articulo", "type": "TEXT", "description": "Nombre del artículo (ej: guayos copa mundial)"},
                {"name": "articulo_detalles", "type": "TEXT", "description": "Descripción detallada del producto"},
                {"name": "url sku", "type": "TEXT", "description": "URL del producto en ecommerce"},
                {"name": "talla", "type": "TEXT", "description": "Talla (ej: US H 10 / M 11)"},
                {"name": "precio", "type": "BIGINT", "description": "Precio original en COP"},
                {"name": "precio_descuento", "type": "TEXT", "description": "Precio con descuento (si aplica)"},
                {"name": "disponibilidad", "type": "TEXT", "description": "Estado: available, out_of_stock"},
                {"name": "descuento", "type": "TEXT", "description": "Porcentaje o valor de descuento"},
                {"name": "precio_final", "type": "BIGINT", "description": "Precio final de venta en COP"},
                {"name": "ecommerce_id", "type": "TEXT", "description": "ID en plataforma ecommerce"},
                {"name": "composicion", "type": "TEXT", "description": "Materiales y composición del producto"},
                {"name": "origen", "type": "TEXT", "description": "País de origen/fabricación"},
            ],
        },
    ]
    
    functions = [
        {
            "name": "get_products_by_brand",
            "description": "Obtener productos de una marca específica",
            "parameters": ["marca (requerido)", "categoria", "segmento", "limit"],
            "example": "get_products_by_brand('Adidas', 'Calzado', 'Mujer')",
        },
        {
            "name": "get_products_by_category",
            "description": "Productos por categoría y subcategoría",
            "parameters": ["categoria (requerido)", "subcategoria", "marca", "segmento", "limit"],
            "example": "get_products_by_category('Calzado', 'Tenis')",
        },
        {
            "name": "get_price_analysis",
            "description": "Análisis de precios (promedio, min, max, descuentos) con filtro de subcategoría",
            "parameters": ["group_by: marca|categoria|segmento|subcategoria", "marca", "categoria", "segmento", "subcategoria"],
            "example": "get_price_analysis(subcategoria='Vestidos', marca='H&M')",
        },
        {
            "name": "get_available_products",
            "description": "Productos actualmente disponibles",
            "parameters": ["marca", "categoria", "segmento", "talla", "limit"],
            "example": "get_available_products('Adidas', 'Calzado', 'Mujer', '38')",
        },
        {
            "name": "get_product_composition",
            "description": "Composición y materiales de productos",
            "parameters": ["marca", "modelo", "categoria", "limit"],
            "example": "get_product_composition('Adidas', 'Copa Mundial')",
        },
        {
            "name": "get_size_distribution",
            "description": "Distribución de tallas disponibles",
            "parameters": ["marca", "categoria", "segmento"],
            "example": "get_size_distribution('Adidas', 'Calzado', 'Mujer')",
        },
        {
            "name": "get_discount_products",
            "description": "Productos con descuento activo",
            "parameters": ["marca", "categoria", "segmento", "min_descuento", "limit"],
            "example": "get_discount_products('Adidas', null, null, 20)",
        },
        {
            "name": "get_brand_catalog",
            "description": "Resumen completo del catálogo de una marca",
            "parameters": ["marca (requerido)"],
            "example": "get_brand_catalog('Adidas')",
        },
        {
            "name": "search_products",
            "description": "Búsqueda por texto en modelo, artículo o composición",
            "parameters": ["search_term (requerido)", "marca", "categoria", "segmento", "solo_disponibles", "limit"],
            "example": "search_products('Copa Mundial', 'Adidas')",
        },
        # NOTA: get_segment_analysis eliminada - usar get_segment_price_comparison()
        {
            "name": "count_products_by_price",
            "description": "Cuenta productos por rango de precio con filtros. Ideal para '¿cuántos productos cuestan más de X?'",
            "parameters": ["precio_min (mayor que)", "precio_max (menor o igual)", "categoria", "segmento", "marca", "usar_precio_final (default: true)"],
            "example": "count_products_by_price(500000, null, 'Calzado', 'Hombre') -> Calzado hombre > 500k",
        },
        {
            "name": "get_price_distribution",
            "description": "Distribución de productos por rangos de precio (0-100k, 100k-200k, etc.)",
            "parameters": ["categoria", "segmento", "marca"],
            "example": "get_price_distribution('Calzado', 'Hombre')",
        },
        {
            "name": "get_top_priced_products",
            "description": "Top productos más caros o más baratos CON FILTROS AVANZADOS - usa subcategoria para búsquedas específicas (chaquetas, tenis, vestidos, etc.)",
            "parameters": ["categoria", "segmento", "marca", "subcategoria", "color", "orden (desc/asc)", "limit"],
            "example": "get_top_priced_products(subcategoria='Chaquetas', segmento='Hombre', color='Azul', orden='desc', limit=1)",
        },
        {
            "name": "get_discount_analysis",
            "description": "Análisis completo de descuentos: promedio, total con descuento, ahorro total, top 10 mayor descuento. Soporta filtro de subcategoría.",
            "parameters": ["categoria", "segmento", "marca", "subcategoria"],
            "example": "get_discount_analysis(subcategoria='Tenis', marca='Nike')",
        },
        {
            "name": "get_availability_analysis",
            "description": "Análisis de disponibilidad: % disponible vs agotado, por categoría y segmento",
            "parameters": ["categoria", "segmento", "marca"],
            "example": "get_availability_analysis('Calzado')",
        },
        {
            "name": "get_segment_price_comparison",
            "description": "Compara precios entre segmentos (Hombre vs Mujer vs Unisex)",
            "parameters": [],
            "example": "get_segment_price_comparison()",
        },
        {
            "name": "get_category_price_comparison",
            "description": "Compara precios entre categorías (Calzado vs Ropa)",
            "parameters": [],
            "example": "get_category_price_comparison()",
        },
        {
            "name": "get_subcategory_distribution",
            "description": "Distribución de productos por subcategoría",
            "parameters": ["categoria", "segmento"],
            "example": "get_subcategory_distribution('Calzado', 'Hombre')",
        },
        {
            "name": "get_model_variety_analysis",
            "description": "Análisis de variedad: modelos únicos, colores, artículos con más variantes",
            "parameters": ["categoria", "segmento"],
            "example": "get_model_variety_analysis('Calzado')",
        },
        # NOTA: get_price_range_distribution eliminada - usar get_price_distribution()
        {
            "name": "get_best_deals",
            "description": "Mejores ofertas: productos con mayor ahorro absoluto y mayor % descuento",
            "parameters": ["categoria", "segmento", "limit"],
            "example": "get_best_deals('Calzado', 'Hombre', 10)",
        },
    ]
    
    metrics = [
        {
            "metric_name": "precio_promedio",
            "definition": "Precio final promedio de productos",
            "parameters": ["marca", "categoria", "segmento"],
        },
        {
            "metric_name": "productos_disponibles",
            "definition": "Cantidad de SKUs con disponibilidad = 'available'",
            "parameters": ["marca", "categoria", "segmento"],
        },
        {
            "metric_name": "productos_con_descuento",
            "definition": "Cantidad de productos con descuento > 0",
            "parameters": ["marca", "categoria", "segmento"],
        },
        {
            "metric_name": "distribucion_tallas",
            "definition": "Distribución porcentual de tallas disponibles",
            "parameters": ["marca", "categoria", "segmento"],
        },
        {
            "metric_name": "rango_precios",
            "definition": "Precio mínimo y máximo",
            "parameters": ["marca", "categoria", "segmento"],
        },
        {
            "metric_name": "composicion",
            "definition": "Materiales y composición de productos",
            "parameters": ["marca", "modelo", "categoria"],
        },
    ]
    
    if scope == "tables":
        return {"tables": tables}
    elif scope == "functions":
        return {"functions": functions}
    elif scope == "metrics":
        return {"metrics": metrics}
    return {"tables": tables, "functions": functions, "metrics": metrics}


# =============================================================================
# Tool 2: get_metric_definition
# =============================================================================

async def get_metric_definition(
    metric_name: str,
    client: MCPClient | None = None,
) -> dict[str, Any]:
    """
    Obtiene definición detallada de una métrica o consulta.
    """
    mcp = client or get_mcp_client()
    
    try:
        result = await mcp.call_tool("get_metric_definition", {"metric_name": metric_name})
        return result
    except Exception as e:
        logger.warning(f"MCP metric fetch failed: {e}")
        return _get_fashion_metric_definition(metric_name)


def _get_fashion_metric_definition(metric_name: str) -> dict[str, Any]:
    """Definiciones de métricas para moda."""
    
    definitions = {
        "precio_promedio": {
            "name": "precio_promedio",
            "formula": "ROUND(AVG(precio_final), 2)",
            "interpretation": "Precio promedio de venta. Útil para comparar marcas/categorías.",
            "typical_range": "Varía por categoría. Calzado: $200K-$800K COP",
            "related_metrics": ["rango_precios", "descuento_promedio"],
        },
        "productos_disponibles": {
            "name": "productos_disponibles",
            "formula": "COUNT(DISTINCT sku) WHERE disponibilidad = 'available'",
            "interpretation": "SKUs en stock listos para venta.",
            "typical_range": "Variable según temporada",
            "related_metrics": ["total_productos", "productos_agotados"],
        },
        "productos_con_descuento": {
            "name": "productos_con_descuento",
            "formula": "COUNT(DISTINCT sku) WHERE descuento > 0",
            "interpretation": "Productos en promoción o liquidación.",
            "typical_range": "20-40% del catálogo típicamente",
            "related_metrics": ["descuento_promedio", "ahorro_maximo"],
        },
        "distribucion_tallas": {
            "name": "distribucion_tallas",
            "formula": "GROUP BY talla con porcentaje de disponibilidad",
            "interpretation": "Disponibilidad por talla. Tallas extremas suelen tener menor stock.",
            "typical_range": "Tallas 38-42 mejor disponibilidad",
            "related_metrics": ["productos_disponibles"],
        },
        "composicion": {
            "name": "composicion",
            "formula": "Campo de texto describiendo materiales",
            "interpretation": "Materiales: cuero, sintético, textil, Primeknit, Boost, etc.",
            "typical_range": "Texto descriptivo",
            "related_metrics": ["origen"],
        },
        "rango_precios": {
            "name": "rango_precios",
            "formula": "MIN(precio_final) || ' - ' || MAX(precio_final)",
            "interpretation": "Precio mínimo y máximo en una categoría/marca.",
            "typical_range": "Depende del segmento",
            "related_metrics": ["precio_promedio"],
        },
    }
    
    return definitions.get(metric_name, {
        "name": metric_name,
        "formula": "No disponible",
        "interpretation": f"Métrica '{metric_name}' no encontrada en catálogo de moda",
        "typical_range": "N/A",
        "related_metrics": [],
    })


# =============================================================================
# Tool 3: validate_query_plan
# =============================================================================

async def validate_query_plan(
    rpc_function: str,
    parameters: dict[str, Any] | None = None,
    client: MCPClient | None = None,
) -> dict[str, Any]:
    """
    Valida un plan de consulta sin ejecutarlo.
    Usa validación local (MCP deshabilitado).
    """
    config = get_config()
    errors = []
    params = parameters or {}
    
    # Verificar allowlist
    if rpc_function not in config.agent.allowed_rpc_functions:
        errors.append(f"Función '{rpc_function}' no está permitida")
        return {"valid": False, "errors": errors, "estimated_cost": "unknown"}
    
    # Validaciones específicas por función
    required_params = {
        "get_products_by_brand": ["marca", "p_marca"],
        "get_products_by_category": ["categoria", "p_categoria"],
        "get_brand_catalog": ["marca", "p_marca"],
        "search_products": ["search_term", "p_search_term"],
    }
    
    if rpc_function in required_params:
        has_required = any(p in params or p.replace("p_", "") in params for p in required_params[rpc_function])
        if not has_required:
            param_name = required_params[rpc_function][0].replace("p_", "")
            errors.append(f"Parámetro requerido '{param_name}' faltante para {rpc_function}")
    
    # Validación local (MCP deshabilitado por errores 400)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "estimated_cost": _estimate_fashion_query_cost(rpc_function, params),
    }


def _estimate_fashion_query_cost(rpc_function: str, params: dict[str, Any]) -> str:
    """Estima el costo de una consulta de moda."""
    high_cost = ["search_products", "get_price_analysis"]
    medium_cost = ["get_brand_catalog"]  # get_segment_analysis eliminada
    
    has_filter = any(k in params for k in ["marca", "p_marca", "categoria", "p_categoria"])
    
    if rpc_function in high_cost and not has_filter:
        return "high"
    elif rpc_function in medium_cost:
        return "medium"
    return "low"


# =============================================================================
# Tool 4: execute_analytics_query
# =============================================================================

async def execute_analytics_query(
    rpc_function: str,
    parameters: dict[str, Any] | None = None,
    timeout_ms: int = 30000,
    client: MCPClient | None = None,
) -> dict[str, Any]:
    """
    Ejecuta una consulta analítica sobre el catálogo de moda.
    Usa directamente Supabase (MCP deshabilitado por errores 400 persistentes).
    """
    config = get_config()
    
    # Verificar allowlist
    if rpc_function not in config.agent.allowed_rpc_functions:
        return {
            "success": False,
            "error": f"Función '{rpc_function}' no permitida",
            "data": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "query_id": "",
        }
    
    query_id = f"qry_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    params = parameters or {}
    
    # Usar Supabase directo (MCP deshabilitado por errores 400)
    try:
        supabase_result = await execute_supabase_query(rpc_function, params)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Normalizar resultado a lista para compatibilidad
        if isinstance(supabase_result, dict):
            data = [supabase_result]
            row_count = supabase_result.get("total_encontrados", 
                         supabase_result.get("total_productos", 
                         supabase_result.get("total_marcas",
                         supabase_result.get("total_registros", 1))))
        elif isinstance(supabase_result, list):
            data = supabase_result
            row_count = len(data)
        else:
            data = [{"result": supabase_result}]
            row_count = 1
        
        return {
            "success": True,
            "data": data,
            "row_count": row_count,
            "execution_time_ms": execution_time_ms,
            "query_id": query_id,
        }
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Supabase query failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "row_count": 0,
            "execution_time_ms": execution_time_ms,
            "query_id": query_id,
        }


def _get_mock_fashion_result(rpc_function: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Mock data para desarrollo de fashion analytics."""
    
    mock_results = {
        "get_products_by_brand": [
            {
                "marca": params.get("marca", params.get("p_marca", "Adidas")),
                "modelo": "Ultraboost 22",
                "articulo": "Tenis Ultraboost 22",
                "categoria": "Calzado",
                "subcategoria": "Tenis",
                "segmento": "Unisex",
                "color": "Core Black",
                "precio": 799900,
                "precio_final": 599900,
                "descuento": 25,
                "disponibilidad": "available",
                "tallas_disponibles": ["38", "39", "40", "41", "42"],
            },
            {
                "marca": params.get("marca", params.get("p_marca", "Adidas")),
                "modelo": "Stan Smith",
                "articulo": "Tenis Stan Smith",
                "categoria": "Calzado",
                "subcategoria": "Tenis",
                "segmento": "Unisex",
                "color": "Cloud White",
                "precio": 449900,
                "precio_final": 449900,
                "descuento": 0,
                "disponibilidad": "available",
                "tallas_disponibles": ["36", "37", "38", "39", "40", "41", "42", "43"],
            },
        ],
        
        "get_products_by_category": [
            {
                "marca": "Adidas",
                "modelo": "Forum Low",
                "articulo": "Tenis Forum Low",
                "subcategoria": "Tenis",
                "segmento": "Unisex",
                "color": "Cloud White",
                "precio": 549900,
                "precio_final": 439900,
                "disponibilidad": "available",
                "total_skus": 24,
            },
        ],
        
        "get_price_analysis": [
            {
                "grupo": "Adidas",
                "precio_promedio": 389900.00,
                "precio_minimo": 89900.00,
                "precio_maximo": 899900.00,
                "precio_final_promedio": 329900.00,
                "descuento_promedio": 15.50,
                "total_productos": 5420,
                "productos_con_descuento": 1850,
            },
        ],
        
        "get_product_composition": [
            {
                "marca": "Adidas",
                "modelo": "Copa Mundial",
                "articulo": "Zapatos de fútbol Copa Mundial",
                "articulo_detalles": "El zapato de fútbol más vendido de la historia. Diseño clásico de los años 70.",
                "composicion": "Parte superior: Cuero de canguro premium para máximo control del balón. Suela: Goma natural con tacos de 12mm. Forro: Textil suave con acolchado en el talón.",
                "origen": "Alemania",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "precio_final": 649900.00,
            },
            {
                "marca": "Adidas",
                "modelo": "Ultraboost",
                "articulo": "Tenis para correr Ultraboost",
                "articulo_detalles": "Tecnología Boost para máximo retorno de energía",
                "composicion": "Parte superior: Primeknit 360 transpirable. Media suela: Boost (TPU expandido). Suela: Continental Rubber para tracción en superficies mojadas.",
                "origen": "Vietnam",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "precio_final": 799900.00,
            },
        ],
        
        "get_brand_catalog": [
            {
                "marca": params.get("marca", params.get("p_marca", "Adidas")),
                "total_modelos": 342,
                "total_skus": 5420,
                "categorias": ["Calzado", "Ropa", "Accesorios"],
                "segmentos": ["Mujer", "Hombre", "Unisex", "Niños"],
                "rango_precios": "89900 - 899900",
                "precio_promedio": 329900.00,
                "productos_disponibles": 4250,
                "productos_con_descuento": 1850,
            },
        ],
        
        # get_segment_analysis eliminada - usar get_segment_price_comparison()
        
        "get_discount_products": [
            {
                "marca": "Adidas",
                "modelo": "NMD_R1",
                "articulo": "Tenis NMD_R1",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "color": "Core Black",
                "precio": 599900.00,
                "precio_descuento": 419900.00,
                "precio_final": 419900.00,
                "descuento": 30,
                "ahorro": 180000.00,
                "disponibilidad": "available",
            },
            {
                "marca": "Adidas",
                "modelo": "Superstar",
                "articulo": "Tenis Superstar",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "color": "Cloud White/Core Black",
                "precio": 449900.00,
                "precio_descuento": 359900.00,
                "precio_final": 359900.00,
                "descuento": 20,
                "ahorro": 90000.00,
                "disponibilidad": "available",
            },
        ],
        
        "get_size_distribution": [
            {"talla": "35", "total_productos": 320, "productos_disponibles": 180, "porcentaje_disponible": 56.25},
            {"talla": "36", "total_productos": 420, "productos_disponibles": 280, "porcentaje_disponible": 66.67},
            {"talla": "37", "total_productos": 485, "productos_disponibles": 350, "porcentaje_disponible": 72.16},
            {"talla": "38", "total_productos": 520, "productos_disponibles": 410, "porcentaje_disponible": 78.85},
            {"talla": "39", "total_productos": 510, "productos_disponibles": 395, "porcentaje_disponible": 77.45},
            {"talla": "40", "total_productos": 530, "productos_disponibles": 420, "porcentaje_disponible": 79.25},
            {"talla": "41", "total_productos": 490, "productos_disponibles": 380, "porcentaje_disponible": 77.55},
            {"talla": "42", "total_productos": 450, "productos_disponibles": 320, "porcentaje_disponible": 71.11},
            {"talla": "43", "total_productos": 380, "productos_disponibles": 245, "porcentaje_disponible": 64.47},
            {"talla": "44", "total_productos": 290, "productos_disponibles": 165, "porcentaje_disponible": 56.90},
        ],
        
        "search_products": [
            {
                "marca": "Adidas",
                "modelo": "Copa Mundial",
                "articulo": "Zapatos de fútbol Copa Mundial",
                "articulo_detalles": "El zapato de fútbol más vendido de la historia",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "color": "Black/White",
                "precio_final": 649900.00,
                "disponibilidad": "available",
                "composicion": "Cuero de canguro premium",
                "relevancia": 3.0,
            },
        ],
        
        "get_available_products": [
            {
                "marca": "Adidas",
                "modelo": "Stan Smith",
                "articulo": "Tenis Stan Smith",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "color": "Cloud White",
                "talla": "40",
                "precio": 449900.00,
                "precio_final": 449900.00,
                "disponibilidad": "available",
                "url": "https://www.adidas.co/stan-smith/FX5500.html",
            },
            {
                "marca": "Adidas",
                "modelo": "Gazelle",
                "articulo": "Tenis Gazelle",
                "categoria": "Calzado",
                "segmento": "Unisex",
                "color": "Collegiate Navy",
                "talla": "40",
                "precio": 399900.00,
                "precio_final": 399900.00,
                "disponibilidad": "available",
                "url": "https://www.adidas.co/gazelle/BB5478.html",
            },
        ],
    }
    
    return mock_results.get(rpc_function, [{"message": f"No mock data for {rpc_function}"}])


# =============================================================================
# Utility Functions
# =============================================================================

def clear_schema_cache():
    """Limpiar cache de schema."""
    global _schema_cache, _schema_cache_time
    _schema_cache = {}
    _schema_cache_time = 0


async def get_all_available_functions() -> list[str]:
    """Obtener lista de funciones RPC permitidas."""
    config = get_config()
    return config.agent.allowed_rpc_functions.copy()
