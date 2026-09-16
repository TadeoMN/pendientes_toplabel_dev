import pymysql
import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'toplabel_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes')

print(f"--- PASO 1: Conectando a MySQL ({DB_USER}@{DB_HOST}:{DB_PORT}) ---")
try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"✅ Base de datos '{DB_NAME}' lista.")
    conn.commit()
    conn.close()
except Exception as e:
    print(f"❌ Error al verificar/crear base de datos: {e}")
    print("Tip: Verifica si tu host es 127.0.0.1 o localhost en MySQL.")
    exit(1)

print("\n--- PASO 2: Creando tablas y datos iniciales con SQLAlchemy ---")
from app import create_app, db
from app.models import Pilar, Usuario, Tarea

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Tablas creadas correctamente.")

    # Poblar Pilares si está vacío
    if Pilar.query.count() == 0:
        pilares = [
            Pilar(id=1, nombre='Producción', color_identificador='#e11d48'),
            Pilar(id=2, nombre='Diseño', color_identificador='#8b5cf6'),
            Pilar(id=3, nombre='Calidad', color_identificador='#059669'),
            Pilar(id=4, nombre='Recursos Humanos', color_identificador='#d97706'),
            Pilar(id=5, nombre='Procesos', color_identificador='#4b5563'),
            Pilar(id=6, nombre='Sistemas', color_identificador='#2563eb'),
            Pilar(id=7, nombre='SAC', color_identificador='#0891b2')
        ]
        for p in pilares: 
            db.session.add(p)
        db.session.commit()
        print("✅ 7 Pilares de Top Label registrados.")

    # Poblar Usuarios iniciales
    if Usuario.query.count() == 0:
        usuarios = [
            Usuario(id=1, nombre_completo='Dirección General', username='direccion', email='dir@toplabel.com', rol='DIRECCION'),
            Usuario(id=2, nombre_completo='Juan Muñoz', username='juan_munoz', email='juan@toplabel.com', rol='LIDER_PILAR', pilar_id=1),
            Usuario(id=3, nombre_completo='Emmanuel', username='emmanuel', email='emmanuel@toplabel.com', rol='LIDER_PILAR', pilar_id=2),
            Usuario(id=4, nombre_completo='Alexis', username='alexis', email='alexis@toplabel.com', rol='LIDER_PILAR', pilar_id=3),
            Usuario(id=5, nombre_completo='Claudia', username='claudia', email='claudia@toplabel.com', rol='LIDER_PILAR', pilar_id=4),
            Usuario(id=6, nombre_completo='Líder Procesos', username='procesos_lider', email='proc@toplabel.com', rol='LIDER_PILAR', pilar_id=5),
            Usuario(id=7, nombre_completo='Tadeo', username='tadeo', email='tadeo@toplabel.com', rol='LIDER_PILAR', pilar_id=6),
            Usuario(id=8, nombre_completo='Lu', username='lu_sac', email='lu@toplabel.com', rol='LIDER_PILAR', pilar_id=7)
        ]
        for u in usuarios:
            u.set_password('TopLabel2026!')
            db.session.add(u)
        db.session.commit()
        print("✅ Usuarios creados con contraseña inicial: TopLabel2026!")

    # Poblar Tareas reales de Top Label del Excel
    if Tarea.query.count() == 0:
        hoy = date.today()
        tareas = [
            Tarea(id=1, codigo_folio='TL-PROD-001', titulo='Reclutar 2 impresores más de los actuales', pilar_id=1, responsable_id=2, creado_por_id=1, prioridad='P1_ALTA', estatus='COMPLETADO', fecha_inicio=hoy, fecha_compromiso=hoy, fecha_cierre=hoy),
            Tarea(id=2, codigo_folio='TL-PROD-002', titulo='Capacitar a impresores actuales en habilidades específicas', pilar_id=1, responsable_id=2, creado_por_id=1, prioridad='P1_ALTA', estatus='PENDIENTE', fecha_inicio=hoy, fecha_compromiso=hoy + timedelta(days=7)),
            Tarea(id=3, codigo_folio='TL-DIS-001', titulo='Promover consumo de papel en rack de la 35', pilar_id=2, responsable_id=3, creado_por_id=1, prioridad='P2_MEDIA', estatus='COMPLETADO', fecha_inicio=hoy, fecha_compromiso=hoy, fecha_cierre=hoy),
            Tarea(id=4, codigo_folio='TL-PROC-001', titulo='Definir proceso y habilidades impresores Flexo', pilar_id=5, responsable_id=6, creado_por_id=1, prioridad='P0_CRITICA', estatus='EN_PROCESO', fecha_inicio=hoy, fecha_compromiso=hoy + timedelta(days=4)),
            Tarea(id=5, codigo_folio='TL-SIS-001', titulo='Levantamiento necesidades sistema Flexo y empaque', pilar_id=6, responsable_id=7, creado_por_id=1, prioridad='P1_ALTA', estatus='PENDIENTE', fecha_inicio=hoy, fecha_compromiso=hoy + timedelta(days=5)),
            Tarea(id=6, codigo_folio='TL-SIS-002', titulo='Crear NAS área Textil en servidor Textil', pilar_id=6, responsable_id=7, creado_por_id=1, prioridad='P2_MEDIA', estatus='EN_PROCESO', fecha_inicio=hoy, fecha_compromiso=hoy + timedelta(days=6)),
            Tarea(id=7, codigo_folio='TL-SAC-001', titulo='Incitar incremento de metros por cada O.P.', pilar_id=7, responsable_id=8, creado_por_id=1, prioridad='P0_CRITICA', estatus='PENDIENTE', fecha_inicio=hoy, fecha_compromiso=hoy + timedelta(days=2))
        ]
        for t in tareas: 
            db.session.add(t)
        db.session.commit()
        print("✅ Tareas reales de Top Label cargadas exitosamente.")

print("\n🎉 ¡SISTEMA TOP LABEL INICIALIZADO AL 100%!")
