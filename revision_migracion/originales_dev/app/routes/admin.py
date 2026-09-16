from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Usuario, Pilar, UsuarioPilar

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def verificar_acceso_direccion():
    if not current_user.es_direccion:
        flash('Acceso restringido únicamente para el área de Dirección.', 'danger')
        return redirect(url_for('dashboard.index'))

# ==========================================================
# CRUD DE USUARIOS (FILAS DINÁMICAS DE PILARES)
# ==========================================================

@admin_bp.route('/usuarios')
def usuarios():
    lista_usuarios = Usuario.query.order_by(Usuario.nombre_completo.asc()).all()
    lista_pilares = Pilar.query.order_by(Pilar.nombre.asc()).all()
    return render_template('admin/usuarios.html', usuarios=lista_usuarios, pilares=lista_pilares)

@admin_bp.route('/usuarios/crear', methods=['POST'])
def crear_usuario():
    nombre = request.form.get('nombre_completo', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip() or None
    password = request.form.get('password', '').strip()
    rol = request.form.get('rol', 'COLABORADOR')

    if not nombre or not username or not password:
        flash('Nombre completo, usuario y contraseña son obligatorios.', 'warning')
        return redirect(url_for('admin.usuarios'))

    if Usuario.query.filter_by(username=username).first():
        flash(f'El usuario @{username} ya está registrado.', 'danger')
        return redirect(url_for('admin.usuarios'))

    if email and Usuario.query.filter_by(email=email).first():
        flash(f'El correo {email} ya pertenece a otro usuario.', 'danger')
        return redirect(url_for('admin.usuarios'))

    nuevo = Usuario(
        nombre_completo=nombre,
        username=username,
        email=email,
        rol=rol,
        activo=True
    )
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.commit()

    # Procesar filas dinámicas de pilares
    pilares_ids = request.form.getlist('usuario_pilar_id[]')
    roles_pilares = request.form.getlist('usuario_rol_pilar[]')
    pilares_vistos = set()

    for i in range(len(pilares_ids)):
        p_id_str = pilares_ids[i]
        if p_id_str:
            p_id = int(p_id_str)
            if p_id in pilares_vistos:
                continue
            pilares_vistos.add(p_id)

            es_lider = (roles_pilares[i] == 'LIDER') if i < len(roles_pilares) else False
            asig = UsuarioPilar(usuario_id=nuevo.id, pilar_id=p_id, es_lider=es_lider)
            db.session.add(asig)

            # Si se designó como líder y el pilar no tiene titular, asignarlo
            if es_lider:
                pilar = Pilar.query.get(p_id)
                if pilar and not pilar.responsable_id:
                    pilar.responsable_id = nuevo.id

    db.session.commit()
    flash(f'Usuario {nuevo.nombre_completo} registrado exitosamente.', 'success')
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/usuarios/<int:usuario_id>/editar', methods=['POST'])
def editar_usuario(usuario_id):
    u = Usuario.query.get_or_404(usuario_id)
    u.nombre_completo = request.form.get('nombre_completo', '').strip()
    u.username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip() or None
    u.rol = request.form.get('rol', u.rol)
    u.activo = request.form.get('activo') == '1'

    if email:
        duplicado = Usuario.query.filter(Usuario.email == email, Usuario.id != u.id).first()
        if duplicado:
            flash(f'El correo {email} ya está en uso.', 'danger')
            return redirect(url_for('admin.usuarios'))

    u.email = email

    # Reemplazar asignaciones en la tabla intermedia
    UsuarioPilar.query.filter_by(usuario_id=u.id).delete()

    pilares_ids = request.form.getlist('usuario_pilar_id[]')
    roles_pilares = request.form.getlist('usuario_rol_pilar[]')
    pilares_vistos = set()

    for i in range(len(pilares_ids)):
        p_id_str = pilares_ids[i]
        if p_id_str:
            p_id = int(p_id_str)
            if p_id in pilares_vistos:
                continue
            pilares_vistos.add(p_id)

            es_lider = (roles_pilares[i] == 'LIDER') if i < len(roles_pilares) else False
            asig = UsuarioPilar(usuario_id=u.id, pilar_id=p_id, es_lider=es_lider)
            db.session.add(asig)

            if es_lider:
                pilar = Pilar.query.get(p_id)
                if pilar and not pilar.responsable_id:
                    pilar.responsable_id = u.id

    db.session.commit()
    flash(f'Datos de {u.nombre_completo} actualizados.', 'success')
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/usuarios/<int:usuario_id>/password', methods=['POST'])
def cambiar_password(usuario_id):
    u = Usuario.query.get_or_404(usuario_id)
    nueva_pass = request.form.get('password', '').strip()
    if not nueva_pass:
        flash('La contraseña no puede estar vacía.', 'warning')
    else:
        u.set_password(nueva_pass)
        db.session.commit()
        flash(f'Contraseña actualizada para @{u.username}.', 'success')
    return redirect(url_for('admin.usuarios'))

# ==========================================================
# CRUD DE PILARES (CON SINCRONIZACIÓN AUTOMÁTICA EN TABLA INTERMEDIA)
# ==========================================================

@admin_bp.route('/pilares')
def pilares():
    lista_pilares = Pilar.query.order_by(Pilar.nombre.asc()).all()
    lista_usuarios = Usuario.query.filter_by(activo=True).order_by(Usuario.nombre_completo.asc()).all()
    return render_template('admin/pilares.html', pilares=lista_pilares, usuarios=lista_usuarios)

@admin_bp.route('/pilares/crear', methods=['POST'])
def crear_pilar():
    nombre = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    color = request.form.get('color_identificador', '#2563eb')
    responsable_id = request.form.get('responsable_id', type=int) or None

    if not nombre:
        flash('El nombre del pilar es obligatorio.', 'warning')
        return redirect(url_for('admin.pilares'))

    if Pilar.query.filter_by(nombre=nombre).first():
        flash('Ya existe un pilar con ese nombre.', 'danger')
        return redirect(url_for('admin.pilares'))

    nuevo = Pilar(
        nombre=nombre,
        descripcion=descripcion,
        color_identificador=color,
        responsable_id=responsable_id
    )
    db.session.add(nuevo)
    db.session.commit()

    # Sincronizar automáticamente en la tabla intermedia
    if responsable_id:
        asig = UsuarioPilar(usuario_id=responsable_id, pilar_id=nuevo.id, es_lider=True)
        db.session.add(asig)
        db.session.commit()

    flash(f'Pilar {nuevo.nombre} registrado con éxito.', 'success')
    return redirect(url_for('admin.pilares'))

@admin_bp.route('/pilares/<int:pilar_id>/editar', methods=['POST'])
def editar_pilar(pilar_id):
    p = Pilar.query.get_or_404(pilar_id)
    p.nombre = request.form.get('nombre', '').strip()
    p.descripcion = request.form.get('descripcion', '').strip()
    p.color_identificador = request.form.get('color_identificador', p.color_identificador)
    
    nuevo_resp_id = request.form.get('responsable_id', type=int) or None

    p.responsable_id = nuevo_resp_id

    # Sincronización en tabla intermedia: asegurar que este usuario exista en UsuarioPilar como Líder
    if nuevo_resp_id:
        asig = UsuarioPilar.query.filter_by(usuario_id=nuevo_resp_id, pilar_id=p.id).first()
        if not asig:
            asig = UsuarioPilar(usuario_id=nuevo_resp_id, pilar_id=p.id, es_lider=True)
            db.session.add(asig)
        else:
            asig.es_lider = True

    db.session.commit()
    flash(f'Pilar {p.nombre} actualizado correctamente.', 'success')
    return redirect(url_for('admin.pilares'))

@admin_bp.route('/pilares/<int:pilar_id>/miembros', methods=['GET'])
def miembros_pilar(pilar_id):
    pilar = Pilar.query.get_or_404(pilar_id)
    miembros_lista = []

    # Extraer todos los miembros desde la relación N:M
    for asig in pilar.asignaciones:
        u = asig.usuario
        if u and u.activo:
            miembros_lista.append({
                'id': u.id,
                'nombre_completo': u.nombre_completo,
                'username': u.username,
                'email': u.email,
                'es_responsable': asig.es_lider
            })

    # Respaldo: si el titular no estuviera en asignaciones por alguna razón histórica
    if pilar.responsable and pilar.responsable.activo:
        ids_existentes = [m['id'] for m in miembros_lista]
        if pilar.responsable.id not in ids_existentes:
            miembros_lista.insert(0, {
                'id': pilar.responsable.id,
                'nombre_completo': pilar.responsable.nombre_completo,
                'username': pilar.responsable.username,
                'email': pilar.responsable.email,
                'es_responsable': True
            })

    return jsonify({
        'pilar': pilar.nombre,
        'color': pilar.color_identificador,
        'miembros': miembros_lista
    })