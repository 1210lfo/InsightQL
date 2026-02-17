"""Debug script to verify average calculation."""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Parámetros
PAGE_SIZE = 1000
# La consulta SQL usa: LOWER(categoria) LIKE '%calzado%'
# Vamos a usar ilike que es case-insensitive

# Primero verificar las categorías únicas
cat_result = client.table('fact_table').select('categoria').limit(1000).execute()
cats = set(row['categoria'] for row in cat_result.data if row.get('categoria'))
print(f"Categorías encontradas: {cats}")

# Contar usando ILIKE (equivalente a LOWER() LIKE)
count_result = client.table('fact_table').select('*', count='exact', head=True) \
    .eq('segmento', 'Hombre') \
    .ilike('categoria', '%calzado%') \
    .not_.is_('precio_final', 'null') \
    .execute()

total = count_result.count
print(f"\nTotal con ILIKE '%calzado%' y segmento='Hombre': {total}")

# También probar con eq exacto
count_eq = client.table('fact_table').select('*', count='exact', head=True) \
    .eq('segmento', 'Hombre') \
    .eq('categoria', 'Calzado') \
    .not_.is_('precio_final', 'null') \
    .execute()
print(f"Total con eq 'Calzado' y segmento='Hombre': {count_eq.count}")

# Paginar con ORDER BY para consistencia
offset = 0
suma = 0.0
count = 0

while offset < total:
    result = client.table('fact_table').select('precio_final') \
        .eq('segmento', 'Hombre') \
        .ilike('categoria', '%calzado%') \
        .not_.is_('precio_final', 'null') \
        .order('precio_final') \
        .range(offset, offset + PAGE_SIZE - 1) \
        .execute()
    
    if not result.data:
        break
    
    for row in result.data:
        pf = row.get('precio_final')
        if pf is not None:
            suma += float(pf)
            count += 1
    
    offset += PAGE_SIZE

promedio = suma / count if count > 0 else 0
print(f"\n=== RESULTADOS ===")
print(f"Total sumados: {count}")
print(f"Suma total: {suma:,.2f}")
print(f"Promedio Python (ILIKE): {promedio:,.2f}")
print(f"Promedio SQL esperado: 429,127.49")
print(f"Diferencia: {abs(promedio - 429127.49):,.2f}")
