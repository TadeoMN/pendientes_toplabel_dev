import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import migracion_estructura as m


class MigrationTests(unittest.TestCase):
    def setUp(self):
        fixtures = Path(__file__).parent / 'fixtures'
        self.before = json.loads((fixtures / 'esquema_prod.json').read_text(encoding='utf-8'))
        self.after = json.loads((fixtures / 'esquema_migrado.json').read_text(encoding='utf-8'))

    def test_plan_solo_tres_ddl(self):
        plan = m.build_plan(self.before, 'test')
        self.assertEqual([p['id'] for p in plan], [
            'crear_usuarios_pilares', 'crear_tareas_dependencias', 'permitir_tarea_sin_pilar'])
        for paso in plan:
            self.assertTrue(paso['sql'].startswith(('CREATE TABLE', 'ALTER TABLE')))
            self.assertNotIn('INSERT ', paso['sql'])
            self.assertNotIn('UPDATE ', paso['sql'])

    def test_esquema_migrado_no_tiene_pasos(self):
        self.assertEqual(m.build_plan(self.after, 'test'), [])

    def test_recuperar_ddl_parcial(self):
        parcial = copy.deepcopy(self.after)
        for key in ('tables', 'columns', 'indexes', 'fks'):
            parcial[key] = [v for v in parcial[key] if v['TABLE_NAME'] != 'tareas_dependencias']
        self.assertEqual([p['id'] for p in m.build_plan(parcial, 'test')], ['crear_tareas_dependencias'])

    def test_rechaza_tabla_existente_sin_indice_unico(self):
        self.after['indexes'] = [i for i in self.after['indexes'] if i['INDEX_NAME'] != 'uq_usuario_pilar']
        with self.assertRaises(m.MigrationError):
            m.build_plan(self.after, 'test')

    def test_rechaza_fk_o_collation_diferente(self):
        self.after['fks'][0]['DELETE_RULE'] = 'SET NULL'
        with self.assertRaises(m.MigrationError):
            m.build_plan(self.after, 'test')
        self.before['defaults']['DEFAULT_COLLATION_NAME'] = 'utf8mb4_unicode_ci'
        with self.assertRaises(m.MigrationError):
            m.build_plan(self.before, 'test')

    def test_rechaza_destino_distinto(self):
        with self.assertRaises(m.MigrationError):
            m.build_plan(self.before, 'otra')

    def test_huella_cambiada_detiene_ejecucion(self):
        before = {'usuarios': {'rows': 19, 'sha256': 'original'}}
        with self.assertRaises(m.MigrationError):
            m.verify_preservation(before, {'usuarios': {'rows': 19, 'sha256': 'alterado'}})
        with self.assertRaises(m.MigrationError):
            m.verify_preservation(before, {**before, 'usuarios_pilares': {'rows': 1}})

    def test_config_explicita_ignora_entorno(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.env'
            path.write_text('DB_HOST=127.0.0.1\nDB_PORT=33316\nDB_USER=fixture\n'
                            'DB_PASSWORD=fixture\nDB_NAME=test\n', encoding='utf-8')
            with patch.dict('os.environ', {'DB_NAME': 'produccion', 'DB_HOST': 'otro'}):
                cfg = m.load_config(str(path), 'test')
            self.assertEqual(cfg['host'], '127.0.0.1')
            with self.assertRaises(m.MigrationError):
                m.load_config(str(path), 'produccion')

    def test_apply_sin_confirmacion_no_conecta(self):
        with patch.object(m, 'load_config', return_value={}), patch.object(m.pymysql, 'connect') as connect:
            args = m.parser().parse_args(['--env-file', 'fixture', '--database', 'test',
                                        '--output-dir', 'fixture', '--apply'])
            with self.assertRaises(m.MigrationError):
                m.run(args)
            connect.assert_not_called()
