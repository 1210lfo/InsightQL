"""
Test de conexión a Supabase
"""
from dotenv import load_dotenv
import os

load_dotenv()

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Service role bypasses RLS

print(f'Conectando a: {url}')
print('-' * 50)

try:
    client = create_client(url, key)
    
    # Consultar la tabla "fact_table"
    result = client.table('fact_table').select('*', count='exact').limit(5).execute()
    
    print('✅ Conexión exitosa!')
    print(f'📊 Total de registros: {result.count}')
    print('📋 Primeros 5 registros:')
    for p in result.data[:5]:
        # Mostrar primeros campos
        preview = str(p)[:100]
        print(f"   - {preview}...")
        
    # Mostrar columnas disponibles
    if result.data:
        print('\n📝 Columnas disponibles:')
        for col in sorted(result.data[0].keys()):
            sample = str(result.data[0][col])[:30]
            print(f"   • {col}: {sample}")
            
except Exception as e:
    print(f'❌ Error: {e}')
