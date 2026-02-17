# InsightQL 🔍👗

**Agente Analítico LLM para Catálogo de Moda - Supabase + LangGraph + GitHub Models**

Un sistema de agente conversacional que permite hacer preguntas sobre un catálogo de productos de moda (**337,714 SKUs**, 29 marcas incluyendo Adidas, Nike, Puma y más) en lenguaje natural, obteniendo respuestas fundamentadas y verificables.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        USUARIO                              │
│   "¿Cuál es el precio promedio de calzado para hombre?"    │
└────────────────────────┬────────────────────────────────────┘
                         │ Pregunta natural
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LANGGRAPH ORCHESTRATOR (6 nodos)               │
│  Parse → Clarify → Plan → Execute → Validate → Synthesize  │
└────────────────────────┬────────────────────────────────────┘
                         │ Supabase Direct Queries
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SUPABASE REST API (Direct)                    │
│  • Consultas paginadas (100% de registros)                 │
│  • Service Role Key (bypass RLS)                           │
│  • Funciones analíticas locales                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SUPABASE - Catálogo de Moda                   │
│  • 337,714 registros a nivel SKU-Talla                     │
│  • Productos: Calzado, Ropa, Accesorios                    │
│  • Marcas: 29 (Adidas, Nike, Puma, Reebok, y más)          │
│  • Tabla: fact_table                                        │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Estructura del Catálogo

La base de datos contiene productos de moda con la siguiente estructura:

### Campos Principales

| Campo | Descripción | Ejemplos |
|-------|-------------|----------|
| `marca` | Marca del producto | Adidas |
| `modelo` | Nombre del modelo | Ultraboost, Stan Smith, Copa Mundial |
| `articulo` | Nombre del artículo | Tenis Ultraboost 22 |
| `categoria` | Categoría principal | Calzado, Ropa exterior, Ropa interior, Accesorios |
| `subcategoria` | Subcategoría | Tenis, Zapatos, Camisetas |
| `segmento` | Público objetivo | Mujer, Hombre, Unisex, Niños |
| `color` | Color del producto | Core Black, Cloud White |
| `talla` | Talla del producto | 35, 36, 37, ..., 44 |
| `precio` | Precio original | $449,900 COP |
| `precio_descuento` | Precio con descuento | $359,900 COP |
| `descuento` | Porcentaje de descuento | 20% |
| `precio_final` | Precio de venta final | $359,900 COP |
| `disponibilidad` | Estado de stock | available, out_of_stock |
| `composicion` | Materiales | Cuero, Primeknit, Boost |
| `origen` | País de origen | Vietnam, Alemania |

## ✨ Consultas Soportadas

### Productos
- "Muéstrame los tenis Adidas para mujer"
- "¿Qué modelos de calzado tienen disponibles?"
- "Busca productos Copa Mundial"

### Precios y Descuentos
- "¿Cuál es el precio promedio de calzado Adidas?"
- "Productos con descuento mayor al 30%"
- "Rango de precios de la categoría Ropa"

### Disponibilidad y Tallas
- "¿Qué tallas hay disponibles para Ultraboost?"
- "Productos disponibles en talla 40"
- "Distribución de tallas en calzado femenino"

### Composición y Materiales
- "¿De qué está hecho el Copa Mundial?"
- "Productos con tecnología Boost"
- "Materiales de los tenis Primeknit"

### Análisis y Resúmenes
- "Resumen del catálogo Adidas"
- "Análisis por segmento (Mujer/Hombre/Unisex)"
- "Comparar precios entre categorías"

## 🚀 Inicio Rápido

### 1. Requisitos

- Python 3.11+ (recomendado 3.13)
- [uv](https://docs.astral.sh/uv/) - Gestor de paquetes Python
- Cuenta de Supabase con el catálogo de moda
- API Key de Google Gemini

### 2. Instalación con uv

```bash
# Navegar al proyecto
cd InsightQL

# Instalar dependencias (uv crea el venv automáticamente)
uv sync

# Para desarrollo (incluye pytest, ruff, mypy)
uv sync --dev
```

> **Nota Windows/OneDrive**: Si tienes el proyecto en OneDrive, usa:
> ```bash
> $env:UV_LINK_MODE="copy"; uv sync
> ```

### 3. Configuración

El archivo `.env` ya está configurado con:

```env
GEMINI_API_KEY=AIzaSyDj3QRnBWoAnaU1BW8Rv8Aze8cgZHY99DQ
MCP_ENDPOINT=https://mcp.supabase.com/mcp?project_ref=lxbbkdnogzosaiqdilou
SUPABASE_PROJECT_REF=lxbbkdnogzosaiqdilou
```

### 4. Configurar Base de Datos (Opcional)

Si necesitas crear las funciones RPC:

```bash
# Ejecutar en el SQL Editor de Supabase
# Ver archivo sql/fashion_schema.sql
```

### 5. Ejecutar

```bash
# Modo interactivo
uv run python -m src.main --interactive

# Query única
uv run python -m src.main --query "¿Cuáles son los tenis más baratos de Adidas?"

# Con verbose
uv run python -m src.main --query "Muéstrame productos para mujer con descuento" --verbose
```

## 📁 Estructura del Proyecto

```
InsightQL/
├── app.py                # Frontend Streamlit
├── src/
│   ├── agent/
│   │   ├── state.py      # Estado del agente (TypedDict)
│   │   ├── nodes.py      # 6 nodos LangGraph
│   │   └── graph.py      # Definición del grafo
│   ├── mcp/
│   │   ├── client.py     # Cliente HTTP para MCP
│   │   ├── supabase_client.py  # Queries directas a Supabase
│   │   └── tools.py      # Herramientas MCP
│   ├── config.py         # Configuración desde .env
│   ├── security.py       # Funciones de seguridad
│   ├── observability.py  # Tracing con LangSmith
│   └── main.py           # Punto de entrada CLI
├── sql/
│   ├── 01_schema.sql     # Documentación del schema
│   ├── 02_indices.sql    # Índices optimizados
│   └── 03_funciones_rpc.sql  # Funciones RPC finales
├── tests/
│   ├── test_nodes.py
│   ├── test_mcp_tools.py
│   ├── test_integration.py
│   └── test_supabase.py
├── .env.example          # Template de configuración
├── .gitignore            # Archivos ignorados por Git
├── pyproject.toml        # Dependencias (uv)
└── README.md
```

## 🔧 Funciones RPC Disponibles

| Función | Descripción | Parámetros |
|---------|-------------|------------|
| `rpc_catalog_summary` | Resumen general del catálogo | ninguno |
| `rpc_catalog_dimensions` | Valores únicos (marcas, categorías, tallas) | ninguno |
| `rpc_count_products` | Conteo con filtros múltiples | categoria?, segmento?, marca?, color?, subcategoria?, **talla?**, disponibilidad? |
| `rpc_price_analysis` | Análisis de precios | categoria?, segmento?, marca? |
| `rpc_discount_analysis` | Análisis de descuentos | categoria?, segmento?, marca? |
| `rpc_availability_analysis` | Disponibilidad por categoría | categoria?, segmento?, marca? |
| `rpc_segment_price_comparison` | Comparar precios por segmento | categoria?, marca? |
| `rpc_subcategory_distribution` | Distribución por subcategoría | categoria?, segmento?, marca? |
| `rpc_search_products_advanced` | **Búsqueda avanzada** | subcategoria?, color?, **talla?**, disponibilidad?, orden?, limit? |
| `rpc_best_deals` | Mejores ofertas | categoria?, segmento?, marca?, **disponibilidad?**, limit? |
| `rpc_get_tallas` | Tallas disponibles | categoria?, segmento?, subcategoria? |

## 🔍 Ejemplos de Uso

### Consulta Simple
```bash
uv run python -m src.main --query "Dame un resumen del catálogo"
```

**Respuesta:**
> El catálogo cuenta con **337,714 productos** de **29 marcas**, distribuidos en:
> - **179,781 productos** disponibles
> - **117,234 productos** con descuento
> - Precio promedio: **$199,597 COP**

### Consulta por Marca
```bash
uv run python -m src.main --query "¿Cuántos productos tiene Adidas?"
```

**Respuesta:**
> **Adidas** tiene **85,420 productos** en el catálogo:
> - Calzado: **32,150** productos
> - Ropa: **45,890** productos
> - Accesorios: **7,380** productos

### Consulta de Descuentos
```bash
uv run python -m src.main --query "Mejores ofertas en calzado"
```

**Respuesta:**
> Las mejores ofertas en Calzado:
>
> | Modelo | Precio Original | Precio Final | Ahorro |
> |--------|----------------|--------------|--------|
> | Air Max 90 | $599,900 | **$359,900** | $240,000 |
> | Ultraboost 22 | $799,900 | **$559,900** | $240,000 |
> | Superstar | $449,900 | **$359,900** | 20% |

## 🧪 Tests

```bash
# Ejecutar todos los tests
uv run pytest

# Con coverage
uv run pytest --cov=src

# Tests específicos
uv run pytest tests/test_nodes.py -v
```

## 🔒 Seguridad

InsightQL implementa múltiples capas de seguridad siguiendo las mejores prácticas de "Vibe Coding 101: Security Edition".

### ✅ Medidas Implementadas

| Recomendación | Estado | Implementación |
|---------------|--------|----------------|
| **Allowlist de funciones RPC** | ✅ | Solo funciones autorizadas en `ALLOWED_RPC_FUNCTIONS` |
| **Validación de inputs** | ✅ | `validate_user_input()` en `src/security.py` |
| **Sanitización de errores** | ✅ | `sanitize_error()` - nunca expone datos sensibles |
| **Rate limiting** | ✅ | 30 req/min configurable via `MAX_REQUESTS_PER_MINUTE` |
| **Protección prompt injection** | ✅ | Patrones bloqueados en `BLOCKED_PATTERNS` |
| **Audit logging** | ✅ | `audit_log()` para todas las consultas |
| **Configuración via env vars** | ✅ | Secretos nunca en código fuente |
| **Límites de tokens LLM** | ✅ | `MAX_TOKENS_PER_REQUEST`, `MAX_DAILY_REQUESTS` |

### 🔧 Configuración de Seguridad

```env
# Rate limiting
MAX_REQUESTS_PER_MINUTE=30
MAX_DAILY_REQUESTS=1000

# LLM spending limits
MAX_TOKENS_PER_REQUEST=4000

# Funciones RPC permitidas (allowlist)
ALLOWED_RPC_FUNCTIONS=rpc_catalog_summary,rpc_price_analysis,rpc_best_deals,...
```

### ⚠️ Recomendaciones para Producción

1. **Rotar secretos regularmente**
   - Regenerar `SUPABASE_SERVICE_ROLE_KEY` cada 90 días
   - Rotar `GITHUB_TOKEN` periódicamente
   - Usar un secrets manager (Azure Key Vault, AWS Secrets Manager)

2. **Separar ambientes**
   ```env
   # .env.development
   SUPABASE_URL=https://dev-project.supabase.co
   
   # .env.production
   SUPABASE_URL=https://prod-project.supabase.co
   ```

3. **Habilitar RLS en Supabase**
   - Actualmente usa Service Role Key (bypass RLS)
   - Para multi-tenant: implementar RLS policies

4. **Monitoreo y alertas**
   - Configurar alertas en LangSmith para anomalías
   - Monitorear logs de auditoría (`AUDIT:` en logs)

5. **Backups automatizados**
   - Supabase Pro incluye backups diarios
   - Para datos críticos: backups adicionales a otro provider

### 🛡️ Lo que NO aplica a este proyecto

| Recomendación | Razón |
|---------------|-------|
| CORS configuration | Streamlit maneja internamente |
| Redirect validation | Sin URLs de redirección |
| Webhook signatures | Sin webhooks de pago |
| Password reset limits | Sin sistema de autenticación |
| Mobile API protection | Aplicación web only |
| File upload limits | Sin uploads de archivos |
| GDPR deletion | Herramienta interna, no consumer-facing |

### 📋 Checklist Pre-Deployment

- [ ] Variables de entorno configuradas (no placeholders)
- [ ] `DEBUG=false` en producción
- [ ] Service Role Key almacenado en secrets manager
- [ ] Rate limits ajustados según uso esperado
- [ ] Logs de auditoría habilitados
- [ ] Alertas de LangSmith configuradas
- [ ] Backup verificado

## 📈 Observabilidad

El proyecto incluye tracing con LangSmith:

```bash
# El tracing se habilita automáticamente con la variable de entorno
# LANGCHAIN_TRACING_V2=true (ya configurado en .env)
uv run python -m src.main --interactive
```

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Add: nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para más detalles.

---

**InsightQL** - Consulta tu catálogo de moda con lenguaje natural 🛍️
