import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes')

print("Conectando a MySQL para actualizar esquema...")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

try:
    # 1. Agregar columna es_responsable a usuarios si no existe
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'es_responsable';
    """, (DB_NAME,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN es_responsable BOOLEAN DEFAULT FALSE AFTER rol;")
        print("✅ Columna 'es_responsable' agregada a usuarios.")

    # 2. Agregar columna responsable_id a pilares si no existe
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'pilares' AND COLUMN_NAME = 'responsable_id';
    """, (DB_NAME,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE pilares ADD COLUMN responsable_id INT NULL AFTER color_identificador;")
        cursor.execute("ALTER TABLE pilares ADD CONSTRAINT fk_pilar_responsable FOREIGN KEY (responsable_id) REFERENCES usuarios(id) ON DELETE SET NULL;")
        print("✅ Columna 'responsable_id' agregada a pilares.")

    # 3. Marcar a los líderes existentes de Top Label como responsables
    cursor.execute("""
        UPDATE usuarios SET es_responsable = TRUE 
        WHERE username IN ('juan_munoz', 'emmanuel', 'alexis', 'claudia', 'procesos_lider', 'tadeo', 'lu_sac');
    """)
    # Asociar cada pilar a su líder
    cursor.execute("UPDATE pilares SET responsable_id = 2 WHERE id = 1;") # Juan -> Producción
    cursor.execute("UPDATE pilares SET responsable_id = 3 WHERE id = 2;") # Emmanuel -> Diseño
    cursor.execute("UPDATE pilares SET responsable_id = 4 WHERE id = 3;") # Alexis -> Calidad
    cursor.execute("UPDATE pilares SET responsable_id = 5 WHERE id = 4;") # Claudia -> RH
    cursor.execute("UPDATE pilares SET responsable_id = 6 WHERE id = 5;") # Procesos -> Procesos
    cursor.execute("UPDATE pilares SET responsable_id = 7 WHERE id = 6;") # Tadeo -> Sistemas
    cursor.execute("UPDATE pilares SET responsable_id = 8 WHERE id = 7;") # Lu -> SAC

    conn.commit()
    print("🎉 Migración de base de datos completada con éxito.")
except Exception as e:
    conn.rollback()
    print(f"❌ Error en la migración: {e}")
finally:
    conn.close()