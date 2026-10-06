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
        if not hex_color or not hex_color.startswith('#'):
            return '#ffffff'
        c = hex_color.lstrip('#')
        if len(c) == 6:
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            # Fórmula estándar de luminosidad relativa W3C
            luminosidad = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return '#0f172a' if luminosidad > 0.55 else '#ffffff'
        return '#ffffff'

    app.jinja_env.filters['contraste'] = color_contraste

    return app
