from datetime import datetime
from app import db


class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(250), nullable=False, default='')
    activo = db.Column(db.Boolean, nullable=False, default=True)
    es_administrador = db.Column(db.Boolean, nullable=False, default=False)
    permisos = db.relationship('RolPermiso', cascade='all, delete-orphan', backref='rol')


class Permiso(db.Model):
    __tablename__ = 'permisos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)


class RolPermiso(db.Model):
    __tablename__ = 'roles_permisos'
    __table_args__ = (db.UniqueConstraint('rol_id', 'permiso_id', 'alcance', name='uq_rol_permiso_alcance'),)
    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permisos.id'), nullable=False)
    alcance = db.Column(db.String(20), nullable=False, default='sistema')
    permiso = db.relationship('Permiso')


class UsuarioRol(db.Model):
    __tablename__ = 'usuarios_roles'
    __table_args__ = (db.UniqueConstraint('usuario_id', 'rol_id', name='uq_usuario_rol'),)
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    usuario = db.relationship('Usuario', back_populates='roles_sistema')
    rol = db.relationship('Rol')


class AuditoriaSistema(db.Model):
    __tablename__ = 'auditoria_sistema'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    accion = db.Column(db.String(80), nullable=False)
    detalle = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Adjunto(db.Model):
    __tablename__ = 'adjuntos'
    id = db.Column(db.Integer, primary_key=True)
    tarea_id = db.Column(db.Integer, db.ForeignKey('tareas.id'), nullable=True, index=True)
    nota_id = db.Column(db.Integer, db.ForeignKey('bitacora_tareas.id'), nullable=True, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    clave = db.Column(db.String(64), nullable=False, unique=True)
    categoria = db.Column(db.String(20), nullable=False)
    mime = db.Column(db.String(100), nullable=False)
    tamano = db.Column(db.BigInteger, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    retirado = db.Column(db.Boolean, nullable=False, default=False)
    tarea = db.relationship('Tarea', backref='adjuntos')
    nota = db.relationship('BitacoraTarea', backref='adjuntos')


class ConfiguracionArchivos(db.Model):
    __tablename__ = 'configuracion_archivos'
    id = db.Column(db.Integer, primary_key=True)
    valores = db.Column(db.Text, nullable=False)


class TransicionNota(db.Model):
    __tablename__ = 'transiciones_notas'
    id = db.Column(db.Integer, primary_key=True)
    nota_id = db.Column(db.Integer, db.ForeignKey('bitacora_tareas.id'), nullable=False, unique=True)
    estatus_anterior = db.Column(db.String(20), nullable=False)
    estatus_nuevo = db.Column(db.String(20), nullable=False)
    origen = db.Column(db.String(20), nullable=False)
    nota = db.relationship('BitacoraTarea', backref=db.backref('transicion', uselist=False))
