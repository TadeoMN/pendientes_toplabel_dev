from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder.'
    login_manager.login_message_category = 'warning'

    from app.models import Usuario

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