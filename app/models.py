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

    # Usuarios y pilares pueden referenciarse mutuamente durante la transición.
    responsable = db.relationship('Usuario', foreign_keys=[responsable_id], backref='pilar_titular', post_update=True)
    asignaciones = db.relationship('UsuarioPilar', back_populates='pilar', cascade='all, delete-orphan', lazy=True)
    tareas = db.relationship('Tarea', foreign_keys='Tarea.pilar_id', backref='pilar', lazy=True)

    @property
    def miembros(self):
        # La migración solo crea estructura: los usuarios aún no editados
        # conservan su membresía histórica sin insertar filas durante la lectura.
        return Usuario.query.filter(
            Usuario.activo.is_(True),
            db.or_(
                Usuario.asignaciones_pilar.any(pilar_id=self.id),
                Usuario.id == self.responsable_id,
                db.and_(Usuario.pilar_id == self.id,
                        ~Usuario.asignaciones_pilar.any()),
            ),
        ).order_by(Usuario.nombre_completo.asc()).all()

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
    roles_sistema = db.relationship('UsuarioRol', back_populates='usuario', cascade='all, delete-orphan')

    def puede(self, permiso, tarea=None):
        from app.permisos import permite
        return permite(self, permiso, tarea)

    @property
    def es_administrador(self):
        return self.activo and any(a.rol.activo and a.rol.es_administrador for a in self.roles_sistema)

    @property
    def tiene_rol_administrador(self):
        # Protege también cuentas desactivadas frente a cambios de terceros.
        return any(a.rol.es_administrador for a in self.roles_sistema)

    @property
    def nombres_roles(self):
        return ', '.join(a.rol.nombre for a in self.roles_sistema if a.rol.activo)

    asignaciones_pilar = db.relationship('UsuarioPilar', back_populates='usuario', cascade='all, delete-orphan', lazy=True)
    pilar_historico = db.relationship('Pilar', foreign_keys=[pilar_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def es_direccion(self):
        return self.activo and any(a.rol.activo and
            (a.rol.codigo == 'DIRECCION' or a.rol.es_administrador) for a in self.roles_sistema)

    def pilares_info(self):
        """Asignaciones efectivas, con lectura compatible del formato anterior.

        Las filas nuevas prevalecen sobre usuarios.pilar_id. Al editar las
        asignaciones se limpian los campos históricos, incluso al quitar todas.
        La titularidad oficial siempre implica membresía y liderazgo.
        """
        info = {}

        def incluir(pilar, es_lider):
            if pilar is not None:
                anterior = info.get(pilar.id, {})
                info[pilar.id] = {
                    'id': pilar.id,
                    'nombre': pilar.nombre,
                    'color': pilar.color_identificador,
                    'es_lider': bool(es_lider or anterior.get('es_lider')),
                }

        if self.asignaciones_pilar:
            for asignacion in self.asignaciones_pilar:
                incluir(asignacion.pilar, asignacion.es_lider)
        else:
            incluir(self.pilar_historico, self.es_responsable)
        for pilar in self.pilar_titular:
            incluir(pilar, True)
        return sorted(info.values(), key=lambda p: (p['nombre'].casefold(), p['id']))

    def to_dict(self):
        pilares_info = self.pilares_info()
        return {
            'id': self.id,
            'nombre_completo': self.nombre_completo,
            'rol_sistema_id': self.roles_sistema[0].rol_id if len(self.roles_sistema) == 1 else None,
            'username': self.username,
            'email': self.email,
            'rol': self.rol,
            'pilares': pilares_info,
            'tiene_pilares': len(pilares_info) > 0,  # <-- Flag para identificar usuarios sin pilar
            'activo': self.activo
        }

class UsuarioPilar(db.Model):
    __tablename__ = 'usuarios_pilares'
    __table_args__ = (db.UniqueConstraint('usuario_id', 'pilar_id', name='uq_usuario_pilar'),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    pilar_id = db.Column(db.Integer, db.ForeignKey('pilares.id', ondelete='CASCADE'), nullable=False)
    es_lider = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.text('CURRENT_TIMESTAMP'))

    pilar = db.relationship('Pilar', foreign_keys=[pilar_id], back_populates='asignaciones')
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], back_populates='asignaciones_pilar')

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

    def dependencias_info(self):
        if self.dependencias:
            return [dependencia.to_dict() for dependencia in self.dependencias]
        if self.pilar_dependencia is not None:
            return [{
                'id': None,
                'pilar_id': self.pilar_dependencia.id,
                'pilar_nombre': self.pilar_dependencia.nombre,
                'pilar_color': self.pilar_dependencia.color_identificador,
                'responsable_id': None,
                'responsable_nombre': 'Sin asignar (Área general)',
            }]
        return []

    def to_dict(self):
        """Representación usada por la API, también para tareas históricas."""
        return {
            'id': self.id,
            'codigo_folio': self.codigo_folio,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'pilar_id': self.pilar_id,
            'pilar': self.pilar.nombre if self.pilar else None,
            'responsable_id': self.responsable_id,
            'responsable': self.responsable.nombre_completo if self.responsable else None,
            'creado_por_id': self.creado_por_id,
            'prioridad': self.prioridad,
            'estatus': self.estatus,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_compromiso': self.fecha_compromiso.isoformat() if self.fecha_compromiso else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'fuente': self.fuente,
            'semaforo': self.semaforo,
            'dependencias': self.dependencias_info(),
        }

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
