from flask import Flask, request, session, abort, jsonify
import os
import secrets
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config is not None:
        # Aplicar antes de crear el motor permite pruebas aisladas sin tocar MySQL.
        app.config.update(test_config)

    app.config.setdefault('UPLOAD_ROOT', os.getenv('UPLOAD_ROOT') or str(Path(app.root_path).parent.parent / 'archivos_pendientes' / app.config['DB_NAME']))
    if app.config.get('MAX_CONTENT_LENGTH') is None:
        app.config['MAX_CONTENT_LENGTH'] = 1030 * 1024 * 1024

    @app.before_request
    def proteger_formularios():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and not request.path.startswith('/api/v1/') and not app.config['TESTING']:
            esperado = session.get('csrf_token')
            recibido = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not esperado or not recibido or not secrets.compare_digest(esperado, recibido):
                abort(400, description='Formulario caducado. Actualiza la página e inténtalo nuevamente.')

    @app.context_processor
    def token_formulario():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return {'csrf_token': session['csrf_token']}

    @app.errorhandler(403)
    def prohibido(error):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message='No tienes permiso para realizar esta acción.'), 403
        return 'No tienes permiso para acceder a esta función.', 403

    @app.errorhandler(413)
    def carga_grande(error):
        return jsonify(success=False, message='La carga supera el límite de tamaño del servidor.'), 413

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder.'
    login_manager.login_message_category = 'warning'

    from app.models import Usuario
    from app import modelos_acceso

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tareas import tareas_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tareas_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    from app.routes.roles import roles_bp
    from app.routes.archivos import archivos_bp
    app.register_blueprint(roles_bp)
    app.register_blueprint(archivos_bp)

    # Filtro Jinja para calcular contraste de texto (blanco o negro) según el fondo
    def color_contraste(hex_color):
        oscuro = '#0f172a'
        if not isinstance(hex_color, str) or not hex_color.startswith('#'):
            return oscuro
        c = hex_color[1:]
        if len(c) not in (3, 6) or any(ch not in '0123456789abcdefABCDEF' for ch in c):
            return oscuro
        if len(c) == 3:
            c = ''.join(ch * 2 for ch in c)

        def luminancia(color):
            canales = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            lineales = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in canales]
            return sum(v * peso for v, peso in zip(lineales, (0.2126, 0.7152, 0.0722)))

        fondo = luminancia(c)
        texto_oscuro = luminancia(oscuro[1:])
        contraste_blanco = 1.05 / (fondo + 0.05)
        contraste_oscuro = (max(fondo, texto_oscuro) + 0.05) / (min(fondo, texto_oscuro) + 0.05)
        if max(contraste_blanco, contraste_oscuro) < 4.5:
            return '#000000'
        return '#ffffff' if contraste_blanco >= contraste_oscuro else oscuro

    app.jinja_env.filters['contraste'] = color_contraste

    return app
