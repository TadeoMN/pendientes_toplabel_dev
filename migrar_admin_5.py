import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes') # Base de desarrollo

print(f"Modificando 'pilar_id' en {DB_NAME} para permitir tareas sin pilar...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tareas MODIFY COLUMN pilar_id INT NULL;")
    conn.commit()
    print("✅ Columna 'pilar_id' ahora permite valores NULL.")
    print("🎉 Migración completada con éxito.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    conn.close()