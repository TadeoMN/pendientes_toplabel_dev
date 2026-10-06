"""Migraciones aprobadas de estructura para producción (MySQL 9.5).

Diagnostica por defecto. Reutiliza respaldo, bloqueo, comprobación de integridad
y huellas de datos del migrador original. No lee ni importa la BD de desarrollo.

--hasta multipilares: solo los tres pasos de la primera migración.
--hasta reportes: añade PROBLEMA y ACUERDO al ENUM de la bitácora (predeterminado).
No copia código, no detiene servicios y no revierte versiones ya aplicadas.
"""
from __future__ import annotations

import copy
from functools import partial
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __package__:
    from . import migracion_estructura as base
else:
    import migracion_estructura as base


VERSIONES = {
    "multipilares": base.MIGRATION_ID,
    "reportes": "20260918_tipos_reporte_v2",
    "roles_archivos": "20260929_roles_archivos_v3",
    "notas_estatus": "20260930_notas_estatus_v4",
}
TIPOS_ANTERIORES = ("AVANCE", "BLOQUEO", "CAMBIO_ESTATUS", "NOTA_REUNION")
TIPOS_REPORTES = (*TIPOS_ANTERIORES, "PROBLEMA", "ACUERDO")
TIPOS_NOTAS = (*TIPOS_REPORTES, "OBSERVACION")
ENUM_NOTAS = "enum(" + ",".join("'" + value + "'" for value in TIPOS_NOTAS) + ")"
ENUM_ANTERIOR = base.COLUMNS["bitacora_tareas"]["tipo"][0]
ENUM_REPORTES = "enum(" + ",".join("'" + value + "'" for value in TIPOS_REPORTES) + ")"
PASO_REPORTES = {
    "id": "ampliar_tipos_reporte",
    # Se agregan valores al final, sin renumerar los cuatro existentes. Se exige
    # INPLACE: si el servidor no lo admite, falla en vez de recurrir a COPY.
    "sql": "ALTER TABLE `bitacora_tareas` MODIFY COLUMN `tipo` "
           + ENUM_REPORTES + " NULL DEFAULT 'AVANCE', ALGORITHM=INPLACE, LOCK=NONE",
    "migration": VERSIONES["reportes"],
}


def build_plan(schema, database, *, hasta="reportes", desarrollo=False):
    if desarrollo:
        from scripts.migracion_acceso import plan_desarrollo, TABLAS
        base.require(hasta in ('roles_archivos', 'notas_estatus'), 'Versión de desarrollo no admitida.')
        return plan_desarrollo(schema, database, base, (*TABLAS, 'transiciones_notas') if hasta == 'notas_estatus' else TABLAS)
    base.require(hasta in VERSIONES, "Versión de migración no contemplada.")
    columns = [c for c in schema["columns"]
               if (c["TABLE_NAME"], c["COLUMN_NAME"]) == ("bitacora_tareas", "tipo")]
    base.require(len(columns) == 1, "Falta o está duplicada la definición bitacora_tareas.tipo.")
    current = columns[0]["COLUMN_TYPE"]
    base.require(current in (ENUM_ANTERIOR, ENUM_REPORTES, ENUM_NOTAS),
                 "bitacora_tareas.tipo no coincide con ninguna versión aprobada; no se convertirá automáticamente.")

    # Validar TODO el contrato original, sustituyendo solo el ENUM ya reconocido
    # en una copia. Nullability, default, collation, índices y FK siguen sujetos
    # a la validación original. Nunca se modifica schema ni el contrato de base.
    validation_schema = copy.deepcopy(schema)
    for column in validation_schema["columns"]:
        if (column["TABLE_NAME"], column["COLUMN_NAME"]) == ("bitacora_tareas", "tipo"):
            column["COLUMN_TYPE"] = ENUM_ANTERIOR
    from scripts.migracion_acceso import contrato, TABLAS
    tablas = (*TABLAS, 'transiciones_notas') if hasta == 'notas_estatus' or any(t['TABLE_NAME'] == 'transiciones_notas' for t in schema['tables']) else TABLAS
    if hasta in ('roles_archivos', 'notas_estatus') or any(t['TABLE_NAME'] in tablas for t in schema['tables']):
        with contrato(base, tablas):
            plan = [{**step, 'migration': VERSIONES['roles_archivos']} for step in base.build_plan(validation_schema, database)]
        if hasta not in ('roles_archivos', 'notas_estatus'):
            plan = [s for s in plan if s['id'] not in {'crear_' + t for t in tablas}]
    else:
        plan = [{**step, "migration": VERSIONES["multipilares"]}
                for step in base.build_plan(validation_schema, database)]
    if hasta in ("reportes", 'roles_archivos') and current == ENUM_ANTERIOR:
        plan.append(dict(PASO_REPORTES))
    if hasta != 'notas_estatus':
        plan = [s for s in plan if s['id'] != 'crear_transiciones_notas']
    else:
        for step in plan:
            if step['id'] == 'crear_transiciones_notas': step['migration'] = VERSIONES['notas_estatus']
        if current != ENUM_NOTAS:
            plan.append({'id':'ampliar_tipos_nota', 'migration':VERSIONES['notas_estatus'],
                         'sql':"ALTER TABLE `bitacora_tareas` MODIFY COLUMN `tipo` " + ENUM_NOTAS + " NULL DEFAULT 'AVANCE', ALGORITHM=INPLACE, LOCK=NONE"})
    return plan


def check_integrity(conn, schema):
    base.check_integrity(conn, schema)
    # Un ENUM puede contener el valor inválido '' si alguna aplicación escribió
    # con modo SQL permisivo. No corregirlo ni convertirlo silenciosamente.
    placeholders = ",".join(["%s"] * len(TIPOS_NOTAS))
    invalid = base.query(conn, "SELECT COUNT(*) n FROM `bitacora_tareas` "
                         "WHERE `tipo` IS NOT NULL AND `tipo` NOT IN (" + placeholders + ")",
                         TIPOS_NOTAS)[0]["n"]
    base.require(invalid == 0, "Hay tipos de bitácora inválidos; deben revisarse antes de migrar.")
    tables = {t['TABLE_NAME'] for t in schema['tables']}
    if 'adjuntos' in tables:
        invalid = base.query(conn, 'SELECT COUNT(*) n FROM adjuntos WHERE (tarea_id IS NULL) = (nota_id IS NULL) OR tamano <= 0')[0]['n']
        base.require(invalid == 0, 'Hay adjuntos sin un único registro padre o con tamaño inválido.')
    from scripts.migracion_acceso import TABLAS
    from app import db
    for nombre in (*TABLAS, 'transiciones_notas'):
        if nombre not in tables:
            continue
        for fk in db.metadata.tables[nombre].foreign_keys:
            sql = (f'SELECT COUNT(*) n FROM `{nombre}` a LEFT JOIN `{fk.column.table.name}` b '
                   f'ON a.`{fk.parent.name}`=b.id WHERE a.`{fk.parent.name}` IS NOT NULL AND b.id IS NULL')
            base.require(base.query(conn, sql)[0]['n'] == 0, f'Hay referencias huérfanas en {nombre}.{fk.parent.name}.')


def parser():
    result = base.parser()
    result.description = __doc__
    result.add_argument("--hasta", choices=tuple(VERSIONES), default="reportes",
                        help="Última versión aprobada que se desea alcanzar; nunca elimina una posterior.")
    result.add_argument('--admin-usuario', help='Cuenta activa DEL DESTINO que será administrador inicial; no reasigna si ya existe uno.')
    result.add_argument('--desarrollo', action='store_true', help='Solo agrega las tablas v3 al esquema de desarrollo, sin convertir sus tablas existentes.')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        initialize = None
        preflight = None
        file_backup = None
        if args.hasta in ('roles_archivos', 'notas_estatus'):
            from scripts.migracion_acceso import inicializar, preflight as comprobar, respaldar_adjuntos
            initialize = partial(inicializar, admin_username=args.admin_usuario)
            preflight = partial(comprobar, admin_username=args.admin_usuario, base=base,
                                env_file=args.env_file, database=args.database)
            file_backup = partial(respaldar_adjuntos, args.env_file, args.database)
        return base.run(args, plan_builder=partial(build_plan, hasta=args.hasta, desarrollo=args.desarrollo),
                        migration_id=VERSIONES[args.hasta], integrity_checker=check_integrity, initialize=initialize, preflight=preflight, file_backup=file_backup)
    except base.MigrationError as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print("ERROR: no se pudo preparar la ejecución (" + type(exc).__name__ + ").", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
