from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app.models import Tarea, Pilar, Usuario

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard.direccion' if current_user.es_direccion else 'dashboard.mis_pendientes'))

@dashboard_bp.route('/dashboard')
@login_required
def direccion():
    pilar_param = request.args.get('pilar_id')
    estatus = request.args.get('estatus')
    prioridad = request.args.get('prioridad')
    filtro_semaforo = request.args.get('semaforo')
    query_search = request.args.get('q', '').strip()

    query = Tarea.query

    # Filtro especial si selecciona "sin_pilar"
    if pilar_param == 'sin_pilar':
        query = query.filter(Tarea.pilar_id.is_(None))
    elif pilar_param:
        query = query.filter_by(pilar_id=int(pilar_param))

    if estatus:
        query = query.filter_by(estatus=estatus)
    if prioridad:
        query = query.filter_by(prioridad=prioridad)
    if query_search:
        query = query.filter(Tarea.titulo.ilike(f'%{query_search}%'))

    todas_tareas = query.order_by(Tarea.fecha_compromiso.asc()).all()

    if filtro_semaforo:
        tareas_filtradas = [t for t in todas_tareas if t.semaforo == filtro_semaforo]
    else:
        tareas_filtradas = todas_tareas

    total_db = Tarea.query.all()
    conteo_total = len(total_db)
    conteo_rojo = sum(1 for t in total_db if t.semaforo == 'ROJO')
    conteo_amarillo = sum(1 for t in total_db if t.semaforo == 'AMARILLO')
    conteo_verde = sum(1 for t in total_db if t.semaforo == 'VERDE')
    conteo_azul = sum(1 for t in total_db if t.semaforo == 'AZUL')

    # Conteo dinámico de tareas sin pilar
    conteo_sin_pilar = sum(1 for t in total_db if t.pilar_id is None)

    pilares = Pilar.query.order_by(Pilar.nombre.asc()).all()
    responsables = Usuario.query.filter_by(activo=True).all()

    resumen_pilares = []
    for p in pilares:
        tareas_p = [t for t in total_db if t.pilar_id == p.id]
        resumen_pilares.append({
            'pilar': p,
            'total': len(tareas_p),
            'completadas': sum(1 for t in tareas_p if t.estatus == 'COMPLETADO'),
            'rojas': sum(1 for t in tareas_p if t.semaforo == 'ROJO')
        })

    return render_template(
        'dashboard_direccion.html',
        tareas=tareas_filtradas, pilares=pilares, responsables=responsables,
        resumen_pilares=resumen_pilares, conteo_total=conteo_total,
        conteo_rojo=conteo_rojo, conteo_amarillo=conteo_amarillo,
        conteo_verde=conteo_verde, conteo_azul=conteo_azul,
        conteo_sin_pilar=conteo_sin_pilar,               # <-- Pasamos el conteo
        pilar_seleccionado=pilar_param,
        filtro_semaforo=filtro_semaforo, filtro_prioridad=prioridad,
        query_search=query_search,
        usuarios_json=[u.to_dict() for u in responsables],
        pilares_json=[p.to_dict() for p in pilares]
    )

@dashboard_bp.route('/mis-pendientes')
@login_required
def mis_pendientes():
    if current_user.es_direccion:
        tareas = Tarea.query.order_by(Tarea.fecha_compromiso.asc()).all()
    else:
        pilar_ids = [pilar['id'] for pilar in current_user.pilares_info()]
        tareas = Tarea.query.filter(
            (Tarea.pilar_id.in_(pilar_ids)) | (Tarea.responsable_id == current_user.id)
        ).order_by(Tarea.fecha_compromiso.asc()).all()

    return render_template('mis_pendientes.html', tareas=tareas)
