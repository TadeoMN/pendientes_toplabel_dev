from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Tarea, Pilar, Usuario, BitacoraTarea
from app.routes.tareas import generar_folio

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/tareas', methods=['GET'])
def listar_tareas():
    tareas = Tarea.query.order_by(Tarea.fecha_compromiso.asc()).all()
    return jsonify([t.to_dict() for t in tareas])

@api_bp.route('/tareas/ingesta-ia', methods=['POST'])
def ingesta_ia():
    token = current_app.config.get('API_AUTH_TOKEN')
    auth = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if auth != token:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json() or {}
    tareas_data = data.get('tareas', [])
    admin_user = Usuario.query.filter_by(rol='DIRECCION').first() or Usuario.query.first()
    creadas = []

    for item in tareas_data:
        pilar = Pilar.query.filter(Pilar.nombre.ilike(f"%{item.get('pilar')}%")).first()
        if not pilar:
            continue
        responsable = Usuario.query.filter(Usuario.nombre_completo.ilike(f"%{item.get('responsable_nombre', '')}%")).first() or admin_user
        
        try:
            f_comp = datetime.strptime(item.get('fecha_compromiso', ''), '%Y-%m-%d').date()
        except Exception:
            f_comp = date.today()

        nueva = Tarea(
            codigo_folio=generar_folio(pilar.id),
            titulo=item.get('titulo'),
            descripcion=item.get('descripcion', ''),
            pilar_id=pilar.id,
            responsable_id=responsable.id,
            creado_por_id=admin_user.id,
            prioridad=item.get('prioridad', 'P1_ALTA'),
            estatus='PENDIENTE',
            fecha_inicio=date.today(),
            fecha_compromiso=f_comp,
            fuente='REUNION_AUDIO_IA'
        )
        db.session.add(nueva)
        db.session.commit()
        creadas.append(nueva.to_dict())

    return jsonify({'success': True, 'creadas': len(creadas)}), 201
