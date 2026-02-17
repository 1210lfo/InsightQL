"""
Test de consultas directas a Supabase
"""
import asyncio
from src.mcp.supabase_client import count_brands, get_catalog_summary, get_price_analysis

async def test():
    print('Probando conexión directa a Supabase...')
    print('-' * 50)
    
    # Contar marcas
    result = await count_brands()
    print(f'Total de marcas: {result["total_marcas"]}')
    print(f'Marcas: {result["marcas"]}')
    print()
    
    # Resumen del catálogo
    summary = await get_catalog_summary()
    print(f'Total registros: {summary["total_registros"]}')
    print(f'Categorías: {summary["categorias"]}')
    print(f'Segmentos: {summary["segmentos"]}')
    print()
    
    # Análisis de precios
    prices = await get_price_analysis()
    print(f'Total productos analizados: {prices.get("total_productos", prices.get("total_registros_analizados", "N/A"))}')
    print(f'Precio promedio: ${prices.get("precio_promedio", 0):,.0f} COP')
    print(f'Precio mínimo: ${prices.get("precio_minimo", 0):,.0f} COP')
    print(f'Precio máximo: ${prices.get("precio_maximo", 0):,.0f} COP')

if __name__ == "__main__":
    asyncio.run(test())
