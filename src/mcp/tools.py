"""
MCP Tools Implementation - Fashion Analytics
Herramientas específicas para análisis de catálogo de moda.
"""

import logging
import time
import uuid
from typing import Any

from src.config import get_config
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
) -> dict[str, Any]:
    """
    Obtiene el esquema de la base de datos de productos de moda.
    Usa directamente el schema local.
    
    Args:
        scope: "tables", "metrics", "functions" o "all"
        
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
                {"name": "subcategoria", "type": "TEXT", "description": "Subcategoría (ej: Tenis, Zapatos, Botas, Sandalias, Chaquetas, Vestidos, Camisetas, Jeans, Joggers, Leggins, Bodys, Bisuteria, Polo, Bermudas, Crop tops, Perfumes, Marroquineria, Mochila, Vestidos de baño, etc.)"},
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
            "description": "Análisis de precios (promedio, min, max, descuentos) con filtros completos",
            "parameters": ["marca", "categoria", "segmento", "subcategoria", "color", "talla", "disponibilidad", "articulo"],
            "example": "get_price_analysis(subcategoria='Vestidos', marca='H&M', talla='M')",
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
            "description": "Distribución de tallas disponibles con filtros avanzados",
            "parameters": ["marca", "categoria", "segmento", "subcategoria", "color", "disponibilidad", "articulo"],
            "example": "get_size_distribution('Adidas', 'Calzado', articulo='Superstar')",
        },
        {
            "name": "get_discount_products",
            "description": "Productos con descuento activo con filtros completos",
            "parameters": ["marca", "categoria", "segmento", "subcategoria", "color", "talla", "disponibilidad", "articulo", "limit"],
            "example": "get_discount_products(marca='Adidas', disponibilidad='available', talla='42')",
        },
        {
            "name": "get_brand_catalog",
            "description": "Resumen completo del catálogo de una marca",
            "parameters": ["marca (requerido)"],
            "example": "get_brand_catalog('Adidas')",
        },
        {
            "name": "search_products",
            "description": "Búsqueda por texto en modelo, artículo o composición con filtros avanzados",
            "parameters": ["search_term (requerido)", "marca", "categoria", "segmento", "disponibilidad", "subcategoria", "color", "talla", "limit"],
            "example": "search_products('Air Max', marca='Nike', color='Negro', talla='42')",
        },
        {
            "name": "count_products_by_price",
            "description": "Cuenta productos por rango de precio con todos los filtros",
            "parameters": ["precio_min", "precio_max", "categoria", "segmento", "marca", "color", "subcategoria", "talla", "disponibilidad"],
            "example": "count_products_by_price(500000, null, 'Calzado', 'Hombre')",
        },
        {
            "name": "get_price_distribution",
            "description": "Distribución de productos por rangos de precio con filtros avanzados",
            "parameters": ["categoria", "segmento", "marca", "color", "subcategoria", "disponibilidad"],
            "example": "get_price_distribution('Calzado', subcategoria='Tenis', disponibilidad='available')",
        },
        {
            "name": "get_top_priced_products",
            "description": "Top productos más caros o baratos con filtros avanzados",
            "parameters": ["categoria", "segmento", "marca", "subcategoria", "color", "talla", "disponibilidad", "orden (desc/asc)", "limit"],
            "example": "get_top_priced_products(subcategoria='Chaquetas', segmento='Hombre', color='Azul', orden='desc', limit=1)",
        },
        {
            "name": "get_discount_analysis",
            "description": "Análisis completo de descuentos con filtros extendidos incluyendo talla y artículo",
            "parameters": ["categoria", "segmento", "marca", "subcategoria", "color", "talla", "disponibilidad", "articulo"],
            "example": "get_discount_analysis(subcategoria='Tenis', marca='Nike', articulo='Air Max')",
        },
        {
            "name": "get_availability_analysis",
            "description": "Análisis de disponibilidad: % disponible vs agotado, con filtro subcategoría y talla",
            "parameters": ["categoria", "segmento", "marca", "color", "subcategoria", "talla"],
            "example": "get_availability_analysis(subcategoria='Tenis', talla='42')",
        },
        {
            "name": "get_segment_price_comparison",
            "description": "Compara precios entre segmentos (Hombre vs Mujer vs Unisex), filtrable por subcategoría",
            "parameters": ["marca", "categoria", "color", "subcategoria"],
            "example": "get_segment_price_comparison(subcategoria='Tenis')",
        },
        {
            "name": "get_category_price_comparison",
            "description": "Compara precios entre categorías (Calzado vs Ropa)",
            "parameters": ["marca", "segmento", "color"],
            "example": "get_category_price_comparison()",
        },
        {
            "name": "get_subcategory_distribution",
            "description": "Distribución de productos por subcategoría, con filtro de disponibilidad",
            "parameters": ["categoria", "segmento", "marca", "color", "disponibilidad"],
            "example": "get_subcategory_distribution('Calzado', disponibilidad='available')",
        },
        {
            "name": "get_model_variety_analysis",
            "description": "Análisis de variedad: modelos únicos, colores, con filtro subcategoría y disponibilidad",
            "parameters": ["categoria", "segmento", "marca", "color", "subcategoria", "disponibilidad"],
            "example": "get_model_variety_analysis(subcategoria='Tenis', marca='Nike')",
        },
        {
            "name": "get_best_deals",
            "description": "Mejores ofertas con filtros avanzados: subcategoría, talla, artículo",
            "parameters": ["categoria", "segmento", "marca", "disponibilidad", "color", "subcategoria", "talla", "articulo", "limit"],
            "example": "get_best_deals(subcategoria='Tenis', articulo='Air Max', disponibilidad='available')",
        },
        {
            "name": "get_article_available_sizes",
            "description": "Tallas disponibles de un artículo específico, con filtro de marca y color para desambiguar",
            "parameters": ["articulo (requerido)", "marca", "color"],
            "example": "get_article_available_sizes('Superstar', marca='Adidas', color='Blanco')",
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
) -> dict[str, Any]:
    """
    Obtiene definición detallada de una métrica o consulta.
    """
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
) -> dict[str, Any]:
    """
    Valida un plan de consulta sin ejecutarlo.
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
) -> dict[str, Any]:
    """
    Ejecuta una consulta analítica sobre el catálogo de moda.
    Usa directamente Supabase REST API + RPC functions.
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
