import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes') # Tu base de desarrollo

print(f"Sincronizando relaciones en '{DB_NAME}'...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    # 1. Asegurar que todo pilar con responsable_id tenga su registro en usuarios_pilares
    cursor.execute("""
        INSERT IGNORE INTO usuarios_pilares (usuario_id, pilar_id, es_lider)
        SELECT responsable_id, id, TRUE 
        FROM pilares 
        WHERE responsable_id IS NOT NULL;
    """)

    # 2. Asegurar que cualquier usuario con pilar_id histórico también exista en usuarios_pilares
    cursor.execute("""
        INSERT IGNORE INTO usuarios_pilares (usuario_id, pilar_id, es_lider)
        SELECT id, pilar_id, es_responsable 
        FROM usuarios 
        WHERE pilar_id IS NOT NULL;
    """)

    conn.commit()
    print("✅ Sincronización completa. Todos los responsables ya están enlazados a sus pilares.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    conn.close()