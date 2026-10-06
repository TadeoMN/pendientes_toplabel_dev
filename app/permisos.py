"""Permisos acumulativos por rol; el liderazgo de un pilar no concede permisos."""
from flask import abort
from flask_login import current_user
from app import db
from app.modelos_acceso import Rol, Permiso, RolPermiso, UsuarioRol, AuditoriaSistema

ALCANCES = {'propias': 'Creadas por el usuario', 'asignadas': 'Asignadas al usuario',
            'apoyo': 'En las que participa como apoyo', 'pilares': 'Pilares donde es líder', 'todas': 'Todas'}
CATALOGO = {
    'panel.ver': ('Acceder al panel general', False),
    'usuarios.ver': ('Consultar usuarios', False), 'usuarios.crear': ('Crear usuarios', False),
    'usuarios.editar': ('Editar/desactivar usuarios', False), 'usuarios.password': ('Restablecer contraseñas', False),
    'usuarios.roles': ('Asignar roles a usuarios', False),
    'pilares.ver': ('Consultar pilares', False), 'pilares.gestionar': ('Administrar pilares y titulares', False),
    'roles.gestionar': ('Administrar roles y permisos', False), 'auditoria.ver': ('Consultar auditoría', False),
    'archivos.configurar': ('Configurar límites de archivos', False),
    'tareas.crear': ('Crear tareas para sí mismo', False),
    'tareas.asignar_pilares': ('Asignar a miembros de pilares donde es líder', False),
    'tareas.asignar_todos': ('Asignar a cualquier usuario', False),
    'tareas.ver': ('Consultar tareas', True), 'tareas.editar': ('Editar tareas', True),
    'tareas.estatus': ('Cambiar estatus', True), 'notas.ver': ('Consultar bitácora', True),
    'notas.crear': ('Registrar notas', True), 'archivos.subir': ('Adjuntar archivos', True),
    'archivos.ver': ('Consultar archivos', True), 'archivos.descargar': ('Descargar archivos', True),
    'archivos.retirar': ('Retirar archivos', True),
}


def alcances(usuario, codigo):
    if not usuario.is_authenticated or not usuario.activo:
        return set()
    if usuario.es_administrador:
        return {'sistema', 'todas'}
    return {p.alcance for a in usuario.roles_sistema if a.rol.activo
            for p in a.rol.permisos if p.permiso.codigo == codigo}


def permite(usuario, codigo, tarea=None):
    concedidos = alcances(usuario, codigo)
    if tarea is None:
        return bool(concedidos)
    if 'todas' in concedidos:
        return True
    if 'propias' in concedidos and tarea.creado_por_id == usuario.id:
        return True
    if 'asignadas' in concedidos and tarea.responsable_id == usuario.id:
        return True
    pilares = usuario.pilares_info()
    if 'pilares' in concedidos and tarea.pilar_id in {p['id'] for p in pilares if p['es_lider']}:
        return True
    if 'apoyo' in concedidos:
        ids = {p['id'] for p in pilares}
        return any(d['responsable_id'] == usuario.id or (d['responsable_id'] is None and d['pilar_id'] in ids)
                   for d in tarea.dependencias_info())
    return False


def exigir(codigo, tarea=None):
    if not permite(current_user, codigo, tarea):
        abort(403)


def puede_asignar(usuario, responsable):
    if usuario.puede('tareas.asignar_todos'):
        return True
    if responsable.id == usuario.id:
        return usuario.puede('tareas.crear')
    lider = {p['id'] for p in usuario.pilares_info() if p['es_lider']}
    return usuario.puede('tareas.asignar_pilares') and bool(lider & {p['id'] for p in responsable.pilares_info()})


def auditar(accion, detalle, usuario_id=None):
    db.session.add(AuditoriaSistema(accion=accion, detalle=detalle,
        usuario_id=usuario_id if usuario_id is not None else current_user.id))


def inicializar_catalogo():
    """Solo para la migración explícita; nunca se ejecuta al atender peticiones."""
    for codigo, (nombre, _) in CATALOGO.items():
        if not Permiso.query.filter_by(codigo=codigo).first():
            db.session.add(Permiso(codigo=codigo, nombre=nombre))
    db.session.flush()
    for codigo, nombre in [('ADMINISTRADOR', 'Administrador del sistema'), ('DIRECCION', 'Dirección'),
                           ('LIDER_PILAR', 'Líder'), ('COLABORADOR', 'Colaborador')]:
        if Rol.query.filter_by(codigo=codigo).first():
            continue
        rol = Rol(codigo=codigo, nombre=nombre, es_administrador=codigo == 'ADMINISTRADOR')
        db.session.add(rol)
        db.session.flush()
        if rol.es_administrador:
            continue
        permisos = {'tareas.crear': ['sistema'], 'tareas.ver': ['propias', 'asignadas', 'apoyo'],
                    'tareas.editar': ['propias'], 'tareas.estatus': ['propias', 'asignadas'],
                    'notas.ver': ['propias', 'asignadas', 'apoyo'], 'notas.crear': ['propias', 'asignadas', 'apoyo'],
                    'archivos.subir': ['propias', 'asignadas', 'apoyo'], 'archivos.ver': ['propias', 'asignadas', 'apoyo'],
                    'archivos.descargar': ['propias', 'asignadas', 'apoyo'], 'archivos.retirar': ['propias']}
        if codigo == 'LIDER_PILAR':
            permisos['tareas.asignar_pilares'] = ['sistema']
            for accion in ('tareas.ver', 'tareas.estatus', 'notas.ver', 'notas.crear', 'archivos.ver', 'archivos.descargar', 'archivos.subir'):
                permisos[accion].append('pilares')
        if codigo == 'DIRECCION':
            for accion in ('panel.ver', 'usuarios.ver', 'usuarios.crear', 'usuarios.editar', 'usuarios.password',
                           'pilares.ver', 'pilares.gestionar', 'tareas.asignar_todos'):
                permisos[accion] = ['sistema']
            for accion in ('tareas.ver', 'tareas.estatus', 'notas.ver', 'notas.crear', 'archivos.ver', 'archivos.descargar', 'archivos.subir'):
                permisos[accion] = ['todas']
        for accion, scopes in permisos.items():
            p = Permiso.query.filter_by(codigo=accion).one()
            for scope in scopes:
                rol.permisos.append(RolPermiso(permiso_id=p.id, alcance=scope))
