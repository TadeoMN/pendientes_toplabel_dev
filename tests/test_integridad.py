from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Usuario, Pilar, UsuarioPilar, Tarea, TareaDependencia, BitacoraTarea
from tests.support import AppTestCase


def fallo_relacion(*args):
    raise IntegrityError('fixture', {}, Exception('fallo simulado'))


class AsignacionesTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.a, self.b, self.c = [self.pilar(n) for n in ['Calidad', 'Sistemas', 'Ventas']]
        self.usuario = self.user('colaborador', pilar_id=self.a.id)
        self.login(self.admin)

    def editar(self, pares):
        return self.client.post(f'/admin/usuarios/{self.usuario.id}/editar', data={
            'nombre_completo': self.usuario.nombre_completo, 'username': self.usuario.username,
            'email': '', 'rol': 'COLABORADOR', 'activo': '1',
            'usuario_pilar_id[]': [str(p[0]) for p in pares],
            'usuario_rol_pilar[]': [p[1] for p in pares],
        })

    def test_lectura_legacy_sin_insertar_relaciones(self):
        self.a.responsable = self.usuario
        db.session.commit()
        self.assertEqual(self.usuario.pilares_info()[0]['id'], self.a.id)
        self.assertTrue(self.usuario.pilares_info()[0]['es_lider'])
        self.assertEqual(UsuarioPilar.query.count(), 0)
        response = self.client.get(f'/admin/pilares/{self.a.id}/miembros')
        self.assertEqual(response.json['miembros'][0]['id'], self.usuario.id)
        self.assertEqual(UsuarioPilar.query.count(), 0)
        for ruta in ['/admin/usuarios', '/admin/pilares', '/dashboard']:
            self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_nuevo_usuario_multipilar_y_edicion_repetida(self):
        response = self.client.post('/admin/usuarios/crear', data={
            'nombre_completo': 'Nuevo', 'username': 'nuevo', 'password': 'fixture-password',
            'usuario_pilar_id[]': [str(self.a.id), str(self.b.id)],
            'usuario_rol_pilar[]': ['LIDER', 'COLABORADOR'],
        })
        self.assertEqual(response.status_code, 302)
        nuevo = Usuario.query.filter_by(username='nuevo').one()
        self.assertEqual(len(nuevo.pilares_info()), 2)
        self.assertEqual(self.a.responsable_id, nuevo.id)
        self.usuario = nuevo
        self.editar([(self.a.id, 'LIDER'), (self.b.id, 'COLABORADOR')])
        self.assertEqual(UsuarioPilar.query.filter_by(usuario_id=nuevo.id).count(), 2)

    def test_reasignacion_deja_de_ver_pilar_antiguo(self):
        self.tarea('Solo Calidad', pilar_id=self.a.id)
        self.tarea('Solo Sistemas', pilar_id=self.b.id)
        self.tarea('Solo Ventas', pilar_id=self.c.id)
        directa = self.tarea('Asignada directamente')
        directa.responsable_id = self.usuario.id
        db.session.commit()
        self.editar([(self.b.id, 'COLABORADOR'), (self.c.id, 'COLABORADOR')])
        self.assertIsNone(self.usuario.pilar_id)
        self.login(self.usuario)
        html = self.client.get('/mis-pendientes').get_data(as_text=True)
        self.assertNotIn('Solo Calidad', html)
        self.assertIn('Solo Sistemas', html)
        self.assertIn('Solo Ventas', html)
        self.assertIn('Asignada directamente', html)

    def test_ultima_asignacion_y_titular_no_resucitan(self):
        self.a.responsable = self.usuario
        self.usuario.es_responsable = True
        db.session.commit()
        self.editar([])
        db.session.expire_all()
        self.assertIsNone(self.a.responsable_id)
        self.assertIsNone(self.usuario.pilar_id)
        self.assertEqual(self.usuario.pilares_info(), [])
        self.assertNotIn(self.usuario, self.a.miembros)

    def test_degradar_titular_conserva_membresia(self):
        self.a.responsable = self.usuario
        db.session.commit()
        self.editar([(self.a.id, 'COLABORADOR')])
        db.session.expire_all()
        self.assertIsNone(self.a.responsable_id)
        self.assertFalse(self.usuario.pilares_info()[0]['es_lider'])

    def test_cambio_titular_preserva_otras_membresias_historicas(self):
        self.a.responsable = self.usuario
        nuevo = self.user('nuevo_titular', pilar_id=self.b.id)
        db.session.commit()
        self.client.post(f'/admin/pilares/{self.a.id}/editar', data={
            'nombre': self.a.nombre, 'responsable_id': str(nuevo.id), 'color_identificador': '#2563eb'})
        db.session.expire_all()
        self.assertEqual(self.a.responsable_id, nuevo.id)
        self.assertEqual({p['id'] for p in nuevo.pilares_info()}, {self.a.id, self.b.id})
        self.assertTrue(self.usuario.pilares_info()[0]['es_lider'])
        self.client.post(f'/admin/pilares/{self.a.id}/editar', data={
            'nombre': self.a.nombre, 'responsable_id': '', 'color_identificador': '#2563eb'})
        db.session.expire_all()
        self.assertIsNone(self.a.responsable_id)
        self.assertFalse(next(p for p in nuevo.pilares_info() if p['id'] == self.a.id)['es_lider'])

    def test_datos_invalidos_no_cambian_usuario(self):
        self.editar([(9999, 'LIDER')])
        self.assertEqual(self.usuario.pilar_id, self.a.id)
        self.assertEqual(UsuarioPilar.query.count(), 0)
        self.editar([(self.b.id, 'LIDER'), (self.b.id, 'COLABORADOR')])
        self.assertEqual(self.usuario.pilar_id, self.a.id)
        self.assertEqual(UsuarioPilar.query.count(), 0)

    def test_fallo_relacion_revierte_alta_usuario_y_titular(self):
        event.listen(UsuarioPilar, 'before_insert', fallo_relacion)
        try:
            self.client.post('/admin/usuarios/crear', data={
                'nombre_completo': 'Falla', 'username': 'falla', 'password': 'fixture-password',
                'usuario_pilar_id[]': [str(self.b.id)], 'usuario_rol_pilar[]': ['LIDER']})
        finally:
            event.remove(UsuarioPilar, 'before_insert', fallo_relacion)
        self.assertIsNone(Usuario.query.filter_by(username='falla').first())
        self.assertIsNone(self.b.responsable_id)

    def test_fallo_relacion_revierte_alta_pilar(self):
        event.listen(UsuarioPilar, 'before_insert', fallo_relacion)
        try:
            self.client.post('/admin/pilares/crear', data={
                'nombre': 'No debe quedar', 'responsable_id': str(self.usuario.id)})
        finally:
            event.remove(UsuarioPilar, 'before_insert', fallo_relacion)
        self.assertIsNone(Pilar.query.filter_by(nombre='No debe quedar').first())
        self.assertEqual(self.usuario.pilar_id, self.a.id)


class TareasTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.p = self.pilar('Sistemas')
        self.login(self.admin)

    def crear(self, **campos):
        datos = {'titulo': 'Tarea de prueba', 'responsable_id': str(self.admin.id),
                 'fecha_compromiso': '2030-01-01', 'pilar_id': ''}
        datos.update(campos)
        return self.client.post('/tareas/crear', data=datos)

    def test_tarea_general_multiples_apoyos_un_commit(self):
        otro = self.user('apoyo')
        self.crear(**{'apoyo_pilar_id[]': [str(self.p.id)] * 3,
                      'apoyo_responsable_id[]': ['', str(otro.id), str(otro.id)]})
        tarea = Tarea.query.one()
        self.assertIsNone(tarea.pilar_id)
        self.assertEqual(len(tarea.dependencias), 2)
        self.assertEqual(self.client.get(f'/tareas/{tarea.id}/detalle').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/tareas').status_code, 200)

    def test_datos_invalidos_no_crean_tarea(self):
        for campos in [dict(prioridad='INVALIDA'), dict(pilar_id='999'),
                       dict(responsable_id='999'), dict(fecha_compromiso='ayer'),
                       {'apoyo_pilar_id[]': ['999']}, {'apoyo_responsable_id[]': ['1']}]:
            self.crear(**campos)
            self.assertEqual(Tarea.query.count(), 0)

    def test_fallo_apoyo_revierte_tarea(self):
        event.listen(TareaDependencia, 'before_insert', fallo_relacion)
        try:
            self.crear(**{'apoyo_pilar_id[]': [str(self.p.id)]})
        finally:
            event.remove(TareaDependencia, 'before_insert', fallo_relacion)
        self.assertEqual(Tarea.query.count(), 0)
        self.assertEqual(TareaDependencia.query.count(), 0)

    def test_fallback_apoyo_historico_solo_lectura(self):
        tarea = self.tarea('Con apoyo antiguo', pilar_dependencia_id=self.p.id)
        datos = self.client.get(f'/tareas/{tarea.id}/detalle').json
        self.assertEqual(datos['dependencias'][0]['pilar_id'], self.p.id)
        self.assertIsNone(datos['dependencias'][0]['responsable_id'])
        self.assertEqual(TareaDependencia.query.count(), 0)
        self.assertIn('Sistemas', self.client.get('/dashboard').get_data(as_text=True))

    def test_nota_invalida_no_se_guarda(self):
        tarea = self.tarea('Bitácora')
        respuesta = self.client.post(f'/tareas/{tarea.id}/agregar-nota', json={'comentario': 'x', 'tipo': 'OTRO'})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(BitacoraTarea.query.count(), 0)
        respuesta = self.client.post(f'/tareas/{tarea.id}/agregar-nota', json={'comentario': 'x', 'tipo': 'NOTA_REUNION'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(BitacoraTarea.query.count(), 1)

    def test_fallo_bitacora_revierte_estatus(self):
        tarea = self.tarea('Cambiar estado')
        event.listen(BitacoraTarea, 'before_insert', fallo_relacion)
        try:
            respuesta = self.client.post(f'/tareas/{tarea.id}/actualizar-estatus', json={'estatus': 'COMPLETADO'})
        finally:
            event.remove(BitacoraTarea, 'before_insert', fallo_relacion)
        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(tarea.estatus, 'PENDIENTE')
        self.assertIsNone(tarea.fecha_cierre)

    def test_lote_api_atomico_si_segunda_tarea_falla(self):
        valida = dict(titulo='Correcta', pilar='Sistemas', fecha_compromiso='2030-01-01')
        mala = dict(titulo='Incorrecta', pilar='Sistemas', fecha_compromiso='fecha inválida')
        respuesta = self.client.post('/api/v1/tareas/ingesta-ia',
            headers={'X-API-Key': 'only-for-isolated-tests'}, json={'tareas': [valida, mala]})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Tarea.query.count(), 0)
        respuesta = self.client.post('/api/v1/tareas/ingesta-ia',
            headers={'X-API-Key': 'only-for-isolated-tests'}, json={'tareas': [valida, valida]})
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Tarea.query.count(), 2)
        self.assertEqual(len({t.codigo_folio for t in Tarea.query.all()}), 2)
