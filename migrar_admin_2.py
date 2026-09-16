import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes')

print("Aplicando ajustes de Fase 2 en MySQL...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    # 1. Permitir que email sea NULL (pero manteniendo el índice único)
    cursor.execute("ALTER TABLE usuarios MODIFY COLUMN email VARCHAR(100) NULL;")
    print("✅ Columna 'email' modificada para permitir NULL.")

    # 2. Modificar columna rol para soportar 'COLABORADOR'
    cursor.execute("ALTER TABLE usuarios MODIFY COLUMN rol VARCHAR(20) DEFAULT 'COLABORADOR';")
    print("✅ Columna 'rol' actualizada con soporte para 'COLABORADOR'.")

    # 3. Marcar a usuarios que no son responsables como COLABORADOR
    cursor.execute("""
        UPDATE usuarios SET rol = 'COLABORADOR' 
        WHERE es_responsable = FALSE AND rol != 'DIRECCION';
    """)

    conn.commit()
    print("🎉 Migración de Fase 2 completada exitosamente.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error en la migración: {e}")
finally:
    conn.close()