"""
LangGraph Nodes Implementation
Each node is a function that takes state and returns updated state.
"""

import logging
import re
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_config
from src.agent.state import AnalyticsAgentState, QueryPlan, RPCCall, Evidence
from src.mcp.tools import (
    get_schema_metadata,
    get_metric_definition,
    validate_query_plan,
    execute_analytics_query,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Setup - GitHub Models (GPT-4o)
# =============================================================================

def get_llm() -> ChatOpenAI:
    """Get configured LLM instance using GitHub Models."""
    config = get_config()
    return ChatOpenAI(
        model=config.github_models.model,
        api_key=config.github_models.token,
        base_url=config.github_models.endpoint,
        temperature=0.1,  # Low temperature for consistent analytical responses
    )


# =============================================================================
# Node 1: PARSE
# =============================================================================

PARSE_SYSTEM_PROMPT = """# ROL
Eres un clasificador de intención especializado en consultas de catálogo de moda.

# CONTEXTO
- Base de datos: ~337,714 productos de moda (29 marcas)
- Campos: marca, categoría, subcategoría, segmento, color, precio, precio_final, talla, disponibilidad

# TAREA
Analiza la pregunta del usuario y extrae 3 elementos:

## 1. INTENT (tipo de consulta)
| Intent | Cuándo usarlo | Ejemplos |
|--------|---------------|----------|
| greeting | Saludos, agradecimientos | "hola", "gracias", "qué tal" |
| product_query | Buscar productos específicos | "muéstrame tenis Adidas", "qué modelos hay" |
| price_query | Precios, descuentos, rangos, conteos con precio | "precio promedio", "cuántos > 300000", "descuentos" |
| availability_query | Stock, tallas, conteos con filtros | "tallas disponibles", "cuántos rojos hay" |
| composition_query | Materiales, origen | "de qué están hechos", "país de origen" |
| comparison | Comparar segmentos/categorías | "diferencia hombre vs mujer", "qué es más caro" |
| catalog_summary | Estadísticas generales | "cuántas marcas", "resumen del catálogo" |
| clarification_needed | Pregunta muy ambigua | "información" (sin especificar qué) |
| unsupported | No relacionado con moda | "clima hoy", "noticias" |

## 2. ENTITIES (entidades detectadas)
Extrae: marcas, categorías (Calzado/Ropa/Accesorios), subcategorías (Tenis/Camisetas), 
segmentos (Hombre/Mujer/Unisex/Niños), colores, modelos, precios, tallas.

## 3. MISSING_PARAMS (parámetros faltantes)
⚠️ REGLA CRÍTICA: Solo incluye parámetros que el usuario NO mencionó.
- Usuario dice "precio > 300000" → precio NO es faltante
- Usuario dice "color negro" → color NO es faltante  
- Consulta completa → missing_params = []

# EJEMPLOS

| Pregunta | Intent | Entities | Missing |
|----------|--------|----------|--------|
| "cuántos tenis negros de hombre > 300000" | price_query | [Tenis, Negro, Hombre, >300000] | [] |
| "calzado mujer color blanco" | availability_query | [Calzado, Mujer, Blanco] | [] |
| "precio promedio" | price_query | [] | [] |
| "productos" | clarification_needed | [] | [categoria/segmento/color] |
| "cuántas marcas hay" | catalog_summary | [] | [] |

# FORMATO DE RESPUESTA
Responde ÚNICAMENTE con JSON válido:
```json
{
  "intent": "<tipo>",
  "entities": ["entidad1", "entidad2"],
  "missing_params": []
}
```
"""


async def parse_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Parse user query to extract intent, entities, and detect missing parameters.
    
    This node:
    1. Sanitizes the user query (anti-prompt injection)
    2. Uses LLM to extract intent and entities
    3. Checks schema to validate entities exist
    4. Identifies missing required parameters
    """
    state["current_node"] = "parse"
    user_query = state["user_query"]
    
    # Anti-prompt injection
    try:
        sanitized_query = _sanitize_user_query(user_query)
    except ValueError as e:
        state["intent"] = "unsupported"
        state["error_message"] = str(e)
        return state
    
    # Get schema context
    schema = await get_schema_metadata(scope="all")
    available_metrics = [m["metric_name"] for m in schema.get("metrics", [])]
    
    # Build context for LLM
    context = f"""
Métricas disponibles: {', '.join(available_metrics)}
Fecha actual: {datetime.now().strftime('%Y-%m-%d')}
Timezone del usuario: {state['user_context'].get('timezone', 'UTC')}
"""
    
    # Call LLM to parse
    llm = get_llm()
    messages = [
        SystemMessage(content=PARSE_SYSTEM_PROMPT),
        HumanMessage(content=f"Contexto:\n{context}\n\nPregunta del usuario: {sanitized_query}"),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        parsed = _extract_json_from_response(response.content)
        
        state["intent"] = parsed.get("intent", "clarification_needed")
        state["entities"] = parsed.get("entities", [])
        state["missing_params"] = parsed.get("missing_params", [])
        
        logger.info(f"Parsed intent: {state['intent']}, entities: {state['entities']}")
        
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        state["intent"] = "clarification_needed"
        state["missing_params"] = ["query"]
        state["error_message"] = str(e)
    
    return state


def _sanitize_user_query(query: str) -> str:
    """
    Sanitize user query to prevent prompt injection attacks.
    
    Raises:
        ValueError: If query contains forbidden patterns
    """
    forbidden_patterns = [
        r"ignore\s+previous",
        r"system\s*:",
        r"\{\{",
        r"ROLE\s*:",
        r"<\|",
        r"</?(system|assistant|user)>",
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError("La consulta contiene patrones no permitidos")
    
    # Limit length
    return query[:500].strip()


def _extract_json_from_response(content: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    import json
    
    # Try to find JSON in code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    
    # Try direct JSON
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    
    return {}


# =============================================================================
# Node 2: CLARIFY
# =============================================================================

CLARIFY_SYSTEM_PROMPT = """# ROL
Eres un asistente amable del catálogo de moda multi-marca.

# TAREA
Genera UNA pregunta de aclaración corta cuando faltan parámetros.

# REGLAS
1. Sé breve y directo (máximo 2 oraciones)
2. Ofrece opciones concretas del catálogo
3. Mantén tono amigable y profesional
4. NO ejecutes consultas, solo pregunta

# OPCIONES DISPONIBLES
- Categorías: Calzado, Ropa exterior, Ropa interior, Accesorios
- Segmentos: Hombre, Mujer, Unisex, Niño, Niña
- Colores: Blanco, Negro, Azul, Rojo, Verde, Gris...
- Marcas populares: Adidas, Nike, Puma, Reebok, Under Armour...

# EJEMPLOS DE RESPUESTA
- "¿Te interesa Calzado, Ropa o Accesorios?"
- "¿Para Hombre, Mujer o Unisex?"
- "¿Buscas alguna marca en particular? (Adidas, Nike, Puma...)"
"""


async def clarify_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Generate clarification question when required parameters are missing.
    """
    state["current_node"] = "clarify"
    
    missing = state.get("missing_params", [])
    entities = state.get("entities", [])
    
    # Build clarification prompt
    prompt = f"""
Pregunta original: {state['user_query']}
Entidades detectadas: {', '.join(entities) if entities else 'ninguna'}
Parámetros faltantes: {', '.join(missing)}

Genera una pregunta de aclaración amable para obtener los parámetros faltantes.
"""
    
    llm = get_llm()
    messages = [
        SystemMessage(content=CLARIFY_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        state["final_answer"] = response.content
    except Exception as e:
        logger.error(f"Clarify failed: {e}")
        # Fallback clarification
        state["final_answer"] = _generate_fallback_clarification(missing)
    
    return state


def _generate_fallback_clarification(missing_params: list[str]) -> str:
    """Generate a simple clarification question for fashion catalog."""
    param_questions = {
        "marca": "¿De qué marca? (ej: Adidas)",
        "categoria": "¿Qué categoría te interesa? (Calzado, Ropa, Accesorios)",
        "segmento": "¿Para qué público? (Mujer, Hombre, Unisex)",
        "modelo": "¿Qué modelo específico? (ej: Ultraboost, Stan Smith, Copa Mundial)",
        "talla": "¿Qué talla buscas?",
        "query": "¿Podrías reformular tu pregunta con más detalle?",
    }
    
    questions = [param_questions.get(p, f"Por favor especifica: {p}") for p in missing_params]
    return "Para ayudarte mejor necesito más información:\n" + "\n".join(f"• {q}" for q in questions)


# =============================================================================
# Node 3: PLAN
# =============================================================================

PLAN_SYSTEM_PROMPT = """# ROL
Eres un planificador de consultas para el catálogo de moda multi-marca (~337,714 productos, 29 marcas).

# TAREA
Convierte la intención del usuario en una llamada a función RPC con parámetros correctos.

# CONCEPTOS CLAVE
| Campo | Descripción |
|-------|-------------|
| precio | Precio original (sin descuento) |
| precio_final | Precio con descuento aplicado |
| ahorro | Diferencia entre precio y precio_final |
| descuento_pct | Porcentaje de descuento (0-100) |
| disponibilidad | "available" o "sold_out" |

# CATÁLOGO DE FUNCIONES

## 🔍 BÚSQUEDA Y PRODUCTOS
| Función | Parámetros | Uso |
|---------|------------|-----|
| get_catalog_summary() | ninguno | Resumen general |
| get_products_by_brand | marca*, categoria?, segmento?, limit? | Productos de una marca |
| get_products_by_category | categoria*, subcategoria?, marca?, segmento? | Productos de categoría |
| search_products | search_term*, marca?, categoria? | Búsqueda por texto libre |

## 💰 PRECIOS Y PRODUCTOS ESPECÍFICOS
| Función | Parámetros | Uso |
|---------|------------|-----|
| get_price_analysis | marca?, categoria?, segmento? | Estadísticas de precio |
| **get_top_priced_products** | categoria?, segmento?, marca?, **subcategoria?**, **color?**, **talla?**, **disponibilidad?**, orden?, limit? | **MÁS CAROS/BARATOS con filtros avanzados** |
| count_products_by_price | precio_min?, precio_max?, categoria?, segmento?, marca?, color?, subcategoria?, talla?, disponibilidad? | Conteos con filtros múltiples |
| get_price_distribution | categoria?, segmento?, marca? | Distribución por rangos |
| get_segment_price_comparison | marca?, categoria? | Comparar Hombre vs Mujer vs Unisex |
| get_category_price_comparison | marca?, segmento? | Comparar entre categorías |

## 🏷️ DESCUENTOS
| Función | Parámetros | Uso |
|---------|------------|-----|
| get_discount_analysis | categoria?, segmento?, marca? | % descuento, ahorro total |
| **get_best_deals** | categoria?, segmento?, marca?, **disponibilidad?**, limit? | **Mejores ofertas** (disponibilidad="available" para solo disponibles) |
| get_discount_products | marca?, categoria?, segmento?, limit? | Lista de productos con descuento |

## 📦 INVENTARIO Y TALLAS
| Función | Parámetros | Uso |
|---------|------------|-----|
| get_availability_analysis | categoria?, segmento?, marca? | % disponible/agotado |
| get_available_products | marca?, categoria?, segmento?, **talla?** | Productos disponibles |
| get_size_distribution | marca?, categoria?, segmento? | Distribución de tallas |

## 📊 ANÁLISIS DE CATÁLOGO
| Función | Parámetros | Uso |
|---------|------------|-----|
| get_subcategory_distribution | categoria?, segmento?, marca? | Productos por subcategoría |
| get_model_variety_analysis | categoria?, segmento?, marca? | Modelos/colores únicos |
| get_segment_analysis | marca?, categoria? | Análisis por segmento |

# VALORES VÁLIDOS ⚠️ CRÍTICO
- **Segmentos**: Hombre, Mujer, Unisex, Niño, Niña
- **Categorías**: Calzado, Ropa exterior, Ropa interior, Accesorios

## SUBCATEGORÍAS POR CATEGORÍA:
- **Calzado**: Tenis, Sandalias, Botas, Mocasines, Botines, Zapatillas, Alpargatas
- **Ropa exterior**: Chaquetas, Vestidos, Camisas, Pantalones, Sudaderas, Camisetas, Blusas, Shorts, Faldas, Jeans, Buzos, Blazers, Chalecos, Cardigans
- **Ropa interior**: Medias, Boxers, Brassieres, Pijamas, Bodies
- **Accesorios**: Gorras, Cinturones, Bolsos, Billeteras, Bufandas, Gafas

- **Colores**: Blanco, Negro, Azul, Rojo, Verde, Gris, Naranja, Rosa, Café, Amarillo, Morado, Beige

- **Tallas Ropa**: XS, S, M, L, XL, XXL, XXXL
- **Tallas Calzado**: 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46

# ⚡ EJEMPLOS DE MAPEO

```
"chaqueta más cara para hombre en color azul"
→ get_top_priced_products(subcategoria="Chaquetas", segmento="Hombre", color="Azul", orden="desc", limit=1)

"vestido más barato para mujer"
→ get_top_priced_products(subcategoria="Vestidos", segmento="Mujer", orden="asc", limit=1)

"tenis negros más caros de Nike"
→ get_top_priced_products(subcategoria="Tenis", color="Negro", marca="Nike", orden="desc", limit=5)

"camisetas talla M para hombre disponibles"
→ get_top_priced_products(subcategoria="Camisetas", segmento="Hombre", talla="M", disponibilidad="available")

"tenis talla 42 para hombre"
→ get_top_priced_products(subcategoria="Tenis", segmento="Hombre", talla="42")

"producto más caro"
→ get_top_priced_products(orden="desc", limit=1)

"precio promedio calzado hombre"
→ get_price_analysis(categoria="Calzado", segmento="Hombre")

"cuántos tenis negros de mujer > 300000"
→ count_products_by_price(subcategoria="Tenis", color="Negro", segmento="Mujer", precio_min=300000)

"mejores ofertas de chaquetas"
→ get_best_deals(categoria="Ropa exterior")

"producto con más descuento que esté disponible"
→ get_best_deals(disponibilidad="available", limit=1)

"comparar precios hombre vs mujer"
→ get_segment_price_comparison()

"qué tallas hay de camisetas"
→ get_size_distribution(categoria="Ropa exterior")
```

# FORMATO DE RESPUESTA
Responde ÚNICAMENTE con JSON válido:
```json
{
  "rpc_function": "nombre_funcion",
  "parameters": {"param": "valor"},
  "metric": "descripción breve",
  "expects_data": true
}
```
"""


async def plan_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Create query plan mapping intent to RPC functions and parameters.
    """
    state["current_node"] = "plan"
    
    # Build planning context
    context = f"""
Intent: {state['intent']}
Entidades: {state['entities']}
Usuario timezone: {state['user_context'].get('timezone', 'UTC')}
Fecha actual: {datetime.now().strftime('%Y-%m-%d')}

Pregunta original: {state['user_query']}
"""
    
    llm = get_llm()
    messages = [
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        plan_data = _extract_json_from_response(response.content)
        
        # Resolve date references
        plan_data = _resolve_date_references(plan_data, state)
        
        # Validate the plan
        if "steps" in plan_data:
            # Multi-step plan
            for step in plan_data["steps"]:
                validation = await validate_query_plan(
                    step.get("rpc_function", ""),
                    step.get("parameters", {}),
                )
                if not validation.get("valid", False):
                    state["validation_errors_plan"].extend(validation.get("errors", []))
        else:
            # Single step
            validation = await validate_query_plan(
                plan_data.get("rpc_function", ""),
                plan_data.get("parameters", {}),
            )
            if not validation.get("valid", False):
                state["validation_errors_plan"] = validation.get("errors", [])
        
        # Store plan if valid
        if not state.get("validation_errors_plan"):
            state["query_plan"] = QueryPlan(
                metric=plan_data.get("metric", ""),
                filters=plan_data.get("filters", {}),
                groupby=plan_data.get("groupby"),
                timeframe=_extract_timeframe(plan_data),
                rpc_function=plan_data.get("rpc_function", ""),
                parameters=plan_data.get("parameters", {}),
                expects_data=plan_data.get("expects_data", True),
                steps=plan_data.get("steps", []),
            )
            logger.info(f"Created query plan: {state['query_plan']}")
        else:
            state["query_plan"] = None
            logger.warning(f"Plan validation failed: {state['validation_errors_plan']}")
            
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        state["query_plan"] = None
        state["validation_errors_plan"] = [str(e)]
    
    return state


def _resolve_date_references(plan_data: dict[str, Any], state: AnalyticsAgentState) -> dict[str, Any]:
    """Resolve relative date references like 'last_month', 'Q4_2025', etc."""
    now = datetime.now()
    
    # Common date patterns in entities
    entities = state.get("entities", [])
    
    params = plan_data.get("parameters", {})
    
    # Check for Q4, Q3, etc.
    for entity in entities:
        entity_lower = entity.lower()
        
        if "q4" in entity_lower or "q4_2025" in entity_lower:
            params["start_date"] = "2025-10-01"
            params["end_date"] = "2025-12-31"
        elif "q3" in entity_lower:
            params["start_date"] = "2025-07-01"
            params["end_date"] = "2025-09-30"
        elif "último mes" in entity_lower or "last_month" in entity_lower:
            first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day = now.replace(day=1) - timedelta(days=1)
            params["start_date"] = first_day.strftime("%Y-%m-%d")
            params["end_date"] = last_day.strftime("%Y-%m-%d")
        elif "último trimestre" in entity_lower:
            # Calculate last quarter
            current_quarter = (now.month - 1) // 3
            if current_quarter == 0:
                params["start_date"] = f"{now.year - 1}-10-01"
                params["end_date"] = f"{now.year - 1}-12-31"
            else:
                start_month = (current_quarter - 1) * 3 + 1
                params["start_date"] = f"{now.year}-{start_month:02d}-01"
                end_month = current_quarter * 3
                params["end_date"] = f"{now.year}-{end_month:02d}-{_last_day_of_month(now.year, end_month)}"
    
    plan_data["parameters"] = params
    return plan_data


def _last_day_of_month(year: int, month: int) -> int:
    """Get the last day of a month."""
    if month == 12:
        return 31
    next_month = datetime(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day


def _extract_timeframe(plan_data: dict[str, Any]) -> dict[str, str]:
    """Extract timeframe from plan parameters."""
    params = plan_data.get("parameters", {})
    return {
        "start": params.get("start_date", params.get("period_start", "")),
        "end": params.get("end_date", params.get("period_end", "")),
    }


# =============================================================================
# Node 4: EXECUTE
# =============================================================================

async def execute_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Execute RPC queries via MCP and collect results.
    """
    state["current_node"] = "execute"
    
    query_plan = state.get("query_plan")
    if not query_plan:
        state["error_message"] = "No hay plan de consulta válido"
        return state
    
    rpc_calls: list[RPCCall] = []
    raw_results: list[dict[str, Any]] = []
    
    # Handle multi-step plans
    steps = query_plan.get("steps", [])
    if not steps:
        # Single step
        steps = [{
            "rpc_function": query_plan.get("rpc_function", ""),
            "parameters": query_plan.get("parameters", {}),
        }]
    
    # Execute each step
    for step in steps:
        rpc_function = step.get("rpc_function", "")
        parameters = step.get("parameters", {})
        
        if not rpc_function:
            continue
        
        try:
            result = await execute_analytics_query(
                rpc_function=rpc_function,
                parameters=parameters,
            )
            
            rpc_calls.append(RPCCall(
                function=rpc_function,
                params=parameters,
                result=result.get("data", []),
                execution_time_ms=result.get("execution_time_ms", 0),
                query_id=result.get("query_id", ""),
            ))
            
            if result.get("success"):
                raw_results.extend(result.get("data", []))
            else:
                state["error_message"] = result.get("error", "Error desconocido")
                
        except Exception as e:
            logger.error(f"Execution failed for {rpc_function}: {e}")
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["error_message"] = str(e)
            
            # Check if we should retry
            if state["retry_count"] < state.get("max_retries", 2):
                logger.info(f"Retrying... attempt {state['retry_count'] + 1}")
                # State will be re-processed by the graph
    
    state["rpc_calls"] = rpc_calls
    state["raw_results"] = raw_results
    
    return state


# =============================================================================
# Node 5: VALIDATE
# =============================================================================

async def validate_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Validate query results for coherence and data quality (fashion catalog).
    """
    state["current_node"] = "validate"
    
    results = state.get("raw_results", [])
    query_plan = state.get("query_plan")
    errors: list[str] = []
    
    # Check 1: Empty results when data was expected
    if query_plan and query_plan.get("expects_data", True) and len(results) == 0:
        errors.append("No se encontraron productos para los filtros especificados")
    
    # Check 2: Price outliers (for fashion catalog)
    if results:
        for key in ["precio", "precio_final", "precio_promedio"]:
            values = [r.get(key) for r in results if r.get(key) is not None and isinstance(r.get(key), (int, float))]
            if len(values) >= 2:
                med = median(values)
                if med > 0 and max(values) > 10 * med:
                    errors.append(f"Precio anómalo detectado en {key} (revisar datos)")
    
    # Check 3: Discount percentage validation
    if results:
        for key in ["descuento", "porcentaje_disponible"]:
            values = [r.get(key) for r in results if r.get(key) is not None]
            for v in values:
                if isinstance(v, (int, float)) and (v < 0 or v > 100):
                    errors.append(f"Porcentaje fuera de rango en {key}: {v}%")
                    break
    
    # Check 4: Negative prices (shouldn't happen)
    if results:
        for key in ["precio", "precio_final", "precio_descuento"]:
            values = [r.get(key) for r in results if r.get(key) is not None]
            if any(v < 0 for v in values if isinstance(v, (int, float))):
                errors.append(f"Se encontraron precios negativos en {key}")
    
    state["validation_passed"] = len(errors) == 0
    state["validation_errors"] = errors
    
    if errors:
        logger.warning(f"Validation errors: {errors}")
    else:
        logger.info("Validation passed")
    
    return state


# =============================================================================
# Node 6: SYNTHESIZE
# =============================================================================

SYNTHESIZE_SYSTEM_PROMPT = """# ROL
Eres un analista de datos especializado en el catálogo de moda multi-marca.
Tu objetivo es comunicar insights de forma clara, precisa y accionable.

# CONTEXTO
- Catálogo: ~337,714 productos (SKUs únicos) de 29 marcas
- Campos: marca, categoría, subcategoría, segmento, color, talla, precio, precio_final, disponibilidad
- precio = precio original | precio_final = precio con descuento aplicado

# REGLAS DE RESPUESTA

## Estructura
1. **Respuesta directa** - Contesta la pregunta en la primera oración
2. **Datos clave** - Números relevantes con contexto
3. **Insight adicional** - Solo si agrega valor

## Formato
- Números importantes en **negrita**
- Precios: **$424,440 COP** (con separador de miles)
- Porcentajes: **25.3%**
- Cantidades: **4,666 productos**
- Menciona el total analizado para contexto: "(de 337,714 productos)"

## 💡 PARA PRODUCTOS ESPECÍFICOS (más caro/más barato)
**SIEMPRE incluye estos datos del producto:**
- Nombre/artículo del producto
- Marca
- Precio original: $X COP
- Precio final: $Y COP  
- Ahorro/Descuento: $Z COP (X%)
- Color, talla, disponibilidad (si aplica)

## Tono
- Profesional pero accesible
- Conciso (máximo 3-4 párrafos)
- Evita jerga técnica innecesaria

# EJEMPLOS DE RESPUESTA

**Pregunta**: "cuántos tenis negros de hombre hay"
**Respuesta**: 
Hay **2,829 tenis negros para Hombre** en el catálogo.

Representan el **3.5%** del total de productos. El precio promedio es **$389,500 COP**.

---

**Pregunta**: "chaqueta más cara para hombre en azul"
**Respuesta**:
La **chaqueta más cara para Hombre en color Azul** es:

**Chaqueta Performance Elite** de Nike
- 💰 Precio original: **$850,000 COP**
- 🏷️ Precio final: **$680,000 COP**
- 💸 Ahorro: **$170,000 COP (20%)**
- 🎨 Color: Azul | 📦 Disponible

*De 125 chaquetas azules para hombre encontradas*

---

**Pregunta**: "precio promedio de calzado"
**Respuesta**:
El precio promedio de Calzado es **$412,300 COP** (precio final con descuento).

- Precio original promedio: $485,000 COP
- Ahorro promedio: **15%** por descuentos
- Rango: $89,900 - $1,200,000 COP

Análisis basado en **32,456 productos** de calzado.

# RESTRICCIONES
- ❌ NO inventes datos
- ❌ NO uses datos que no estén en los resultados
- ✅ Si falta información, dilo: "No tengo datos sobre..."
- ✅ Si hay errores, menciónalos como advertencia
"""


async def synthesize_node(state: AnalyticsAgentState) -> AnalyticsAgentState:
    """
    Generate natural language response with evidence and recommendations.
    """
    state["current_node"] = "synthesize"
    
    # Handle greeting intent
    if state.get("intent") == "greeting":
        state["final_answer"] = (
            "¡Hola! 👋 Soy **InsightQL**, tu asistente analítico para el catálogo de moda de Adidas.\n\n"
            "Puedo ayudarte con:\n"
            "• 📊 **Resumen del catálogo** - Productos, categorías, segmentos\n"
            "• 💰 **Análisis de precios** - Promedios, descuentos, rangos\n"
            "• 👥 **Segmentación** - Hombre, Mujer, Niños, Unisex\n"
            "• 📏 **Disponibilidad** - Tallas y stock\n\n"
            "¿Qué te gustaría saber sobre el catálogo?"
        )
        return state
    
    # Handle unsupported intent
    if state.get("intent") == "unsupported":
        state["final_answer"] = (
            "Lo siento, no puedo responder a esa pregunta con los datos disponibles del catálogo de moda.\n\n"
            "Puedo ayudarte con preguntas sobre:\n"
            "• Productos por marca, categoría o segmento\n"
            "• Precios y descuentos\n"
            "• Disponibilidad de tallas\n"
            "• Composición y materiales\n"
            "• Análisis del catálogo Adidas"
        )
        return state
    
    # Handle case where we have no plan (validation failed)
    if not state.get("query_plan") and state.get("validation_errors_plan"):
        state["final_answer"] = _generate_limitation_response(state)
        return state
    
    # Handle case where execution failed completely
    if not state.get("raw_results") and state.get("error_message"):
        state["final_answer"] = f"Lo siento, no pude ejecutar la consulta: {state['error_message']}"
        return state
    
    # Handle case where there are no results
    if not state.get("raw_results"):
        state["final_answer"] = "No se encontraron resultados para tu consulta. Intenta con otros filtros."
        return state
    
    # Build synthesis context
    results = state.get("raw_results", [])
    query_plan = state.get("query_plan") or {}
    validation_errors = state.get("validation_errors", [])
    
    context = f"""
Pregunta original: {state['user_query']}
Métrica consultada: {query_plan.get('metric', 'N/A')}
Periodo: {query_plan.get('timeframe', {})}
Resultados obtenidos: {results}
Errores de validación: {validation_errors if validation_errors else 'Ninguno'}
Es data mock: {any(call.get('_mock') for call in state.get('rpc_calls', []))}
"""
    
    llm = get_llm()
    messages = [
        SystemMessage(content=SYNTHESIZE_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        state["final_answer"] = response.content
        
        # Build evidence
        state["evidence"] = Evidence(
            sql_template=_get_sql_template_from_plan(query_plan),
            params_used=query_plan.get("parameters", {}),
            row_count=len(results),
            query_ids=[call.get("query_id", "") for call in state.get("rpc_calls", [])],
        )
        
        # Generate recommendations
        state["recommendations"] = _generate_recommendations(state)
        
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        state["final_answer"] = _generate_fallback_response(state)
    
    return state


def _generate_limitation_response(state: AnalyticsAgentState) -> str:
    """Generate response when plan validation failed."""
    errors = state.get("validation_errors_plan", [])
    return (
        "No puedo procesar esta consulta debido a las siguientes limitaciones:\n"
        + "\n".join(f"• {e}" for e in errors)
        + "\n\n¿Puedo ayudarte con otra consulta?"
    )


def _generate_fallback_response(state: AnalyticsAgentState) -> str:
    """Generate a simple response when LLM synthesis fails."""
    results = state.get("raw_results", [])
    if not results:
        return "No se encontraron datos para tu consulta."
    
    # Simple formatting of results
    lines = ["Resultados de tu consulta:"]
    for r in results[:5]:  # Limit to 5 results
        items = [f"{k}: {v}" for k, v in r.items() if not k.startswith("_")]
        lines.append("• " + ", ".join(items))
    
    if len(results) > 5:
        lines.append(f"... y {len(results) - 5} resultados más.")
    
    return "\n".join(lines)


def _get_sql_template_from_plan(query_plan: dict[str, Any]) -> str:
    """Extract SQL template from query plan for fashion catalog."""
    rpc_function = query_plan.get("rpc_function", "")
    params = query_plan.get("parameters", {})
    
    templates = {
        "get_products_by_brand": "SELECT marca, modelo, articulo, categoria, segmento, precio_final FROM products WHERE marca = $1",
        "get_products_by_category": "SELECT marca, modelo, articulo, subcategoria, segmento, precio_final FROM products WHERE categoria = $1",
        "get_price_analysis": "SELECT $1, AVG(precio_final) as precio_promedio, MIN(precio_final), MAX(precio_final) FROM products GROUP BY $1",
        "get_available_products": "SELECT * FROM products WHERE disponibilidad = 'available' AND marca = $1",
        "get_product_composition": "SELECT marca, modelo, articulo, composicion, origen FROM products WHERE modelo ILIKE $1",
        "get_size_distribution": "SELECT talla, COUNT(*) as total, COUNT(*) FILTER (disponibilidad='available') FROM products GROUP BY talla",
        "get_discount_products": "SELECT marca, modelo, precio, precio_final, descuento FROM products WHERE descuento > $1",
        "get_brand_catalog": "SELECT COUNT(*) as total, COUNT(DISTINCT modelo), AVG(precio_final) FROM products WHERE marca = $1",
        "search_products": "SELECT * FROM products WHERE modelo ILIKE '%$1%' OR articulo ILIKE '%$1%'",
        "get_segment_analysis": "SELECT segmento, COUNT(*) as total, AVG(precio_final) FROM products GROUP BY segmento",
    }
    
    return templates.get(rpc_function, f"RPC: {rpc_function}({params})")


def _generate_recommendations(state: AnalyticsAgentState) -> list[str]:
    """Generate follow-up recommendations based on fashion catalog results."""
    recommendations = []
    results = state.get("raw_results", [])
    intent = state.get("intent", "")
    
    if not results:
        recommendations.append("Intenta buscar con menos filtros o una categoría más amplia")
        return recommendations
    
    # Recommendations based on query type
    if intent == "product_query":
        recommendations.append("¿Te gustaría ver los precios y descuentos de estos productos?")
    
    if intent == "price_query":
        recommendations.append("¿Quieres ver qué productos tienen descuento activo?")
    
    if intent == "availability_query":
        recommendations.append("¿Te gustaría ver la distribución de tallas disponibles?")
    
    if intent == "composition_query":
        recommendations.append("¿Quieres ver otros modelos con materiales similares?")
    
    if intent == "catalog_summary":
        recommendations.append("¿Te gustaría un análisis por segmento (Mujer/Hombre/Unisex)?")
    
    # Check for patterns in data
    for result in results:
        if result.get("descuento", 0) > 30:
            recommendations.append("¡Hay productos con descuentos mayores al 30%! ¿Quieres verlos?")
            break
        if result.get("productos_disponibles", 1) == 0:
            recommendations.append("Algunos productos están agotados. ¿Busco alternativas similares?")
            break
    
    return recommendations[:3]  # Limit to 3 recommendations
