import pymysql
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')

# Nombre de la nueva instancia productiva
DB_PROD_NAME = 'toplabel_pendientes_prod'

print(f"--- PASO 1: Creando la base de datos productiva '{DB_PROD_NAME}' ---")
conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
cursor = conn.cursor()

try:
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_PROD_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE {DB_PROD_NAME};")
    print(f"✅ Base de datos '{DB_PROD_NAME}' creada.")

    print("\n--- PASO 2: Creando estructura de tablas ---")
    
    # 1. Tabla Pilares
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pilares (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(50) NOT NULL UNIQUE,
        descripcion VARCHAR(150) NULL,
        color_identificador VARCHAR(7) DEFAULT '#2563eb',
        responsable_id INT NULL
    );
    """)

    # 2. Tabla Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre_completo VARCHAR(100) NOT NULL,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NULL,
        password_hash VARCHAR(255) NOT NULL,
        rol VARCHAR(20) DEFAULT 'COLABORADOR',
        es_responsable BOOLEAN DEFAULT FALSE,
        pilar_id INT NULL,
        activo BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (pilar_id) REFERENCES pilares(id) ON DELETE SET NULL
    );
    """)

    # Llave foránea de pilares hacia usuarios (para el responsable del pilar)
    cursor.execute("""
    ALTER TABLE pilares ADD CONSTRAINT fk_pilar_responsable 
    FOREIGN KEY (responsable_id) REFERENCES usuarios(id) ON DELETE SET NULL;
    """)

    # 3. Tabla Tareas (Vacía)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tareas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        codigo_folio VARCHAR(20) UNIQUE,
        titulo VARCHAR(200) NOT NULL,
        descripcion TEXT,
        pilar_id INT NOT NULL,
        responsable_id INT NOT NULL,
        creado_por_id INT NOT NULL,
        prioridad ENUM('P0_CRITICA', 'P1_ALTA', 'P2_MEDIA', 'P3_BAJA') DEFAULT 'P2_MEDIA',
        estatus ENUM('PENDIENTE', 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO', 'CANCELADO') DEFAULT 'PENDIENTE',
        fecha_inicio DATE NOT NULL,
        fecha_compromiso DATE NOT NULL,
        fecha_cierre DATE NULL,
        fuente VARCHAR(30) DEFAULT 'DIRECCION',
        pilar_dependencia_id INT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (pilar_id) REFERENCES pilares(id),
        FOREIGN KEY (responsable_id) REFERENCES usuarios(id),
        FOREIGN KEY (creado_por_id) REFERENCES usuarios(id),
        FOREIGN KEY (pilar_dependencia_id) REFERENCES pilares(id)
    );
    """)

    # 4. Tabla Bitácora (Vacía)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bitacora_tareas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tarea_id INT NOT NULL,
        usuario_id INT NOT NULL,
        comentario TEXT NOT NULL,
        tipo ENUM('AVANCE', 'BLOQUEO', 'CAMBIO_ESTATUS', 'NOTA_REUNION') DEFAULT 'AVANCE',
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
    """)
    print("✅ Tablas creadas con éxito.")

    print("\n--- PASO 3: Sembrando datos maestros iniciales ---")
    
    # Inserción del Administrador Principal
    password_hash = generate_password_hash('Dkzo5713.')
    cursor.execute("""
    INSERT INTO usuarios (id, nombre_completo, username, email, password_hash, rol, es_responsable, pilar_id, activo)
    VALUES (1, 'Administrador Principal', 'admin_pilares', NULL, %s, 'DIRECCION', FALSE, NULL, TRUE);
    """, (password_hash,))
    print("✅ Usuario principal 'admin_pilares' registrado con rol DIRECCION.")

    # Inserción de los 8 Pilares iniciales (Sin jefe asignado)
    pilares_iniciales = [
        ('Calidad', 'Aseguramiento, inspección y pruebas de producto terminado', '#059669'),
        ('Diseño', 'Pre-prensa, diseño gráfico y preparación de originales', '#8b5cf6'),
        ('Procesos', 'Estandarización, matriz de habilidades y optimización de flujos', '#4b5563'),
        ('Producción', 'Área de prensas, impresión Flexo y Textil', '#e11d48'),
        ('Recursos Humanos', 'Atracción de talento, capacitación y desarrollo organizacional', '#d97706'),
        ('SAC', 'Servicio y Atención a Clientes, seguimiento a O.P.s y pedidos', '#0891b2'),
        ('Sistemas', 'Infraestructura TI, software de planta y redes', '#2563eb'),
        ('Mantenimiento', 'Mantenimiento preventivo y correctivo de maquinaria de planta', '#ea580c')
    ]

    for nombre, desc, color in pilares_iniciales:
        cursor.execute("""
        INSERT INTO pilares (nombre, descripcion, color_identificador, responsable_id)
        VALUES (%s, %s, %s, NULL);
        """, (nombre, desc, color))

    print("✅ Los 8 Pilares iniciales creados sin jefes asignados.")
    print("✅ Lista de tareas y bitácoras inicializadas en blanco (0 registros).")

    conn.commit()
    print("\n🎉 ¡BASE DE DATOS PRODUCTIVA CONFIGURADA CON ÉXITO!")

except Exception as e:
    conn.rollback()
    print(f"❌ Error durante la creación: {e}")
finally:
    conn.close()