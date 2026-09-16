from datetime import datetime, date, timedelta
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Tarea, Pilar, BitacoraTarea, TareaDependencia

tareas_bp = Blueprint('tareas', __name__, url_prefix='/tareas')

def generar_folio(pilar_id):
    if pilar_id:
        pilar = Pilar.query.get(pilar_id)
        prefijo = (pilar.nombre[:4].upper() if pilar else 'GEN')
        conteo = Tarea.query.filter_by(pilar_id=pilar_id).count() + 1
    else:
        prefijo = 'GRAL'
        conteo = Tarea.query.filter(Tarea.pilar_id.is_(None)).count() + 1
    return f"TL-{prefijo}-{conteo:03d}"

@tareas_bp.route('/crear', methods=['POST'])
@login_required
def crear():
    titulo = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    pilar_id = request.form.get('pilar_id', type=int) or None  # <-- Puede ser None
    responsable_id = request.form.get('responsable_id', type=int)
    prioridad = request.form.get('prioridad', 'P2_MEDIA')
    fecha_comp_str = request.form.get('fecha_compromiso')

    if not titulo or not responsable_id or not fecha_comp_str:
        flash('Título, responsable y fecha límite son obligatorios.', 'warning')
        return redirect(url_for('dashboard.direccion'))

    try:
        fecha_comp = datetime.strptime(fecha_comp_str, '%Y-%m-%d').date()
    except Exception:
        flash('Fecha de compromiso inválida.', 'danger')
        return redirect(url_for('dashboard.direccion'))

    nueva_tarea = Tarea(
        codigo_folio=generar_folio(pilar_id),
        titulo=titulo,
        descripcion=descripcion,
        pilar_id=pilar_id,
        responsable_id=responsable_id,
        creado_por_id=current_user.id,
        prioridad=prioridad,
        estatus='PENDIENTE',
        fecha_inicio=date.today(),
        fecha_compromiso=fecha_comp,
        fuente='DIRECCION' if current_user.es_direccion else 'INICIATIVA_PROPIA'
    )
    db.session.add(nueva_tarea)
    db.session.commit()

    # Procesar apoyos si los hubiera
    apoyos_pilares = request.form.getlist('apoyo_pilar_id[]')
    apoyos_responsables = request.form.getlist('apoyo_responsable_id[]')

    for i in range(len(apoyos_pilares)):
        p_id_str = apoyos_pilares[i]
        if p_id_str:
            p_id = int(p_id_str)
            r_id_str = apoyos_responsables[i] if i < len(apoyos_responsables) else ''
            r_id = int(r_id_str) if r_id_str else None

            dep = TareaDependencia(tarea_id=nueva_tarea.id, pilar_id=p_id, responsable_id=r_id)
            db.session.add(dep)

    db.session.commit()
    flash(f'Tarea {nueva_tarea.codigo_folio} creada con éxito.', 'success')
    return redirect(url_for('dashboard.direccion'))

@tareas_bp.route('/<int:tarea_id>/actualizar-estatus', methods=['POST'])
@login_required
def actualizar_estatus(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)
    nuevo_estatus = request.json.get('estatus') if request.is_json else request.form.get('estatus')

    if nuevo_estatus in ['PENDIENTE', 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO']:
        tarea.estatus = nuevo_estatus
        tarea.fecha_cierre = date.today() if nuevo_estatus == 'COMPLETADO' else None
        
        bitacora = BitacoraTarea(
            tarea_id=tarea.id, usuario_id=current_user.id,
            comentario=f"Cambio de estatus a {nuevo_estatus}.",
            tipo='BLOQUEO' if nuevo_estatus == 'BLOQUEADO' else 'CAMBIO_ESTATUS'
        )
        db.session.add(bitacora)
        db.session.commit()
        return jsonify({'success': True, 'semaforo': tarea.semaforo})

    return jsonify({'success': False}), 400

@tareas_bp.route('/<int:tarea_id>/agregar-nota', methods=['POST'])
@login_required
def agregar_nota(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)

    # Captura tanto si viene en JSON (modal) como en formulario estándar
    if request.is_json:
        comentario = request.json.get('comentario', '').strip()
        tipo = request.json.get('tipo', 'AVANCE')
    else:
        comentario = request.form.get('comentario', '').strip()
        tipo = request.form.get('tipo', 'AVANCE')

    if not comentario:
        if request.is_json:
            return jsonify({'success': False, 'message': 'El comentario no puede estar vacío.'}), 400
        flash('El comentario no puede estar vacío.', 'warning')
        return redirect(request.referrer or url_for('dashboard.direccion'))

    bitacora = BitacoraTarea(
        tarea_id=tarea.id,
        usuario_id=current_user.id,
        comentario=comentario,
        tipo=tipo,
        fecha_registro=datetime.utcnow()  # Se guarda en estándar UTC
    )
    db.session.add(bitacora)
    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Nota registrada con éxito.',
            'tarea_id': tarea.id
        })

    flash('Nota registrada en la bitácora.', 'success')
    return redirect(request.referrer or url_for('dashboard.direccion'))

@tareas_bp.route('/<int:tarea_id>/detalle', methods=['GET'])
@login_required
def detalle(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)
    
    bitacora_lista = []
    for b in tarea.bitacora:
        fecha_mexico = b.fecha_registro - timedelta(hours=6) if b.fecha_registro else datetime.utcnow() - timedelta(hours=6)
        bitacora_lista.append({
            'id': b.id,
            'autor': b.autor.nombre_completo if b.autor else "Sistema",
            'comentario': b.comentario,
            'tipo': b.tipo,
            'fecha': fecha_mexico.strftime('%d/%m/%Y %H:%M hrs')
        })

    # Lista de apoyos estructurada
    dependencias_lista = [d.to_dict() for d in tarea.dependencias]

    return jsonify({
        'id': tarea.id,
        'folio': tarea.codigo_folio or f"TL-{tarea.id}",
        'titulo': tarea.titulo,
        'descripcion': tarea.descripcion or "Sin instrucciones adicionales.",
        'pilar': tarea.pilar.nombre if tarea.pilar else "-",
        'pilar_color': tarea.pilar.color_identificador if tarea.pilar else "#0284c7",
        'responsable': tarea.responsable.nombre_completo if tarea.responsable else "-",
        'prioridad': tarea.prioridad,
        'estatus': tarea.estatus,
        'semaforo': tarea.semaforo,
        'fecha_inicio': tarea.fecha_inicio.strftime('%d/%m/%Y') if tarea.fecha_inicio else "-",
        'fecha_compromiso': tarea.fecha_compromiso.strftime('%d/%m/%Y') if tarea.fecha_compromiso else "-",
        'dependencias': dependencias_lista,
        'bitacora': bitacora_lista
    })