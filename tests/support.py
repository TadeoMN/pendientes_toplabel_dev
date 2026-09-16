from datetime import date
import unittest
from flask import g
from sqlalchemy import event
from app import create_app, db
from app.models import Usuario, Pilar, Tarea


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'only-for-isolated-tests',
            'API_AUTH_TOKEN': 'only-for-isolated-tests',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_ENGINE_OPTIONS': {},
        })
        self.context = self.app.app_context()
        self.context.push()
        @event.listens_for(db.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        db.create_all()
        self.client = self.app.test_client()
        self.admin = self.user('direccion', rol='DIRECCION')

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def user(self, name, **fields):
        usuario = Usuario(username=name, nombre_completo=name,
            password_hash='fixture-not-an-authentication-secret', activo=True, **fields)
        db.session.add(usuario)
        db.session.commit()
        return usuario

    def pilar(self, name):
        pilar = Pilar(nombre=name)
        db.session.add(pilar)
        db.session.commit()
        return pilar

    def tarea(self, title, **fields):
        tarea = Tarea(titulo=title, responsable_id=self.admin.id,
            creado_por_id=self.admin.id, fecha_compromiso=date(2030, 1, 1), **fields)
        db.session.add(tarea)
        db.session.commit()
        return tarea

    def login(self, usuario):
        with self.client.session_transaction() as session:
            session['_user_id'] = str(usuario.id)
            session['_fresh'] = True
        g.pop('_login_user', None)
