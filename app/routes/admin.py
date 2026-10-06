from functools import wraps
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Usuario, Pilar, UsuarioPilar
from app.modelos_acceso import Rol
from app.permisos import exigir
from app.routes.roles import asignar_rol, proteger_administradores

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
ROLES = {'DIRECCION', 'LIDER_PILAR', 'COLABORADOR'}


@admin_bp.before_request
@login_required
def verificar_acceso_direccion():
    permisos = {
        'admin.usuarios': 'usuarios.ver', 'admin.crear_usuario': 'usuarios.crear',
        'admin.editar_usuario': 'usuarios.editar', 'admin.cambiar_password': 'usuarios.password',
        'admin.pilares': 'pilares.ver',
    }
    exigir(permisos.get(request.endpoint, 'pilares.gestionar'))



def guardar_en(endpoint):
    """Todas las modificaciones de una operación se confirman juntas."""
    def decorar(func):
        @wraps(func)
        def ejecutar(*args, **kwargs):
            try:
                mensaje = func(*args, **kwargs)
                db.session.commit()
            except ValueError as error:
                db.session.rollback()
                flash(str(error), 'warning')
            except SQLAlchemyError as error:
                db.session.rollback()
                current_app.logger.error('No se guardó %s: %s', func.__name__, type(error).__name__)
                flash('No se guardaron los cambios. Revisa los datos e inténtalo nuevamente.', 'danger')
            else:
                flash(mensaje, 'success')
            return redirect(url_for(endpoint))
        return ejecutar
    return decorar


def texto(campo, limite, obligatorio=False, predeterminado=''):
    valor = request.form.get(campo, predeterminado).strip()
    if obligatorio and not valor:
        raise ValueError(f'El campo {campo} es obligatorio.')
    if len(valor) > limite:
        raise ValueError(f'El campo {campo} admite hasta {limite} caracteres.')
    return valor


def id_opcional(valor):
    if valor in ('', None):
        return None
    try:
        valor = int(valor)
    except (ValueError, TypeError):
        raise ValueError('Identificador inválido.') from None
    if valor <= 0:
        raise ValueError('Identificador inválido.')
    return valor


def datos_usuario(usuario=None):
    nombre = texto('nombre_completo', 100, True)
    username = texto('username', 50, True)
    email = texto('email', 100) or None
    rol = usuario.rol if usuario else 'COLABORADOR'
    duplicados = Usuario.query.filter(Usuario.username == username)
    if usuario is not None:
        duplicados = duplicados.filter(Usuario.id != usuario.id)
    if duplicados.first():
        raise ValueError('La clave de usuario ya está registrada.')
    if email:
        duplicados = Usuario.query.filter(Usuario.email == email)
        if usuario is not None:
            duplicados = duplicados.filter(Usuario.id != usuario.id)
        if duplicados.first():
            raise ValueError('El correo ya está registrado.')
    return dict(nombre_completo=nombre, username=username, email=email, rol=rol)


def leer_asignaciones():
    ids = request.form.getlist('usuario_pilar_id[]')
    roles = request.form.getlist('usuario_rol_pilar[]')
    asignaciones = {}
    for indice, valor in enumerate(ids):
        pilar_id = id_opcional(valor)
        if pilar_id is None:
            continue
        rol = roles[indice] if indice < len(roles) else 'COLABORADOR'
        if rol not in {'LIDER', 'COLABORADOR'}:
            raise ValueError('Rol de pilar inválido.')
        if pilar_id in asignaciones:
            raise ValueError('Un pilar no puede asignarse dos veces al mismo usuario.')
        pilar = db.session.get(Pilar, pilar_id)
        if pilar is None:
            raise ValueError('Uno de los pilares seleccionados ya no existe.')
        asignaciones[pilar_id] = (pilar, rol == 'LIDER')
    if any(roles[len(ids):]):
        raise ValueError('Las filas de asignaciones están incompletas.')
    return asignaciones


def reemplazar_asignaciones(usuario, asignaciones):
    actuales = {a.pilar_id: a for a in usuario.asignaciones_pilar}
    for pilar in list(usuario.pilar_titular):
        nueva = asignaciones.get(pilar.id)
        if nueva is None or not nueva[1]:
            pilar.responsable = None
    for pilar_id, actual in actuales.items():
        if pilar_id not in asignaciones:
            usuario.asignaciones_pilar.remove(actual)
    for pilar_id, (pilar, lider) in asignaciones.items():
        if pilar_id in actuales:
            actuales[pilar_id].es_lider = lider
        else:
            usuario.asignaciones_pilar.append(UsuarioPilar(pilar=pilar, es_lider=lider))
        if lider and pilar.responsable is None:
            pilar.responsable = usuario
    # Evita reactivar datos antiguos al retirar la última asignación.
    usuario.pilar_historico = None
    usuario.es_responsable = False


def materializar_asignaciones(usuario):
    """Conserva relaciones efectivas al editar un titular, sin migración masiva."""
    actuales = {a.pilar_id: a for a in usuario.asignaciones_pilar}
    for info in usuario.pilares_info():
        if info['id'] in actuales:
            actuales[info['id']].es_lider = info['es_lider']
        else:
            usuario.asignaciones_pilar.append(UsuarioPilar(
                pilar=db.session.get(Pilar, info['id']), es_lider=info['es_lider']))
    usuario.pilar_historico = None
    usuario.es_responsable = False


def datos_pilar(pilar=None):
    nombre = texto('nombre', 50, True)
    descripcion = texto('descripcion', 150)
    color = texto('color_identificador', 7, predeterminado=pilar.color_identificador if pilar else '#2563eb')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('El color debe tener formato hexadecimal #RRGGBB.')
    consulta = Pilar.query.filter(Pilar.nombre == nombre)
    if pilar is not None:
        consulta = consulta.filter(Pilar.id != pilar.id)
    if consulta.first():
        raise ValueError('Ya existe un pilar con ese nombre.')
    responsable_id = id_opcional(request.form.get('responsable_id'))
    responsable = db.session.get(Usuario, responsable_id) if responsable_id else None
    if responsable_id and (responsable is None or not responsable.activo):
        raise ValueError('El titular seleccionado no existe o está inactivo.')
    return dict(nombre=nombre, descripcion=descripcion, color_identificador=color), responsable


def cambiar_titular(pilar, nuevo):
    anterior = pilar.responsable
    for usuario in {u for u in (anterior, nuevo) if u is not None}:
        materializar_asignaciones(usuario)
    if anterior is not None and nuevo is None:
        for asignacion in anterior.asignaciones_pilar:
            if asignacion.pilar_id == pilar.id or asignacion.pilar is pilar:
                asignacion.es_lider = False
    pilar.responsable = nuevo
    if nuevo is not None:
        asignacion = next((a for a in nuevo.asignaciones_pilar
                           if a.pilar_id == pilar.id or a.pilar is pilar), None)
        if asignacion is None:
            nuevo.asignaciones_pilar.append(UsuarioPilar(pilar=pilar, es_lider=True))
        else:
            asignacion.es_lider = True
    # Cambiar titular conserva al anterior como líder secundario; quitarlo
    # explícitamente lo deja colaborador. Los demás líderes se conservan.


@admin_bp.route('/usuarios')
def usuarios():
    return render_template('admin/usuarios.html',
        usuarios=Usuario.query.order_by(Usuario.nombre_completo.asc()).all(),
        pilares=Pilar.query.order_by(Pilar.nombre.asc()).all(),
        roles=Rol.query.filter_by(activo=True).order_by(Rol.nombre).all())


@admin_bp.route('/usuarios/crear', methods=['POST'])
@guardar_en('admin.usuarios')
def crear_usuario():
    datos = datos_usuario()
    password = request.form.get('password', '').strip()
    if not password:
        raise ValueError('La contraseña es obligatoria.')
    asignaciones = leer_asignaciones()
    nuevo = Usuario(**datos, activo=True)
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.flush()
    asignar_rol(nuevo, request.form.get('rol_id', type=int), nuevo=True)
    reemplazar_asignaciones(nuevo, asignaciones)
    return f'Usuario {nuevo.nombre_completo} registrado exitosamente.'


@admin_bp.route('/usuarios/<int:usuario_id>/editar', methods=['POST'])
@guardar_en('admin.usuarios')
def editar_usuario(usuario_id):
    Rol.query.filter_by(es_administrador=True).with_for_update().all()
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.tiene_rol_administrador and not current_user.es_administrador:
        from flask import abort
        abort(403)
    datos = datos_usuario(usuario)
    asignaciones = leer_asignaciones()
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    asignar_rol(usuario, request.form.get('rol_id', type=int))
    usuario.activo = request.form.get('activo') == '1'
    proteger_administradores()
    reemplazar_asignaciones(usuario, asignaciones)
    return f'Datos de {usuario.nombre_completo} actualizados.'


@admin_bp.route('/usuarios/<int:usuario_id>/password', methods=['POST'])
@guardar_en('admin.usuarios')
def cambiar_password(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.tiene_rol_administrador and not current_user.es_administrador:
        from flask import abort
        abort(403)
    password = request.form.get('password', '').strip()
    if not password:
        raise ValueError('La contraseña no puede estar vacía.')
    usuario.set_password(password)
    return f'Contraseña actualizada para @{usuario.username}.'


@admin_bp.route('/pilares')
def pilares():
    return render_template('admin/pilares.html',
        pilares=Pilar.query.order_by(Pilar.nombre.asc()).all(),
        usuarios=Usuario.query.filter_by(activo=True).order_by(Usuario.nombre_completo.asc()).all())


@admin_bp.route('/pilares/crear', methods=['POST'])
@guardar_en('admin.pilares')
def crear_pilar():
    datos, responsable = datos_pilar()
    pilar = Pilar(**datos)
    db.session.add(pilar)
    db.session.flush()
    cambiar_titular(pilar, responsable)
    return f'Pilar {pilar.nombre} registrado con éxito.'


@admin_bp.route('/pilares/<int:pilar_id>/editar', methods=['POST'])
@guardar_en('admin.pilares')
def editar_pilar(pilar_id):
    pilar = Pilar.query.get_or_404(pilar_id)
    datos, responsable = datos_pilar(pilar)
    cambiar_titular(pilar, responsable)
    for campo, valor in datos.items():
        setattr(pilar, campo, valor)
    return f'Pilar {pilar.nombre} actualizado correctamente.'


@admin_bp.route('/pilares/<int:pilar_id>/miembros', methods=['GET'])
def miembros_pilar(pilar_id):
    pilar = Pilar.query.get_or_404(pilar_id)
    miembros = []
    for usuario in pilar.miembros:
        info = next(p for p in usuario.pilares_info() if p['id'] == pilar.id)
        miembros.append(dict(id=usuario.id, nombre_completo=usuario.nombre_completo,
            username=usuario.username, email=usuario.email, es_responsable=info['es_lider']))
    return jsonify(pilar=pilar.nombre, color=pilar.color_identificador, miembros=miembros)
