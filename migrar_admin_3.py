import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes')

print(f"Conectando a {DB_NAME} para aplicar migración de Fase 3...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    # Crear tabla para soportar múltiples pilares de apoyo por tarea
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tareas_dependencias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tarea_id INT NOT NULL,
        pilar_id INT NOT NULL,
        responsable_id INT NULL,
        FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
        FOREIGN KEY (pilar_id) REFERENCES pilares(id) ON DELETE CASCADE,
        FOREIGN KEY (responsable_id) REFERENCES usuarios(id) ON DELETE SET NULL
    );
    """)
    conn.commit()
    print("✅ Tabla 'tareas_dependencias' creada con éxito.")
    print("🎉 Migración de Fase 3 finalizada.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error en la migración: {e}")
finally:
    conn.close()