import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.modelos_acceso import Rol, Permiso, RolPermiso, UsuarioRol, AuditoriaSistema, ConfiguracionArchivos
from app.permisos import CATALOGO, ALCANCES, exigir, auditar

roles_bp = Blueprint('roles', __name__, url_prefix='/roles')


@roles_bp.route('/', methods=['GET', 'POST'])
@login_required
def gestionar():
    exigir('roles.gestionar')
    if request.method == 'POST':
        try:
            rol_id = request.form.get('rol_id', type=int)
            rol = db.session.get(Rol, rol_id) if rol_id else Rol(codigo='PERSONALIZADO_' + __import__('uuid').uuid4().hex[:20])
            if rol is None or rol.es_administrador:
                abort(403)
            nombre = request.form.get('nombre', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            if not nombre or len(nombre) > 100 or len(descripcion) > 250:
                raise ValueError('Revisa el nombre y la descripción del rol.')
            nuevos = set(request.form.getlist('permisos'))
            validos = {codigo + '|' + scope for codigo, (_, scoped) in CATALOGO.items()
                       for scope in (ALCANCES if scoped else ['sistema'])}
            if not nuevos <= validos:
                raise ValueError('Hay permisos desconocidos.')
            antes = {'nombre': rol.nombre, 'permisos': [p.permiso.codigo + '|' + p.alcance for p in rol.permisos]}
            rol.nombre, rol.descripcion = nombre, descripcion
            db.session.add(rol)
            rol.permisos.clear()
            db.session.flush()
            catalogo = {p.codigo: p.id for p in Permiso.query.all()}
            for item in sorted(nuevos):
                codigo, scope = item.split('|')
                rol.permisos.append(RolPermiso(permiso_id=catalogo[codigo], alcance=scope))
            auditar('roles.editar', json.dumps({'rol': rol.codigo, 'antes': antes, 'nombre': nombre, 'permisos': sorted(nuevos)}, ensure_ascii=False))
            db.session.commit()
            flash('Rol y permisos guardados.', 'success')
            return redirect(url_for('roles.gestionar', editar=rol.id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'warning')
        except Exception:
            db.session.rollback()
            raise
    seleccionado = db.session.get(Rol, request.args.get('editar', type=int)) if request.args.get('editar') else None
    if seleccionado and seleccionado.es_administrador:
        seleccionado = None
    marcados = {p.permiso.codigo + '|' + p.alcance for p in seleccionado.permisos} if seleccionado else set()
    return render_template('admin/roles.html', roles=Rol.query.order_by(Rol.nombre).all(),
                           seleccionado=seleccionado, catalogo=CATALOGO, alcances=ALCANCES, marcados=marcados)


@roles_bp.route('/auditoria')
@login_required
def auditoria():
    exigir('auditoria.ver')
    pagina = max(1, request.args.get('pagina', 1, type=int))
    registros = AuditoriaSistema.query.order_by(AuditoriaSistema.id.desc()).paginate(page=pagina, per_page=50, error_out=False)
    return render_template('admin/auditoria.html', registros=registros)


def asignar_rol(usuario, rol_id, nuevo=False):
    rol = db.session.get(Rol, rol_id)
    if rol is None or not rol.activo:
        raise ValueError('Selecciona un rol activo.')
    ids = {a.rol_id for a in usuario.roles_sistema}
    if ids == {rol.id}:
        return
    # Crear usuarios sin gestionar roles solo puede usar Colaborador.
    if not current_user.puede('usuarios.roles') and not (nuevo and rol.codigo == 'COLABORADOR'):
        abort(403)
    anteriores = [a.rol.nombre for a in usuario.roles_sistema]
    usuario.roles_sistema[:] = [UsuarioRol(rol=rol)]
    auditar('usuarios.roles', json.dumps({'usuario': usuario.id, 'antes': anteriores, 'despues': rol.nombre}, ensure_ascii=False))


def proteger_administradores():
    """El lock serializa desactivaciones/cambios del último administrador."""
    from app.models import Usuario
    Rol.query.filter_by(es_administrador=True).with_for_update().all()
    db.session.flush()
    total = db.session.query(UsuarioRol.id).join(Rol).join(Usuario, Usuario.id == UsuarioRol.usuario_id).filter(
        Rol.es_administrador.is_(True), Rol.activo.is_(True), Usuario.activo.is_(True)).count()
    if not total:
        raise ValueError('Debe conservarse al menos un administrador activo.')
