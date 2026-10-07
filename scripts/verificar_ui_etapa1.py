"""Renderiza fixtures de interfaz sin leer ni escribir la base de datos.

python scripts/verificar_ui_etapa1.py
python scripts/verificar_ui_etapa1.py --servir  (solo loopback, puerto 5012)
No sustituye las pruebas de integración con cuentas y datos reales de prueba.
"""
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask import Flask, flash, jsonify, render_template
from app import create_app

PAYLOAD = '<img src=x onerror=alert(1)> `${alert(2)}` </script>'
app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'SECRET_KEY': 'fixture-local'})


def usuario(identificador, activo, roles):
    datos = dict(id=identificador, nombre_completo=f'Usuario de prueba {identificador}',
                 username=f'prueba{identificador}', email=None, activo=activo,
                 nombres_roles=roles, es_direccion=False, tiene_rol_administrador=False,
                 es_administrador=True, is_authenticated=True)
    u = SimpleNamespace(**datos)
    u.puede = lambda *args: True
    u.pilares_info = lambda: []
    u.to_dict = lambda: {**datos, 'rol_sistema_id': 1, 'pilares': []}
    return u


usuarios = [usuario(1, True, 'Dirección, Líder'), usuario(2, False, 'Colaborador'),
            usuario(3, True, 'Administrador del sistema')]
roles = [SimpleNamespace(id=i, nombre=n, codigo=c) for i, n, c in [
    (1, 'Administrador del sistema', 'ADMINISTRADOR'), (2, 'Dirección', 'DIRECCION'),
    (3, 'Colaborador', 'COLABORADOR'), (4, 'Líder', 'LIDER_PILAR')]]
pilar = SimpleNamespace(id=1, nombre=PAYLOAD, descripcion='Pilar de prueba',
                        color_identificador='#0284c7', responsable_id=None,
                        responsable=None, tareas=[], miembros=[])
pilar.to_dict = lambda: {'id': 1, 'nombre': PAYLOAD, 'color': '#0284c7'}


def renderizar(nombre, mensaje=None):
    with app.test_request_context('/admin/usuarios'):
        if mensaje:
            flash(PAYLOAD, mensaje)
        return render_template(nombre, current_user=usuarios[0], usuarios=usuarios,
                               roles=roles, pilares=[pilar], grupos=[('mias', 'Mis tareas', [])],
                               usuarios_json=[], pilares_json=[], responsables_permitidos=[])


class Elementos(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elementos = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))


class Verificacion(unittest.TestCase):
    def test_permisos_agrupados_conservan_catalogo_y_seleccion(self):
        from app.permisos import CATALOGO, ALCANCES
        esperados = {codigo + '|' + scope for codigo, (_, scoped) in CATALOGO.items()
                     for scope in (ALCANCES if scoped else ['sistema'])}
        marcados = {'usuarios.ver|sistema', 'tareas.ver|asignadas', 'archivos.ver|propias'}
        with app.test_request_context('/roles/'):
            html = render_template('admin/roles.html', current_user=usuarios[0], roles=[],
                                   seleccionado=None, catalogo=CATALOGO, alcances=ALCANCES,
                                   marcados=marcados)
        casillas = [a for tag, a in Elementos(html).elementos
                    if tag == 'input' and a.get('name') == 'permisos']
        self.assertEqual(len(casillas), len(esperados))
        self.assertEqual({a['value'] for a in casillas}, esperados)
        self.assertEqual({a['value'] for a in casillas if 'checked' in a}, marcados)
        self.assertTrue(all('disabled' not in a for a in casillas))

    def test_estado_y_roles(self):
        elementos = Elementos(renderizar('admin/usuarios.html')).elementos
        estados = [a['data-val'] for tag, a in elementos if tag == 'td' and 'data-val' in a]
        self.assertEqual(estados, ['Activo', 'Inactivo', 'Activo'])
        opciones = {a.get('value') for tag, a in elementos if tag == 'option'}
        self.assertTrue({r.nombre for r in roles}.issubset(opciones))
        html = renderizar('admin/usuarios.html')
        self.assertIn(r'\u003cimg', html)
        self.assertNotIn('OPCIONES_PILARES_HTML', html)

    def test_autocompletar_y_carga_scripts(self):
        html = renderizar('login.html')
        campos = {a['id']: a for t, a in Elementos(html).elementos if t == 'input' and 'id' in a}
        self.assertEqual(campos['username']['autocomplete'], 'username')
        self.assertEqual(campos['password']['autocomplete'], 'current-password')
        self.assertLess(html.index('js/csrf.js'), html.index('js/formularios.js'))
        campos = [a for t, a in Elementos(renderizar('admin/usuarios.html')).elementos
                  if t == 'input' and a.get('type') == 'password']
        self.assertEqual(len(campos), 2)
        self.assertTrue(all(a.get('autocomplete') == 'new-password' for a in campos))

    def test_flash_seguro_y_persistente(self):
        for categoria in ('danger', 'success'):
            html = renderizar('login.html', categoria)
            script = html.split("Swal.fire({")[-1].split('});')[0]
            self.assertIn('titleText:', script)
            self.assertIn(r'\u003cimg', script)
            if categoria == 'danger':
                self.assertIn('showCloseButton: false', script)
                self.assertIn('showConfirmButton: true', script)
                self.assertIn("confirmButtonText: 'Cerrar'", script)
                self.assertNotIn('timer:', script)
            else:
                self.assertIn('timer: 5000', script)
                self.assertIn('timerProgressBar: true', script)

    def test_cierre_y_kpi(self):
        html = renderizar('dashboard_direccion.html')
        self.assertNotIn('btn-close-white', html)
        self.assertIn('fs-2 fw-bold text-warning-emphasis', html)

    def test_sintaxis_todas_las_plantillas(self):
        for nombre in app.jinja_env.list_templates():
            with self.subTest(plantilla=nombre):
                app.jinja_env.get_template(nombre)


if __name__ == '__main__':
    if '--servir' not in sys.argv:
        unittest.main()
    else:
        # Servidor independiente con datos sintéticos. No registra usuarios ni tareas.
        visor = Flask('verificacion-ui', static_folder=app.static_folder, static_url_path='/static')

        @visor.get('/verificacion/<pantalla>')
        def pantalla(pantalla):
            plantillas = {'usuarios': 'admin/usuarios.html', 'pilares': 'admin/pilares.html',
                          'direccion': 'dashboard_direccion.html', 'pendientes': 'mis_pendientes.html',
                          'error': 'login.html', 'exito': 'login.html'}
            return renderizar(plantillas[pantalla], {'error': 'danger', 'exito': 'success'}.get(pantalla))

        @visor.get('/admin/pilares/1/miembros')
        def miembros():
            return jsonify(pilar=PAYLOAD, color='#0284c7', miembros=[{
                'nombre_completo': PAYLOAD, 'username': PAYLOAD,
                'email': PAYLOAD, 'es_responsable': True}])

        visor.run(host='127.0.0.1', port=5012, debug=False)
