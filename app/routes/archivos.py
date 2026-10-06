import json
from flask import Blueprint, request, jsonify, send_file, abort, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Tarea, BitacoraTarea
from app.modelos_acceso import Adjunto, ConfiguracionArchivos
from app.permisos import exigir, auditar
from app.archivos import guardar_archivos, limpiar_archivos, ruta, datos_adjunto, limites, LIMITES

archivos_bp = Blueprint('archivos', __name__, url_prefix='/archivos')


@archivos_bp.route('/<int:archivo_id>/descargar')
@login_required
def descargar(archivo_id):
    adjunto = db.get_or_404(Adjunto, archivo_id)
    tarea = adjunto.tarea if adjunto.tarea_id else adjunto.nota.tarea
    exigir('tareas.ver', tarea)
    exigir('archivos.ver', tarea)
    exigir('archivos.descargar', tarea)
    if adjunto.nota_id:
        exigir('notas.ver', tarea)
    if adjunto.retirado or not ruta(adjunto.clave).is_file():
        abort(404)
    respuesta = send_file(ruta(adjunto.clave), mimetype=adjunto.mime, as_attachment=True, download_name=adjunto.nombre, conditional=True)
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
    respuesta.headers['Cache-Control'] = 'private, no-store'
    return respuesta


@archivos_bp.route('/tarea/<int:tarea_id>', methods=['POST'])
@login_required
def subir(tarea_id):
    creados = []
    try:
        tarea = Tarea.query.filter_by(id=tarea_id).with_for_update().first_or_404()
        exigir('tareas.ver', tarea)
        exigir('archivos.subir', tarea)
        guardar_archivos(request.files.getlist('archivos'), current_user.id, tarea=tarea, creados=creados)
        if not creados:
            raise ValueError('Selecciona al menos un archivo.')
        db.session.add(BitacoraTarea(tarea_id=tarea.id, usuario_id=current_user.id, tipo='AVANCE', comentario=f'Se adjuntaron {len(creados)} archivo(s) a la tarea.'))
        db.session.commit()
        return jsonify(success=True)
    except ValueError as e:
        db.session.rollback()
        limpiar_archivos(creados)
        return jsonify(success=False, message=str(e)), 400
    except Exception:
        db.session.rollback()
        limpiar_archivos(creados)
        raise


@archivos_bp.route('/<int:archivo_id>/retirar', methods=['POST'])
@login_required
def retirar(archivo_id):
    adjunto = db.get_or_404(Adjunto, archivo_id)
    tarea = adjunto.tarea if adjunto.tarea_id else adjunto.nota.tarea
    exigir('tareas.ver', tarea)
    exigir('archivos.retirar', tarea)
    if adjunto.nota_id:
        exigir('notas.ver', tarea)
    Tarea.query.filter_by(id=tarea.id).with_for_update().one()
    if not adjunto.retirado:
        adjunto.retirado = True
        db.session.add(BitacoraTarea(tarea_id=tarea.id, usuario_id=current_user.id, tipo='AVANCE', comentario=f'Archivo retirado: {adjunto.nombre}.'))
        auditar('archivos.retirar', f'Adjunto {adjunto.id}; tarea {tarea.id}.')
        db.session.commit()
    return jsonify(success=True)


@archivos_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configurar():
    exigir('archivos.configurar')
    if request.method == 'POST':
        try:
            nuevos = {categoria: [int(request.form[categoria + '_cantidad']), int(request.form[categoria + '_mb'])] for categoria in LIMITES}
            if any(not 1 <= v[0] <= 100 or not 1 <= v[1] <= 1024 for v in nuevos.values()):
                raise ValueError('Cantidad: 1–100; tamaño: 1–1024 MB.')
            anteriores = limites()
            row = db.session.get(ConfiguracionArchivos, 1)
            if row is None:
                row = ConfiguracionArchivos(id=1)
                db.session.add(row)
            auditar('archivos.limites', json.dumps({'antes': anteriores, 'despues': nuevos}))
            row.valores = json.dumps(nuevos)
            db.session.commit()
            flash('Límites guardados para nuevas cargas.', 'success')
            return redirect(url_for('archivos.configurar'))
        except (ValueError, KeyError) as error:
            db.session.rollback()
            flash(str(error), 'warning')
    return render_template('admin/archivos.html', limites=limites())
