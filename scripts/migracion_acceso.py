"""Contrato aditivo v3 y datos iniciales obtenidos exclusivamente del destino."""
from contextlib import contextmanager
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql
from app import db
from app import models, modelos_acceso

TABLAS = ('roles', 'permisos', 'roles_permisos', 'usuarios_roles', 'auditoria_sistema', 'adjuntos', 'configuracion_archivos')


@contextmanager
def contrato(base, tablas=TABLAS):
    anteriores = (base.COLUMNS, base.UNIQUE_KEYS, base.FOREIGN_KEYS, base.NEW_TABLES, base.DDLS)
    base.COLUMNS, base.UNIQUE_KEYS, base.FOREIGN_KEYS, base.DDLS = [dict(x) for x in
        (base.COLUMNS, base.UNIQUE_KEYS, base.FOREIGN_KEYS, base.DDLS)]
    base.NEW_TABLES = (*base.NEW_TABLES, *tablas)
    try:
        for nombre in tablas:
            tabla = db.metadata.tables[nombre]
            columnas = {}
            for col in tabla.columns:
                tipo = str(col.type.compile(dialect=mysql.dialect())).lower().replace('integer', 'int').replace('bool', 'tinyint(1)')
                columnas[col.name] = (tipo, 'YES' if col.nullable else 'NO', None, 'auto_increment' if col.primary_key else '')
            base.COLUMNS[nombre] = columnas
            unicas = {('id',)}
            for constraint in tabla.constraints:
                if constraint.__class__.__name__ == 'UniqueConstraint':
                    unicas.add(tuple(c.name for c in constraint.columns))
            base.UNIQUE_KEYS[nombre] = unicas
            base.FOREIGN_KEYS[nombre] = [(fk.parent.name, fk.column.table.name, 'NO ACTION') for fk in tabla.foreign_keys]
            # Índices de FK explícitos dentro del CREATE para verificación inmediata.
            ddl = str(CreateTable(tabla).compile(dialect=mysql.dialect())).strip()
            indices = [f'INDEX ix_{nombre}_{fk.parent.name} (`{fk.parent.name}`)' for fk in tabla.foreign_keys]
            cierre = ddl.rfind(')')
            if indices:
                ddl = ddl[:cierre].rstrip() + ',\n' + ',\n'.join(indices) + '\n' + ddl[cierre:]
            base.DDLS['crear_' + nombre] = ddl + ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=' + base.COLLATION
        yield
    finally:
        base.COLUMNS, base.UNIQUE_KEYS, base.FOREIGN_KEYS, base.NEW_TABLES, base.DDLS = anteriores


def inicializar(conn, admin_username):
    """Una transacción DML separada del DDL; no altera filas de las tablas antiguas."""
    # Usar el app factory con una conexión al mismo destino evita leer .env de desarrollo.
    from app import create_app
    from sqlalchemy.pool import StaticPool
    # Sembrado con Session normal, reutilizando el catálogo de una app enlazada al destino.
    app = create_app({'SQLALCHEMY_DATABASE_URI': 'mysql+pymysql://',
                      'SQLALCHEMY_ENGINE_OPTIONS': {'creator': lambda: conn, 'poolclass': StaticPool}})
    from app.permisos import inicializar_catalogo
    from app.modelos_acceso import Rol, UsuarioRol, AuditoriaSistema
    from app.models import Usuario
    with app.app_context():
        try:
            conn.autocommit(False)
            inicializar_catalogo()
            usuarios = Usuario.query.order_by(Usuario.id).all()
            for usuario in usuarios:
                if not usuario.roles_sistema:
                    rol = Rol.query.filter_by(codigo=usuario.rol).one_or_none()
                    if rol is None:
                        raise ValueError('Rol histórico desconocido; requiere revisión.')
                    usuario.roles_sistema.append(UsuarioRol(rol=rol))
            admin = Usuario.query.filter_by(username=admin_username, activo=True).one_or_none() if admin_username else None
            ya_admin = any(u.es_administrador for u in usuarios)
            if not ya_admin:
                if admin is None:
                    raise ValueError('Indica --admin-usuario con una cuenta activa del destino.')
                admin.roles_sistema[:] = [UsuarioRol(rol=Rol.query.filter_by(codigo='ADMINISTRADOR').one())]
            db.session.add(AuditoriaSistema(usuario_id=admin.id if admin else None, accion='migracion.roles_archivos',
                detalle='Catálogo y asignaciones iniciales verificados. No se modificaron tareas, notas ni cuentas originales.'))
            db.session.commit()
            return {'usuarios_verificados': len(usuarios), 'administrador_inicial': admin_username if not ya_admin else 'existente'}
        except Exception:
            db.session.rollback()
            raise
        finally:
            # No cerrar aquí la conexión propiedad del migrador.
            db.session.remove()
            conn.autocommit(True)


def preflight(conn, schema, admin_username, base, env_file=None, database=None):
    tables = {t['TABLE_NAME'] for t in schema['tables']}
    if {'roles', 'usuarios_roles'} <= tables:
        admin = base.query(conn, 'SELECT COUNT(*) n FROM usuarios u JOIN usuarios_roles ur ON ur.usuario_id=u.id JOIN roles r ON r.id=ur.rol_id WHERE u.activo=1 AND r.activo=1 AND r.es_administrador=1')[0]['n']
    else:
        admin = 0
    if not admin:
        base.require(bool(admin_username), 'Para la primera aplicación indica --admin-usuario con una cuenta activa del destino.')
        base.require(len(base.query(conn, 'SELECT id FROM usuarios WHERE username=%s AND activo=1', (admin_username,))) == 1,
                     'No existe una única cuenta activa para el administrador inicial del destino.')
    desconocidos = base.query(conn, "SELECT COUNT(*) n FROM usuarios WHERE rol IS NULL OR rol NOT IN ('DIRECCION','LIDER_PILAR','COLABORADOR')")[0]['n']
    base.require(not desconocidos, 'Existen roles históricos no reconocidos; revisa el mapeo antes de migrar.')
    archivos = 0
    if env_file and 'adjuntos' in tables:
        import hashlib
        import re
        root = carpeta_adjuntos(env_file, database)
        for row in base.query(conn, 'SELECT id,clave,tamano,sha256 FROM adjuntos'):
            base.require(bool(re.fullmatch('[0-9a-f]{32}', row['clave'])), 'Clave de adjunto inválida.')
            path = root / row['clave']
            base.require(not path.is_symlink() and path.is_file() and path.resolve().parent == root,
                         'Falta un archivo adjunto o su ruta no es válida. Revisa UPLOAD_ROOT antes de migrar.')
            base.require(path.stat().st_size == row['tamano'], 'El tamaño de un adjunto no coincide con la BD.')
            with path.open('rb') as stream:
                base.require(hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'],
                             'El contenido de un adjunto no coincide con la BD.')
            archivos += 1
    return {'administrador_existente': bool(admin), 'asignacion_inicial': admin_username if not admin else None,
            'adjuntos_verificados': archivos}


def carpeta_adjuntos(env_file, database):
    from pathlib import Path
    from dotenv import dotenv_values
    valores = dotenv_values(env_file)
    return Path(valores.get('UPLOAD_ROOT') or Path(env_file).resolve().parent.parent / 'archivos_pendientes' / database).resolve()


def respaldar_adjuntos(env_file, database, output):
    from pathlib import Path
    import hashlib
    import zipfile
    origen = carpeta_adjuntos(env_file, database)
    if not origen.exists():
        return {'status': 'sin_archivos', 'origen': str(origen)}
    paths = [origen, *origen.rglob('*')]
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in paths):
        raise ValueError('No se admiten enlaces en el almacenamiento de adjuntos.')
    def huellas():
        resultado = {}
        for path in origen.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:
                    resultado[str(path.relative_to(origen))] = hashlib.file_digest(stream, 'sha256').hexdigest()
        return resultado
    antes = huellas()
    destino = Path(output) / 'adjuntos_antes.zip'
    with zipfile.ZipFile(destino, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for nombre in antes:
            z.write(origen / nombre, nombre)
    with zipfile.ZipFile(destino) as z:
        if z.testzip() is not None:
            raise ValueError('El respaldo de adjuntos no se pudo verificar.')
        for nombre, digest in antes.items():
            with z.open(nombre.replace('\\', '/')) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    raise ValueError('Cambió un archivo durante el respaldo.')
    if huellas() != antes:
        raise ValueError('El almacenamiento cambió durante el respaldo.')
    return {'status': 'verificado', 'origen': str(origen), 'zip': str(destino), 'archivos': len(antes)}


def plan_desarrollo(schema, database, base, tablas=TABLAS):
    import copy
    base.require(database == 'toplabel_pendientes', 'El modo desarrollo solo admite toplabel_pendientes.')
    reducido = copy.deepcopy(schema)
    for key in ('tables', 'columns', 'indexes', 'fks', 'checks'):
        reducido[key] = [x for x in reducido[key] if x['TABLE_NAME'] in tablas]
    original = base.ORIGINAL_TABLES
    collation = base.COLLATION
    base.require(schema['defaults'] == {'DEFAULT_CHARACTER_SET_NAME': 'utf8mb4', 'DEFAULT_COLLATION_NAME': 'utf8mb4_unicode_ci'}, 'Collation de desarrollo no reconocida.')
    base.COLLATION = 'utf8mb4_unicode_ci'
    with contrato(base, tablas):
        base.ORIGINAL_TABLES = ()
        base.NEW_TABLES = tablas
        try:
            return base.build_plan(reducido, database)
        finally:
            base.ORIGINAL_TABLES = original
            base.COLLATION = collation
