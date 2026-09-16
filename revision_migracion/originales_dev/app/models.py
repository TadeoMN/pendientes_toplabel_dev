from datetime import datetime, date, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Pilar(db.Model):
    __tablename__ = 'pilares'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(150), nullable=True)
    color_identificador = db.Column(db.String(7), default='#2563eb')
    responsable_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)

    responsable = db.relationship('Usuario', foreign_keys=[responsable_id], backref='pilar_titular')
    asignaciones = db.relationship('UsuarioPilar', backref='pilar_rel', cascade='all, delete-orphan', lazy=True)
    tareas = db.relationship('Tarea', foreign_keys='Tarea.pilar_id', backref='pilar', lazy=True)

    @property
    def miembros(self):
        return [a.usuario for a in self.asignaciones if a.usuario and a.usuario.activo]

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'color': self.color_identificador,
            'responsable': self.responsable.nombre_completo if self.responsable else 'Sin asignar'
        }

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='COLABORADOR')
    pilar_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='SET NULL'), nullable=True)
    es_responsable = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)

    asignaciones_pilar = db.relationship('UsuarioPilar', backref='usuario_rel', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def es_direccion(self):
        return self.rol == 'DIRECCION'

    def to_dict(self):
        pilares_info = []
        pilar_ids_vistos = set()

        # 1. Asignaciones desde la tabla intermedia
        for a in self.asignaciones_pilar:
            if a.pilar:
                pilares_info.append({
                    'id': a.pilar.id,
                    'nombre': a.pilar.nombre,
                    'color': a.pilar.color_identificador,
                    'es_lider': a.es_lider
                })
                pilar_ids_vistos.add(a.pilar.id)

        # 2. Respaldo directo: Si es titular oficial del pilar (pilar.responsable_id == usuario.id)
        for p in self.pilar_titular:
            if p.id not in pilar_ids_vistos:
                pilares_info.append({
                    'id': p.id,
                    'nombre': p.nombre,
                    'color': p.color_identificador,
                    'es_lider': True
                })
                pilar_ids_vistos.add(p.id)

        return {
            'id': self.id,
            'nombre_completo': self.nombre_completo,
            'username': self.username,
            'email': self.email,
            'rol': self.rol,
            'pilares': pilares_info,
            'tiene_pilares': len(pilares_info) > 0,  # <-- Flag para identificar usuarios sin pilar
            'activo': self.activo
        }

class UsuarioPilar(db.Model):
    __tablename__ = 'usuarios_pilares'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    pilar_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='CASCADE'), nullable=False)
    es_lider = db.Column(db.Boolean, default=False)

    pilar = db.relationship('Pilar', foreign_keys=[pilar_id])
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id])    

class Tarea(db.Model):
    __tablename__ = 'tareas'

    id = db.Column(db.Integer, primary_key=True)
    codigo_folio = db.Column(db.String(20), unique=True, nullable=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    pilar_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='SET NULL'), nullable=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    creado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    prioridad = db.Column(db.String(20), default='P2_MEDIA')
    estatus = db.Column(db.String(20), default='PENDIENTE')
    
    fecha_inicio = db.Column(db.Date, nullable=False, default=date.today)
    fecha_compromiso = db.Column(db.Date, nullable=False)
    fecha_cierre = db.Column(db.Date, nullable=True)
    
    fuente = db.Column(db.String(30), default='DIRECCION')
    pilar_dependencia_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='SET NULL'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    responsable = db.relationship('Usuario', foreign_keys=[responsable_id], backref='tareas_asignadas')
    creador = db.relationship('Usuario', foreign_keys=[creado_por_id], backref='tareas_creadas')
    pilar_dependencia = db.relationship('Pilar', foreign_keys=[pilar_dependencia_id])
    dependencias = db.relationship('TareaDependencia', backref='tarea', cascade='all, delete-orphan', lazy=True)
    bitacora = db.relationship('BitacoraTarea', backref='tarea', cascade='all, delete-orphan', lazy=True, order_by='BitacoraTarea.fecha_registro.desc()')

    @property
    def semaforo(self):
        if self.estatus == 'COMPLETADO':
            return 'VERDE'
        if self.estatus == 'BLOQUEADO':
            return 'ROJO'
        
        hoy = date.today()
        if self.fecha_compromiso < hoy:
            return 'ROJO'
        elif self.fecha_compromiso <= (hoy + timedelta(days=2)):
            return 'AMARILLO'
        else:
            return 'AZUL'

class BitacoraTarea(db.Model):
    __tablename__ = 'bitacora_tareas'

    id = db.Column(db.Integer, primary_key=True)
    tarea_id = db.Column(db.Integer, db.ForeignKey('tareas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    comentario = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default='AVANCE')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    autor = db.relationship('Usuario', foreign_keys=[usuario_id])

class TareaDependencia(db.Model):
    __tablename__ = 'tareas_dependencias'

    id = db.Column(db.Integer, primary_key=True)
    tarea_id = db.Column(db.Integer, db.ForeignKey('tareas.id', ondelete='CASCADE'), nullable=False)
    pilar_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='CASCADE'), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)

    pilar = db.relationship('Pilar', foreign_keys=[pilar_id])
    responsable = db.relationship('Usuario', foreign_keys=[responsable_id])

    def to_dict(self):
        return {
            'id': self.id,
            'pilar_id': self.pilar_id,
            'pilar_nombre': self.pilar.nombre if self.pilar else '',
            'pilar_color': self.pilar.color_identificador if self.pilar else '#0284c7',
            'responsable_id': self.responsable_id,
            'responsable_nombre': self.responsable.nombre_completo if self.responsable else 'Sin asignar (Área general)'
        }