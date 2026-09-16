from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Tarea, Pilar, Usuario, BitacoraTarea
from app.routes.tareas import generar_folio, PRIORIDADES

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/tareas', methods=['GET'])
def listar_tareas():
    tareas = Tarea.query.order_by(Tarea.fecha_compromiso.asc()).all()
    return jsonify([t.to_dict() for t in tareas])

@api_bp.route('/tareas/ingesta-ia', methods=['POST'])
def ingesta_ia():
    token = current_app.config.get('API_AUTH_TOKEN')
    auth = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token or auth != token:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('tareas'), list):
        return jsonify({'error': 'Se requiere una lista de tareas.'}), 400
    tareas_data = data['tareas']
    try:
        admin_user = Usuario.query.filter_by(rol='DIRECCION', activo=True).order_by(Usuario.id).first()
        if admin_user is None:
            raise ValueError('No existe un usuario activo de Dirección para registrar las tareas.')
        for indice, item in enumerate(tareas_data, start=1):
            if not isinstance(item, dict):
                raise ValueError(f'Tarea {indice}: datos inválidos.')
            titulo = item.get('titulo')
            descripcion = item.get('descripcion', '')
            prioridad = item.get('prioridad', 'P1_ALTA')
            if not isinstance(titulo, str) or not titulo.strip() or len(titulo.strip()) > 200:
                raise ValueError(f'Tarea {indice}: título inválido.')
            if not isinstance(descripcion, str) or not isinstance(prioridad, str) or prioridad not in PRIORIDADES:
                raise ValueError(f'Tarea {indice}: descripción o prioridad inválida.')
            try:
                f_comp = datetime.strptime(item.get('fecha_compromiso', ''), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                raise ValueError(f'Tarea {indice}: fecha de compromiso inválida.') from None
            pilar_nombre = item.get('pilar')
            if not isinstance(pilar_nombre, str) or not pilar_nombre.strip():
                raise ValueError(f'Tarea {indice}: pilar obligatorio.')
            pilares = Pilar.query.filter(Pilar.nombre == pilar_nombre.strip()).all()
            if not pilares:
                pilares = Pilar.query.filter(Pilar.nombre.contains(pilar_nombre.strip(), autoescape=True)).all()
            if len(pilares) != 1:
                raise ValueError(f'Tarea {indice}: el pilar no existe o su nombre es ambiguo.')
            responsable_nombre = item.get('responsable_nombre', '')
            if not isinstance(responsable_nombre, str):
                raise ValueError(f'Tarea {indice}: responsable inválido.')
            responsable = admin_user
            if responsable_nombre.strip():
                candidatos = Usuario.query.filter_by(activo=True, nombre_completo=responsable_nombre.strip()).all()
                if not candidatos:
                    candidatos = Usuario.query.filter(Usuario.activo.is_(True),
                        Usuario.nombre_completo.contains(responsable_nombre.strip(), autoescape=True)).all()
                if len(candidatos) != 1:
                    raise ValueError(f'Tarea {indice}: el responsable no existe o su nombre es ambiguo.')
                responsable = candidatos[0]
            nueva = Tarea(codigo_folio=generar_folio(pilares[0].id), titulo=titulo.strip(),
                descripcion=descripcion, pilar_id=pilares[0].id, responsable_id=responsable.id,
                creado_por_id=admin_user.id, prioridad=prioridad, estatus='PENDIENTE',
                fecha_inicio=date.today(), fecha_compromiso=f_comp, fuente='REUNION_AUDIO_IA')
            db.session.add(nueva)
            db.session.flush()
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({'error': str(error)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'error': 'No se guardó el lote de tareas. Revisa los datos e inténtalo nuevamente.'}), 500
    return jsonify({'success': True, 'creadas': len(tareas_data)}), 201
