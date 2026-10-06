from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app.models import Tarea, Pilar, Usuario
from app.permisos import exigir, puede_asignar

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard.direccion' if current_user.puede('panel.ver') else 'dashboard.mis_pendientes'))

@dashboard_bp.route('/dashboard')
@login_required
def direccion():
    exigir('panel.ver')
    visibles = [t for t in Tarea.query.order_by(Tarea.fecha_compromiso.asc()).all()
                if current_user.puede('tareas.ver', t)]
    grupos = [
        ('mis_asignaciones', 'Mis asignaciones', []),
        ('otros_directores', 'Otros directores', []),
        ('autonomas', 'Tareas autónomas', []),
    ]
    for tarea in visibles:
        # El origen registrado conserva el contexto aunque el creador cambie de rol.
        if tarea.creado_por_id == current_user.id:
            indice = 0
        elif tarea.fuente == 'INICIATIVA_PROPIA':
            indice = 2
        elif tarea.fuente == 'DIRECCION' or (tarea.creador and tarea.creador.es_direccion):
            indice = 1
        else:
            indice = 2
        grupos[indice][2].append(tarea)
    vista = request.args.get('vista', 'mis_asignaciones')
    if vista not in {g[0] for g in grupos}:
        vista = 'mis_asignaciones'
    pilares = Pilar.query.order_by(Pilar.nombre).all()
    responsables = Usuario.query.filter_by(activo=True).all()
    return render_template('dashboard_direccion.html', grupos=grupos, vista_actual=vista,
        pilares=pilares, responsables_permitidos=[u.id for u in responsables if puede_asignar(current_user,u)],
        usuarios_json=[u.to_dict() for u in responsables], pilares_json=[p.to_dict() for p in pilares])

@dashboard_bp.route('/mis-pendientes')
@login_required
def mis_pendientes():
    visibles = [t for t in Tarea.query.order_by(Tarea.fecha_compromiso.asc()).all()
                if current_user.puede('tareas.ver', t)]
    pilares_usuario = {p['id'] for p in current_user.pilares_info()}
    apoyos = {t.id: [d for d in t.dependencias_info() if d['responsable_id'] == current_user.id or
                    (d['responsable_id'] is None and d['pilar_id'] in pilares_usuario)] for t in visibles}
    grupos = [
        ('mias', 'Mis tareas', [t for t in visibles if t.responsable_id == current_user.id]),
        ('apoyo', 'Tareas de apoyo', [t for t in visibles if apoyos[t.id]]),
        ('delegadas', 'Asignadas por mí', [t for t in visibles if t.creado_por_id == current_user.id and t.responsable_id != current_user.id]),
    ]
    return render_template('mis_pendientes.html', grupos=grupos, apoyos=apoyos,
        responsables_permitidos=[u.id for u in Usuario.query.filter_by(activo=True).all() if puede_asignar(current_user,u)],
        pilares=Pilar.query.order_by(Pilar.nombre).all(),
        usuarios_json=[u.to_dict() for u in Usuario.query.filter_by(activo=True).all()],
        pilares_json=[p.to_dict() for p in Pilar.query.order_by(Pilar.nombre).all()])
