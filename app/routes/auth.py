from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.direccion' if current_user.es_direccion else 'dashboard.mis_pendientes'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        usuario = Usuario.query.filter((Usuario.username == username) | (Usuario.email == username)).first()

        if usuario and usuario.activo and usuario.check_password(password):
            login_user(usuario, remember=True)
            flash(f'¡Bienvenido, {usuario.nombre_completo}!', 'success')
            return redirect(url_for('dashboard.direccion' if usuario.es_direccion else 'dashboard.mis_pendientes'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))