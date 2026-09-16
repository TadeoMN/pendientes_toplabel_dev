from datetime import datetime, date, timedelta
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Tarea, Pilar, Usuario, BitacoraTarea, TareaDependencia

tareas_bp = Blueprint('tareas', __name__, url_prefix='/tareas')

PRIORIDADES = frozenset({'P0_CRITICA', 'P1_ALTA', 'P2_MEDIA', 'P3_BAJA'})
TIPOS_BITACORA = frozenset({'AVANCE', 'BLOQUEO', 'CAMBIO_ESTATUS', 'NOTA_REUNION'})


def _id_formulario(valor, campo, opcional=False):
    if valor is None or valor == '':
        if opcional:
            return None
        raise ValueError(f'{campo} es obligatorio.')
    try:
        identificador = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f'{campo} inválido.') from None
    if identificador <= 0:
        raise ValueError(f'{campo} inválido.')
    return identificador


def _usuario_activo(identificador, campo):
    usuario = db.session.get(Usuario, identificador)
    if usuario is None or not usuario.activo:
        raise ValueError(f'{campo} no existe o está inactivo.')
    return usuario


def _error_formulario(mensaje, volver=False):
    if request.is_json:
        return jsonify({'success': False, 'message': mensaje}), 400
    flash(mensaje, 'warning')
    return redirect((request.referrer if volver else None) or url_for('dashboard.direccion'))


def _error_guardado(mensaje, volver=False):
    db.session.rollback()
    if request.is_json:
        return jsonify({'success': False, 'message': mensaje}), 500
    flash(mensaje, 'danger')
    return redirect((request.referrer if volver else None) or url_for('dashboard.direccion'))


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
    prioridad = request.form.get('prioridad', 'P2_MEDIA')
    fecha_comp_str = request.form.get('fecha_compromiso')

    try:
        if not titulo or not fecha_comp_str:
            raise ValueError('Título, responsable y fecha límite son obligatorios.')
        if len(titulo) > 200:
            raise ValueError('El título no debe superar los 200 caracteres.')
        if prioridad not in PRIORIDADES:
            raise ValueError('Prioridad inválida.')
        try:
            fecha_comp = datetime.strptime(fecha_comp_str, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            raise ValueError('Fecha de compromiso inválida.') from None

        pilar_id = _id_formulario(request.form.get('pilar_id'), 'Pilar', opcional=True)
        responsable_id = _id_formulario(request.form.get('responsable_id'), 'Responsable')
        if pilar_id is not None and db.session.get(Pilar, pilar_id) is None:
            raise ValueError('El pilar seleccionado no existe.')
        _usuario_activo(responsable_id, 'El responsable')
        _usuario_activo(current_user.id, 'El usuario creador')

        # Validar todos los apoyos antes de insertar la tarea. Se permiten varias
        # personas por pilar, pero una misma combinación se guarda una sola vez.
        pilares = request.form.getlist('apoyo_pilar_id[]')
        responsables = request.form.getlist('apoyo_responsable_id[]')
        apoyos = []
        for indice in range(max(len(pilares), len(responsables))):
            p_id = _id_formulario(pilares[indice] if indice < len(pilares) else '',
                                 'Pilar de apoyo', opcional=True)
            r_id = _id_formulario(responsables[indice] if indice < len(responsables) else '',
                                 'Responsable de apoyo', opcional=True)
            if p_id is None:
                if r_id is not None:
                    raise ValueError('Selecciona un pilar para cada responsable de apoyo.')
                continue
            if db.session.get(Pilar, p_id) is None:
                raise ValueError('Un pilar de apoyo seleccionado no existe.')
            if r_id is not None:
                _usuario_activo(r_id, 'El responsable de apoyo')
            if (p_id, r_id) not in apoyos:
                apoyos.append((p_id, r_id))

        folio = generar_folio(pilar_id)
        nueva_tarea = Tarea(
            codigo_folio=folio, titulo=titulo, descripcion=descripcion,
            pilar_id=pilar_id, responsable_id=responsable_id,
            creado_por_id=current_user.id, prioridad=prioridad,
            estatus='PENDIENTE', fecha_inicio=date.today(), fecha_compromiso=fecha_comp,
            fuente='DIRECCION' if current_user.es_direccion else 'INICIATIVA_PROPIA'
        )
        db.session.add(nueva_tarea)
        db.session.flush()
        for p_id, r_id in apoyos:
            db.session.add(TareaDependencia(
                tarea_id=nueva_tarea.id, pilar_id=p_id, responsable_id=r_id))
        db.session.commit()
    except ValueError as error:
        return _error_formulario(str(error))
    except IntegrityError:
        return _error_guardado('No se guardó la tarea. Otra operación pudo cambiar los datos o usar el folio; vuelve a intentarlo.')
    except SQLAlchemyError:
        return _error_guardado('No se pudo guardar la tarea y sus apoyos. Vuelve a intentarlo.')

    flash(f'Tarea {folio} creada con éxito.', 'success')
    return redirect(url_for('dashboard.direccion'))

@tareas_bp.route('/<int:tarea_id>/actualizar-estatus', methods=['POST'])
@login_required
def actualizar_estatus(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)
    data = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(data, 'get'):
        return jsonify({'success': False, 'message': 'Datos inválidos.'}), 400
    nuevo_estatus = data.get('estatus')

    if nuevo_estatus in ['PENDIENTE', 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO']:
        try:
            _usuario_activo(current_user.id, 'El usuario')
            tarea.estatus = nuevo_estatus
            tarea.fecha_cierre = date.today() if nuevo_estatus == 'COMPLETADO' else None
            semaforo = tarea.semaforo
            bitacora = BitacoraTarea(
                tarea_id=tarea.id, usuario_id=current_user.id,
                comentario=f"Cambio de estatus a {nuevo_estatus}.",
                tipo='BLOQUEO' if nuevo_estatus == 'BLOQUEADO' else 'CAMBIO_ESTATUS'
            )
            db.session.add(bitacora)
            db.session.commit()
        except ValueError as error:
            return jsonify({'success': False, 'message': str(error)}), 400
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'No se pudo guardar el cambio de estatus.'}), 500
        return jsonify({'success': True, 'semaforo': semaforo})

    return jsonify({'success': False}), 400

@tareas_bp.route('/<int:tarea_id>/agregar-nota', methods=['POST'])
@login_required
def agregar_nota(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)

    data = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(data, 'get'):
        return _error_formulario('Datos inválidos.', volver=True)
    comentario = data.get('comentario', '')
    tipo = data.get('tipo', 'AVANCE')
    if not isinstance(comentario, str) or not comentario.strip():
        return _error_formulario('El comentario no puede estar vacío.', volver=True)
    if not isinstance(tipo, str) or tipo not in TIPOS_BITACORA:
        return _error_formulario('Tipo de nota inválido.', volver=True)

    try:
        _usuario_activo(current_user.id, 'El usuario')
        bitacora = BitacoraTarea(
            tarea_id=tarea.id, usuario_id=current_user.id,
            comentario=comentario.strip(), tipo=tipo, fecha_registro=datetime.utcnow()
        )
        db.session.add(bitacora)
        db.session.commit()
    except ValueError as error:
        return _error_formulario(str(error), volver=True)
    except SQLAlchemyError:
        return _error_guardado('No se pudo guardar la nota. Vuelve a intentarlo.', volver=True)

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Nota registrada con éxito.',
            'tarea_id': tarea_id
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
    dependencias_lista = tarea.dependencias_info()

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
