"""
Verificar marcas únicas en la base de datos
"""
from dotenv import load_dotenv
import os

load_dotenv()

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

print(f'Conectando a: {url}')
print('-' * 50)

client = create_client(url, key)

# Contar total
count_result = client.table('fact_table').select('*', count='exact').limit(1).execute()
print(f"Total de registros en fact_table: {count_result.count}")

# Paginar para obtener todas las marcas
print("Paginando para obtener todas las marcas...")
all_marcas = set()
offset = 0
page_size = 1000

while True:
    result = client.table('fact_table').select('marca').range(offset, offset + page_size - 1).execute()
    if not result.data:
        break
    for row in result.data:
        if row.get('marca'):
            all_marcas.add(row['marca'])
    offset += page_size
    print(f"  Procesados {offset} registros, marcas encontradas: {len(all_marcas)}")
    if len(result.data) < page_size:
        break

print(f"\n✅ Total de marcas únicas: {len(all_marcas)}")
print("Marcas:")
for m in sorted(all_marcas):
    print(f"  - {m}")
