"""Migración conservadora del esquema productivo, sin importar ni convertir datos.

Sin --apply solo consulta MySQL y escribe un informe local. Para aplicar requiere
confirmación de base y mantenimiento, crea primero un respaldo y verifica cada DDL.
MySQL confirma los DDL implícitamente: no existe rollback global de estos pasos.
Un respaldo con hash NO sustituye un ensayo de restauración en una base separada.
No importa app/config.py, no ejecuta create_all() y no despliega código.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import dotenv_values
import pymysql


MIGRATION_ID = "20260914_estructura_multipilares_v1"
COLLATION = "utf8mb4_0900_ai_ci"
DEFAULT_DUMP = r"C:\Program Files\MySQL\MySQL Server 9.5\bin\mysqldump.exe"
DEFAULT_OUTPUT = r"C:\sites\migraciones_pendientes\revision_migracion\publicaciones"
ORIGINAL_TABLES = ("usuarios", "pilares", "tareas", "bitacora_tareas")
NEW_TABLES = ("usuarios_pilares", "tareas_dependencias")
ID_COLUMN = ("int", "NO", None, "auto_increment")
INT_REQUIRED = ("int", "NO", None, "")
INT_OPTIONAL = ("int", "YES", None, "")
TIMESTAMP = ("timestamp", "YES", "CURRENT_TIMESTAMP", "DEFAULT_GENERATED")

# Contrato explícito del esquema productivo inspeccionado el 14/09/2026.
# Se rechazan diferencias no contempladas en lugar de alterarlas automáticamente.
COLUMNS = {
    "usuarios": {
        "id": ID_COLUMN, "nombre_completo": ("varchar(100)", "NO", None, ""),
        "username": ("varchar(50)", "NO", None, ""),
        "email": ("varchar(100)", "YES", None, ""),
        "password_hash": ("varchar(255)", "NO", None, ""),
        "rol": ("varchar(20)", "YES", "COLABORADOR", ""),
        "es_responsable": ("tinyint(1)", "YES", "0", ""),
        "pilar_id": INT_OPTIONAL, "activo": ("tinyint(1)", "YES", "1", ""),
    },
    "pilares": {
        "id": ID_COLUMN, "nombre": ("varchar(50)", "NO", None, ""),
        "descripcion": ("varchar(150)", "YES", None, ""),
        "color_identificador": ("varchar(7)", "YES", "#2563eb", ""),
        "responsable_id": INT_OPTIONAL,
    },
    "tareas": {
        "id": ID_COLUMN, "codigo_folio": ("varchar(20)", "YES", None, ""),
        "titulo": ("varchar(200)", "NO", None, ""), "descripcion": ("text", "YES", None, ""),
        "pilar_id": INT_REQUIRED, "responsable_id": INT_REQUIRED, "creado_por_id": INT_REQUIRED,
        "prioridad": ("enum('P0_CRITICA','P1_ALTA','P2_MEDIA','P3_BAJA')", "YES", "P2_MEDIA", ""),
        "estatus": ("enum('PENDIENTE','EN_PROCESO','BLOQUEADO','COMPLETADO','CANCELADO')", "YES", "PENDIENTE", ""),
        "fecha_inicio": ("date", "NO", None, ""), "fecha_compromiso": ("date", "NO", None, ""),
        "fecha_cierre": ("date", "YES", None, ""), "fuente": ("varchar(30)", "YES", "DIRECCION", ""),
        "pilar_dependencia_id": INT_OPTIONAL, "created_at": TIMESTAMP,
        "updated_at": ("timestamp", "YES", "CURRENT_TIMESTAMP", "DEFAULT_GENERATED on update CURRENT_TIMESTAMP"),
    },
    "bitacora_tareas": {
        "id": ID_COLUMN, "tarea_id": INT_REQUIRED, "usuario_id": INT_REQUIRED,
        "comentario": ("text", "NO", None, ""),
        "tipo": ("enum('AVANCE','BLOQUEO','CAMBIO_ESTATUS','NOTA_REUNION')", "YES", "AVANCE", ""),
        "fecha_registro": TIMESTAMP,
    },
    "usuarios_pilares": {
        "id": ID_COLUMN, "usuario_id": INT_REQUIRED, "pilar_id": INT_REQUIRED,
        "es_lider": ("tinyint(1)", "YES", "0", ""), "created_at": TIMESTAMP,
    },
    "tareas_dependencias": {
        "id": ID_COLUMN, "tarea_id": INT_REQUIRED, "pilar_id": INT_REQUIRED, "responsable_id": INT_OPTIONAL,
    },
}
# (columna local, tabla referenciada, regla DELETE); UPDATE permanece NO ACTION.
FOREIGN_KEYS = {
    "usuarios": [("pilar_id", "pilares", "SET NULL")],
    "pilares": [("responsable_id", "usuarios", "SET NULL")],
    "tareas": [("pilar_id", "pilares", "NO ACTION"), ("responsable_id", "usuarios", "NO ACTION"),
               ("creado_por_id", "usuarios", "NO ACTION"), ("pilar_dependencia_id", "pilares", "NO ACTION")],
    "bitacora_tareas": [("tarea_id", "tareas", "CASCADE"), ("usuario_id", "usuarios", "NO ACTION")],
    "usuarios_pilares": [("usuario_id", "usuarios", "CASCADE"), ("pilar_id", "pilares", "CASCADE")],
    "tareas_dependencias": [("tarea_id", "tareas", "CASCADE"), ("pilar_id", "pilares", "CASCADE"),
                           ("responsable_id", "usuarios", "SET NULL")],
}
UNIQUE_KEYS = {
    "usuarios": {("id",), ("username",), ("email",)}, "pilares": {("id",), ("nombre",)},
    "tareas": {("id",), ("codigo_folio",)}, "bitacora_tareas": {("id",)},
    "usuarios_pilares": {("id",), ("usuario_id", "pilar_id")}, "tareas_dependencias": {("id",)},
}
DDLS = {
    "crear_usuarios_pilares": """CREATE TABLE `usuarios_pilares` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `usuario_id` INT NOT NULL,
  `pilar_id` INT NOT NULL,
  `es_lider` TINYINT(1) NULL DEFAULT 0,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuario_pilar` (`usuario_id`, `pilar_id`),
  KEY `ix_usuarios_pilares_pilar_id` (`pilar_id`),
  CONSTRAINT `fk_usuarios_pilares_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_usuarios_pilares_pilar` FOREIGN KEY (`pilar_id`) REFERENCES `pilares` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",
    "crear_tareas_dependencias": """CREATE TABLE `tareas_dependencias` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `tarea_id` INT NOT NULL,
  `pilar_id` INT NOT NULL,
  `responsable_id` INT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_tareas_dependencias_tarea_id` (`tarea_id`),
  KEY `ix_tareas_dependencias_pilar_id` (`pilar_id`),
  KEY `ix_tareas_dependencias_responsable_id` (`responsable_id`),
  CONSTRAINT `fk_tareas_dependencias_tarea` FOREIGN KEY (`tarea_id`) REFERENCES `tareas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tareas_dependencias_pilar` FOREIGN KEY (`pilar_id`) REFERENCES `pilares` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tareas_dependencias_responsable` FOREIGN KEY (`responsable_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",
    "permitir_tarea_sin_pilar": "ALTER TABLE `tareas` MODIFY COLUMN `pilar_id` INT NULL DEFAULT NULL",
}


class MigrationError(Exception):
    """Fallo esperado; el mensaje nunca incluye valores de credenciales ni filas."""


def require(condition, message):
    if not condition:
        raise MigrationError(message)


def identifier(value):
    require(bool(re.fullmatch(r"[A-Za-z0-9_]{1,64}", value)), "Identificador de base o tabla no admitido.")
    return "`" + value + "`"


def load_config(env_file, database):
    path = Path(env_file)
    require(path.is_absolute() and path.is_file(), "--env-file debe ser un archivo absoluto existente.")
    # interpolate=False impide tomar ${VARIABLES} del entorno del proceso.
    values = dotenv_values(path, interpolate=False, encoding="utf-8-sig")
    keys = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
    for key in keys:
        require(isinstance(values.get(key), str) and bool(values[key]), "Falta un valor explícito para " + key)
        require("\n" not in values[key] and "\r" not in values[key] and "\x00" not in values[key], "Valor de configuración no válido: " + key)
        require("${" not in values[key], "No se admite interpolación en " + key)
    identifier(database)
    require(values["DB_NAME"] == database, "DB_NAME del .env no coincide exactamente con --database.")
    try:
        port = int(values["DB_PORT"])
    except ValueError:
        raise MigrationError("DB_PORT debe ser un entero.") from None
    require(1 <= port <= 65535, "DB_PORT fuera de rango.")
    return {"host": values["DB_HOST"], "port": port, "user": values["DB_USER"],
            "password": values["DB_PASSWORD"], "database": database}


def query(conn, sql, args=()):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, args)
        return list(cur.fetchall())


def execute(conn, sql, args=()):
    with conn.cursor() as cur:
        cur.execute(sql, args)


def inspect_schema(conn, database):
    schema = {"server": query(conn, "SELECT DATABASE() db, VERSION() version, @@server_uuid server_uuid")[0]}
    schema["defaults"] = query(conn, "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s", (database,))[0]
    schema["tables"] = query(conn, "SELECT TABLE_NAME, TABLE_TYPE, ENGINE, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME", (database,))
    schema["columns"] = query(conn, "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, COLLATION_NAME, COLUMN_COMMENT, GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, ORDINAL_POSITION", (database,))
    schema["indexes"] = query(conn, "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART, IS_VISIBLE, EXPRESSION FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX", (database,))
    schema["fks"] = query(conn, """SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_SCHEMA,
        k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.DELETE_RULE, r.UPDATE_RULE
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r ON r.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA
          AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME AND r.TABLE_NAME=k.TABLE_NAME
        WHERE k.TABLE_SCHEMA=%s AND k.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY k.TABLE_NAME,k.CONSTRAINT_NAME,k.ORDINAL_POSITION""", (database,))
    schema["extras"] = {}
    for kind, catalog, column in (("triggers", "TRIGGERS", "TRIGGER_SCHEMA"), ("routines", "ROUTINES", "ROUTINE_SCHEMA"), ("events", "EVENTS", "EVENT_SCHEMA")):
        schema["extras"][kind] = query(conn, f"SELECT COUNT(*) n FROM information_schema.{catalog} WHERE {column}=%s", (database,))[0]["n"]
    schema["checks"] = query(conn, "SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=%s AND CONSTRAINT_TYPE='CHECK'", (database,))
    return schema


def normalize_column(value):
    col_type, nullable, default, extra = value
    if isinstance(default, str) and default.lower().replace("()", "") == "current_timestamp":
        default = "CURRENT_TIMESTAMP"
    return col_type, nullable, default, extra.lower().replace("()", "")


def build_plan(schema, database):
    require(schema["server"]["db"] == database, "La conexión seleccionó una base diferente.")
    require(bool(re.match(r"^9\.5\.", schema["server"]["version"])), "Solo se admite el servidor MySQL 9.5 ensayado; revise otras versiones por separado.")
    require(schema["defaults"] == {"DEFAULT_CHARACTER_SET_NAME": "utf8mb4", "DEFAULT_COLLATION_NAME": COLLATION}, "Charset o collation de la base inesperados.")
    tables = {t["TABLE_NAME"] for t in schema["tables"]}
    require(set(ORIGINAL_TABLES) <= tables <= set(COLUMNS), "Faltan tablas originales o existen tablas/vistas no contempladas.")
    require(not any(schema["extras"].values()) and not schema["checks"], "Hay triggers, rutinas, eventos o restricciones CHECK no contemplados.")
    for info in schema["tables"]:
        table = info["TABLE_NAME"]
        require(info["TABLE_TYPE"] == "BASE TABLE" and info["ENGINE"] == "InnoDB" and info["TABLE_COLLATION"] == COLLATION, "Motor/collation/tipo inesperado en " + table)
        rows = {c["COLUMN_NAME"]: c for c in schema["columns"] if c["TABLE_NAME"] == table}
        require(rows.keys() == COLUMNS[table].keys(), "Columnas no contempladas en " + table)
        for name, expected in COLUMNS[table].items():
            col = rows[name]
            actual = tuple(col[k] for k in ("COLUMN_TYPE", "IS_NULLABLE", "COLUMN_DEFAULT", "EXTRA"))
            allowed = [normalize_column(expected)]
            if (table, name) == ("tareas", "pilar_id"):
                allowed.append(normalize_column(INT_OPTIONAL))
            require(normalize_column(actual) in allowed, "Definición inesperada en " + table + "." + name)
            require(not col.get("GENERATION_EXPRESSION") and not col.get("COLUMN_COMMENT"), "Columna generada o comentada requiere revisión: " + table + "." + name)
            require(col["COLLATION_NAME"] in (None, COLLATION), "Collation de columna inesperada: " + table + "." + name)
        indexes = {}
        for index in (i for i in schema["indexes"] if i["TABLE_NAME"] == table):
            require(not index.get("SUB_PART") and not index.get("EXPRESSION") and index.get("IS_VISIBLE", "YES") == "YES", "Índice parcial/funcional/invisible requiere revisión en " + table)
            indexes.setdefault(index["INDEX_NAME"], {"unique": not index["NON_UNIQUE"], "columns": []})["columns"].append(index["COLUMN_NAME"])
        require(indexes.get("PRIMARY") == {"unique": True, "columns": ["id"]}, "Llave primaria inesperada en " + table)
        uniques = {tuple(i["columns"]) for i in indexes.values() if i["unique"]}
        require(uniques == UNIQUE_KEYS[table], "Índices únicos inesperados o faltantes en " + table)
        actual_fks = [f for f in schema["fks"] if f["TABLE_NAME"] == table]
        shapes = []
        for fk in actual_fks:
            require(fk["REFERENCED_TABLE_SCHEMA"] == database and fk["REFERENCED_COLUMN_NAME"] == "id" and fk["UPDATE_RULE"] in ("NO ACTION", "RESTRICT"), "Referencia externa o FK inesperada en " + table)
            delete = "NO ACTION" if fk["DELETE_RULE"] == "RESTRICT" else fk["DELETE_RULE"]
            shapes.append((fk["COLUMN_NAME"], fk["REFERENCED_TABLE_NAME"], delete))
        require(sorted(shapes) == sorted(FOREIGN_KEYS[table]), "Llaves foráneas inesperadas o faltantes en " + table)
        for column, _, _ in FOREIGN_KEYS[table]:
            require(any(i["columns"][0] == column for i in indexes.values()), "Falta índice de FK en " + table + "." + column)
    pending = ["crear_" + t for t in NEW_TABLES if t not in tables]
    if any(c['TABLE_NAME'] == 'tareas' and c['COLUMN_NAME'] == 'pilar_id' and c['IS_NULLABLE'] == 'NO' for c in schema['columns']):
        pending.append("permitir_tarea_sin_pilar")
    return [{"id": key, "sql": DDLS[key]} for key in pending]


def check_integrity(conn, schema):
    """Detecta referencias huérfanas preexistentes, sin corregir filas."""
    for fk in schema["fks"]:
        table, column, target = (identifier(fk[key]) for key in ("TABLE_NAME", "COLUMN_NAME", "REFERENCED_TABLE_NAME"))
        count = query(conn, f"SELECT COUNT(*) n FROM {table} a LEFT JOIN {target} b ON a.{column}=b.id WHERE a.{column} IS NOT NULL AND b.id IS NULL")[0]["n"]
        require(count == 0, "Referencias huérfanas detectadas en " + fk["TABLE_NAME"] + "." + fk["COLUMN_NAME"])


def fingerprint(conn, tables):
    """Hash ordenado por PK; no guarda filas ni hashes de contraseñas en informes."""
    result = {}
    for table in sorted(tables):
        digest, count = hashlib.sha256(), 0
        with conn.cursor(pymysql.cursors.SSCursor) as cur:
            cur.execute("SELECT * FROM " + identifier(table) + " ORDER BY `id`")
            digest.update(json.dumps([d[0] for d in cur.description], ensure_ascii=False).encode("utf-8"))
            for row in cur:
                raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
                digest.update(len(raw).to_bytes(8, "big"))
                digest.update(raw)
                count += 1
        result[table] = {"rows": count, "sha256": digest.hexdigest()}
    return result


def private_directory(path):
    """Restringe ACL ANTES de escribir credenciales temporales o el respaldo."""
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    if os.name == "nt":
        system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        result = subprocess.run([str(system32 / "whoami.exe"), "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True, timeout=10)
        sid = next(csv.reader(result.stdout.strip().splitlines()))[1]
        require(bool(re.fullmatch(r"S-1-[0-9-]+", sid)), "No se pudo identificar el SID para proteger el respaldo.")
        subprocess.run([str(system32 / "icacls.exe"), str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"], capture_output=True, check=True, timeout=10)
    else:
        path.chmod(0o700)


def option_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def make_backup(config, run_dir, executable, tables, timeout):
    exe = Path(executable)
    require(exe.is_absolute() and exe.is_file(), "mysqldump debe ser un ejecutable absoluto existente.")
    # El cliente no hereda MYSQL_PWD, MYSQL_HOST, archivos defaults ni login paths.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("MYSQL")}
    version = subprocess.run([str(exe), "--no-defaults", "--no-login-paths", "--version"], capture_output=True, env=env, timeout=10)
    require(version.returncode == 0 and re.search(rb"\b9\.5\.\d+", version.stdout), "Se requiere mysqldump 9.5 compatible con este servidor.")
    backup = run_dir / "respaldo_antes.sql"
    # Directorio padre ya tiene ACL privada; el archivo se elimina aun si falla el dump.
    fd, name = tempfile.mkstemp(prefix=".mysql-client-", suffix=".cnf", dir=run_dir)
    credentials = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("[client]\n")
            for key in ("host", "port", "user", "password"):
                handle.write(key + "=" + option_quote(config[key]) + "\n")
            handle.write("protocol=TCP\ndefault-character-set=utf8mb4\n")
        command = [str(exe), "--defaults-file=" + str(credentials), "--no-login-paths", "--single-transaction",
                   "--quick", "--hex-blob", "--triggers", "--no-tablespaces", "--set-gtid-purged=OFF",
                   "--column-statistics=0", "--routines", "--events", "--default-character-set=utf8mb4",
                   "--result-file=" + str(backup), config["database"]]
        result = subprocess.run(command, capture_output=True, env=env, timeout=timeout)
        # stderr puede contener datos de conexión: no se imprime ni se guarda.
        require(result.returncode == 0, "mysqldump terminó con error; no se aplicó DDL. Código: " + str(result.returncode))
    finally:
        credentials.unlink(missing_ok=True)
    size = backup.stat().st_size
    require(size > 1024, "El respaldo tiene un tamaño inesperado; no se aplicó DDL.")
    digest, found, complete = hashlib.sha256(), set(), False
    with backup.open("rb") as handle:
        for line in handle:
            digest.update(line)
            if line.startswith(b"CREATE TABLE `"):
                found.add(line.split(b"`", 2)[1].decode("ascii"))
            if line.startswith(b"-- Dump completed on "):
                complete = True
    require(set(tables) == found and complete, "El respaldo no contiene todas las tablas o su marcador de finalización.")
    return {"path": str(backup), "bytes": size, "sha256": digest.hexdigest(), "returncode": 0,
            "tables_verified": sorted(found), "restore_tested": False,
            "note": "Salida completa y hash verificados; ensayar restauración por separado."}


def write_report(path, report):
    staging = path.with_suffix(".tmp")
    with staging.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    staging.replace(path)


def verify_preservation(before, after):
    for table, previous in before.items():
        require(after.get(table) == previous, "Cambió el conteo o la huella de " + table + "; mantener el servicio detenido y revisar el informe.")
    for table in after.keys() - before.keys():
        require(after[table]["rows"] == 0, "La tabla recién creada contiene filas; revisar escrituras concurrentes.")


def validate_output_dir(value):
    output = Path(value)
    require(output.is_absolute(), "--output-dir debe ser absoluto.")
    output = output.resolve()
    require(not {"static", "public", "wwwroot", "htdocs", ".git"}.intersection(p.lower() for p in output.parts),
            "No guarde respaldos en directorios publicados ni .git.")
    return output


def parser():
    result = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    result.add_argument("--env-file", required=True, help="Ruta absoluta del .env del destino (también para clones).")
    result.add_argument("--database", required=True, help="Debe coincidir exactamente con DB_NAME del archivo.")
    result.add_argument("--output-dir", default=DEFAULT_OUTPUT,
                        help="Ruta absoluta privada de informes y respaldos. Por defecto: " + DEFAULT_OUTPUT)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Aplicar después de respaldar; confirma cada DDL implícitamente.")
    mode.add_argument("--dry-run", action="store_true", help="Solo plan (también es el modo predeterminado).")
    result.add_argument("--confirm-database", help="Nombre exacto del destino; obligatorio con --apply.")
    result.add_argument("--maintenance-confirmed", action="store_true", help="Confirma que se detuvieron app, workers y cualquier escritor del destino.")
    result.add_argument("--mysqldump", default=DEFAULT_DUMP, help="Ruta absoluta de mysqldump 9.5.")
    result.add_argument("--lock-timeout", type=int, default=10, help="Espera máxima por bloqueos DDL, en segundos (1-60).")
    result.add_argument("--backup-timeout", type=int, default=300, help="Límite del proceso de respaldo, en segundos (30-3600).")
    return result


def run(args, *, plan_builder=None, migration_id=None, integrity_checker=None, initialize=None, preflight=None, file_backup=None):
    # Las migraciones versionadas reutilizan estas protecciones. La entrada
    # histórica conserva exactamente su plan y contrato por defecto.
    plan_builder = plan_builder or build_plan
    integrity_checker = integrity_checker or check_integrity
    migration_id = migration_id or MIGRATION_ID
    config = load_config(args.env_file, args.database)
    require(1 <= args.lock_timeout <= 60 and 30 <= args.backup_timeout <= 3600, "Límites de tiempo fuera de rango.")
    if args.apply:
        require(args.confirm_database == args.database, "--apply requiere --confirm-database con el nombre exacto.")
        require(args.maintenance_confirmed, "--apply requiere --maintenance-confirmed después de detener todos los escritores.")
    else:
        require(not args.maintenance_confirmed and args.confirm_database is None, "Las confirmaciones solo se usan junto con --apply.")
    output = validate_output_dir(args.output_dir)
    run_dir = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    private_directory(run_dir)
    report_path = run_dir / "informe.json"
    report = {"migration": migration_id, "started_utc": datetime.now(timezone.utc).isoformat(),
              "mode": "apply" if args.apply else "dry-run", "database": args.database,
              "host": config["host"], "port": config["port"], "status": "starting", "steps": [],
              "warning": "DDL con commit implícito; no hay rollback global. No importa ni convierte datos."}
    conn, locked = None, False
    lock_name = "toplabel_schema_" + hashlib.sha256(args.database.encode()).hexdigest()[:32]
    write_report(report_path, report)
    try:
        conn = pymysql.connect(**config, charset="utf8mb4", autocommit=True,
                               connect_timeout=10, read_timeout=60, write_timeout=60)
        execute(conn, "SET SESSION time_zone='+00:00'")
        if args.apply:
            execute(conn, "SET SESSION lock_wait_timeout=%s", (args.lock_timeout,))
            execute(conn, "SET SESSION innodb_lock_wait_timeout=%s", (args.lock_timeout,))
            locked = query(conn, "SELECT GET_LOCK(%s, 0) locked", (lock_name,))[0]["locked"] == 1
            require(locked, "Otra ejecución mantiene el bloqueo de esta migración.")
        else:
            execute(conn, "SET SESSION TRANSACTION READ ONLY")
        initial = inspect_schema(conn, args.database)
        plan = plan_builder(initial, args.database)
        integrity_checker(conn, initial)
        if preflight:
            report['preflight'] = preflight(conn, initial)
        tables = [t["TABLE_NAME"] for t in initial["tables"]]
        before = fingerprint(conn, tables)
        report.update({"server": initial["server"], "schema_before": initial, "data_before": before, "plan": plan,
                       "status": "planned", "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()})
        write_report(report_path, report)
        print("Destino: " + args.database + "; modo: " + report["mode"])
        print("Conteos actuales: " + json.dumps({t: v["rows"] for t, v in before.items()}))
        for step in plan:
            print("Pendiente: " + step["id"])
        if args.apply and (plan or initialize):
            print("Creando respaldo completo antes del primer DDL...")
            report["backup"] = make_backup(config, run_dir, args.mysqldump, tables, args.backup_timeout)
            if file_backup:
                report['backup_adjuntos'] = file_backup(run_dir)
            write_report(report_path, report)
            verify_preservation(before, fingerprint(conn, tables))
            require(inspect_schema(conn, args.database) == initial, "El esquema cambió durante el respaldo; no se aplicó DDL.")
            for step in plan:
                pending = plan_builder(inspect_schema(conn, args.database), args.database)
                require(step in pending, "El estado cambió fuera de esta ejecución; revisar antes de reintentar.")
                progress = {"id": step["id"], "status": "started", "started_utc": datetime.now(timezone.utc).isoformat()}
                report["steps"].append(progress)
                write_report(report_path, report)
                execute(conn, step["sql"])
                require(not any(s["id"] == step["id"] for s in plan_builder(inspect_schema(conn, args.database), args.database)), "No se pudo verificar el DDL " + step["id"])
                progress.update(status="verified", finished_utc=datetime.now(timezone.utc).isoformat())
                write_report(report_path, report)
                print("Verificado: " + step["id"])
        if args.apply:
            final_schema = inspect_schema(conn, args.database)
            require(not plan_builder(final_schema, args.database), "Quedan pasos pendientes después de aplicar.")
            integrity_checker(conn, final_schema)
            after = fingerprint(conn, [t["TABLE_NAME"] for t in final_schema["tables"]])
            report.update(schema_after=final_schema, data_after=after)
            verify_preservation(before, after)
            if initialize:
                report['initialization'] = initialize(conn)
                integrity_checker(conn, final_schema)
                final_data = fingerprint(conn, [t['TABLE_NAME'] for t in final_schema['tables']])
                for table in ORIGINAL_TABLES + NEW_TABLES:
                    require(final_data[table] == after[table], 'La inicialización alteró datos originales: ' + table)
                report['data_initialized'] = final_data
            report["status"] = "verified" if plan else "already_applied"
        else:
            report["status"] = "dry_run_ok"
        print("Resultado: " + report["status"])
        return 0
    except Exception as exc:
        # No imprimir str(exc) de conectores, subprocess o IO: puede contener secretos.
        report["status"] = "failed"
        report["error"] = str(exc) if isinstance(exc, MigrationError) else "Fallo de " + type(exc).__name__ + "; revisar conexión, permisos y pasos registrados."
        if isinstance(exc, pymysql.MySQLError) and exc.args and isinstance(exc.args[0], int):
            report["mysql_error_code"] = exc.args[0]
        print("ERROR: " + report["error"], file=sys.stderr)
        if report["steps"]:
            print("Puede haber DDL ya confirmado. Mantenga mantenimiento y revise el informe antes de reintentar.", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            try:
                if locked:
                    query(conn, "SELECT RELEASE_LOCK(%s)", (lock_name,))
            except Exception:
                pass
            conn.close()
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_report(report_path, report)
        print("Informe: " + str(report_path))


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return run(args)
    except MigrationError as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print("ERROR: no se pudo preparar la ejecución (" + type(exc).__name__ + ").", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
