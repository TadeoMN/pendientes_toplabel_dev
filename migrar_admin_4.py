import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes_prod')

print(f"Conectando a {DB_NAME} para migrar a modelo N:M de Pilares...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    # 1. Crear tabla intermedia usuarios_pilares
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios_pilares (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        pilar_id INT NOT NULL,
        es_lider BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_usuario_pilar (usuario_id, pilar_id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (pilar_id) REFERENCES pilares(id) ON DELETE CASCADE
    );
    """)
    print("✅ Tabla 'usuarios_pilares' creada.")

    # 2. Migrar relaciones existentes si las hubiera
    cursor.execute("""
        INSERT IGNORE INTO usuarios_pilares (usuario_id, pilar_id, es_lider)
        SELECT id, pilar_id, es_responsable 
        FROM usuarios 
        WHERE pilar_id IS NOT NULL;
    """)

    conn.commit()
    print("🎉 Migración de múltiples pilares completada exitosamente.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error en migración: {e}")
finally:
    conn.close()