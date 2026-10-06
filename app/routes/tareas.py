from datetime import datetime, date, timedelta
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.permisos import exigir, puede_asignar
from app.archivos import guardar_archivos, limpiar_archivos, datos_adjunto
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException
from app.models import Tarea, Pilar, Usuario, BitacoraTarea, TareaDependencia
from app.routes.edicion_tareas import aplicar_edicion, version_tarea, opciones_edicion

tareas_bp = Blueprint('tareas', __name__, url_prefix='/tareas')

PRIORIDADES = frozenset({'P0_CRITICA', 'P1_ALTA', 'P2_MEDIA', 'P3_BAJA'})



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


def _destino_formulario():
    return url_for('dashboard.mis_pendientes' if request.form.get('volver') == 'mis_pendientes' else 'dashboard.index')


def _error_formulario(mensaje, volver=False):
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': mensaje}), 400
    flash(mensaje, 'warning')
    return redirect(_destino_formulario())


def _error_guardado(mensaje, volver=False):
    db.session.rollback()
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': mensaje}), 500
    flash(mensaje, 'danger')
    return redirect(_destino_formulario())


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
    exigir('tareas.crear')
    creados = []
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
        responsable = _usuario_activo(responsable_id, 'El responsable')
        if not puede_asignar(current_user, responsable):
            from flask import abort
            abort(403)
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
        if any(f.filename for f in request.files.getlist('archivos')):
            exigir('archivos.subir', nueva_tarea)
            guardar_archivos(request.files.getlist('archivos'), current_user.id, tarea=nueva_tarea, creados=creados)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        limpiar_archivos(creados)
        return _error_formulario(str(error))
    except IntegrityError:
        limpiar_archivos(creados)
        return _error_guardado('No se guardó la tarea. Otra operación pudo cambiar los datos o usar el folio; vuelve a intentarlo.')
    except (SQLAlchemyError, OSError):
        limpiar_archivos(creados)
        return _error_guardado('No se pudo guardar la tarea y sus apoyos. Vuelve a intentarlo.')

    flash(f'Tarea {folio} creada con éxito.', 'success')
    return redirect(_destino_formulario())

def guardar_nota_o_estatus(tarea_id, cambio_estatus=False):
    from app.notas import registrar_nota
    creados = []
    try:
        tarea = Tarea.query.filter_by(id=tarea_id).with_for_update().populate_existing().first_or_404()
        exigir('tareas.ver', tarea)
        exigir('tareas.estatus' if cambio_estatus else 'notas.crear', tarea)
        data = request.get_json(silent=True) if request.is_json else request.form
        if not hasattr(data, 'get'):
            raise ValueError('Datos inválidos.')
        nuevo = data.get('estatus') or None
        if cambio_estatus and not nuevo:
            raise ValueError('Selecciona el nuevo estatus.')
        if nuevo and data.get('version') != version_tarea(tarea):
            return jsonify(success=False, message='La tarea cambió. Actualiza su detalle antes de guardar.'), 409
        nota = registrar_nota(tarea, current_user.id, data.get('tipo', 'AVANCE'),
                              data.get('comentario', data.get('nota', '')), nuevo,
                              'ESTATUS' if cambio_estatus else 'NOTA')
        db.session.flush()
        if any(f.filename for f in request.files.getlist('archivos')):
            exigir('archivos.subir', tarea)
            guardar_archivos(request.files.getlist('archivos'), current_user.id, nota=nota, creados=creados)
        db.session.commit()
        return jsonify(success=True, tarea_id=tarea.id, estatus=tarea.estatus, semaforo=tarea.semaforo)
    except HTTPException:
        db.session.rollback()
        limpiar_archivos(creados)
        raise
    except ValueError as error:
        db.session.rollback()
        limpiar_archivos(creados)
        return jsonify(success=False, message=str(error)), 400
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        limpiar_archivos(creados)
        return jsonify(success=False, message='No se guardó la operación. Inténtalo nuevamente.'), 500


@tareas_bp.route('/<int:tarea_id>/actualizar-estatus', methods=['POST'])
@login_required
def actualizar_estatus(tarea_id):
    return guardar_nota_o_estatus(tarea_id, cambio_estatus=True)


@tareas_bp.route('/<int:tarea_id>/agregar-nota', methods=['POST'])
@login_required
def agregar_nota(tarea_id):
    return guardar_nota_o_estatus(tarea_id)

@tareas_bp.route('/<int:tarea_id>/editar', methods=['POST'])
@login_required
def editar(tarea_id):
    try:
        tarea = Tarea.query.filter_by(id=tarea_id).with_for_update().populate_existing().first_or_404()
        exigir('tareas.ver', tarea)
        exigir('tareas.editar', tarea)
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify(success=False, message='Datos inválidos.'), 400
        if datos.get('version') != version_tarea(tarea):
            return jsonify(success=False, message='La tarea cambió desde que abriste el detalle. Cierra y vuelve a abrir el detalle para revisar la versión actual.'), 409
        responsable_id = datos.get('responsable_id')
        if type(responsable_id) is not int or responsable_id <= 0:
            raise ValueError('Responsable inválido.')
        if responsable_id != tarea.responsable_id:
            responsable = db.session.get(Usuario, datos.get('responsable_id'))
            if responsable is not None and not puede_asignar(current_user, responsable):
                from flask import abort
                abort(403)
        modificado = aplicar_edicion(tarea, datos, current_user.id)
        db.session.commit()
        return jsonify(success=True, modificado=modificado)
    except ValueError as error:
        db.session.rollback()
        return jsonify(success=False, message=str(error)), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(success=False, message='No se guardaron los cambios. Inténtalo nuevamente.'), 500


@tareas_bp.route('/<int:tarea_id>/detalle', methods=['GET'])
@login_required
def detalle(tarea_id):
    tarea = Tarea.query.get_or_404(tarea_id)
    exigir('tareas.ver', tarea)
    puede_editar = current_user.puede('tareas.editar', tarea)
    
    bitacora_lista = []
    for b in (tarea.bitacora if current_user.puede('notas.ver', tarea) else []):
        fecha_mexico = b.fecha_registro - timedelta(hours=6) if b.fecha_registro else datetime.utcnow() - timedelta(hours=6)
        bitacora_lista.append({
            'id': b.id,
            'transicion': {'anterior': b.transicion.estatus_anterior, 'nuevo': b.transicion.estatus_nuevo, 'origen': b.transicion.origen} if b.transicion else None,
            'adjuntos': [datos_adjunto(a) for a in b.adjuntos if not a.retirado] if current_user.puede('archivos.ver', tarea) else [],
            'autor': b.autor.nombre_completo if b.autor else "Sistema",
            'comentario': b.comentario,
            'tipo': 'MODIFICACION' if b.comentario.startswith('Modificación de tarea:\n') else b.tipo,
            'fecha': fecha_mexico.strftime('%d/%m/%Y %H:%M hrs')
        })

    # Lista de apoyos estructurada
    dependencias_lista = tarea.dependencias_info()

    return jsonify({
        'id': tarea.id,
        'puede_editar': puede_editar,
        'puede_estatus': current_user.puede('tareas.estatus', tarea),
        'puede_notar': current_user.puede('notas.crear', tarea),
        'puede_subir': current_user.puede('archivos.subir', tarea),
        'puede_retirar': current_user.puede('archivos.retirar', tarea),
        'puede_descargar': current_user.puede('archivos.descargar', tarea),
        'adjuntos': [datos_adjunto(a) for a in tarea.adjuntos if not a.retirado] if current_user.puede('archivos.ver', tarea) else [],
        'version': version_tarea(tarea),
        'campos': tarea.to_dict() if puede_editar else None,
        'opciones': opciones_edicion() if puede_editar else None,
        'fecha_creacion': (tarea.created_at - timedelta(hours=6)).strftime('%d/%m/%Y %H:%M') if tarea.created_at else '-',
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
