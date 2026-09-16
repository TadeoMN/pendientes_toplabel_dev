# Revisión de migración a producción

> Informe histórico anterior a las correcciones. La entrega actual usa migración **solo de estructura** y compatibilidad de lectura en la aplicación. Consultar [GUIA_PUBLICACION.md](C:/sites/pendientes_toplabel_dev/revision_migracion/GUIA_PUBLICACION.md) para el procedimiento vigente; el traslado de relaciones propuesto en este análisis ya no es necesario con el código corregido.

Fecha: 14 de septiembre de 2026.

## Dictamen

**No ejecutar `code-migracion.py` tal como está.** En la base productiva consultada trasladaría 7 de las 10 asignaciones existentes entre usuarios y pilares. Las otras 3 quedarían únicamente en la columna antigua y dejarían de aparecer en los listados nuevos. Además, el código de desarrollo tiene consultas y edición de líderes que todavía no son coherentes con las relaciones múltiples.

La migración es viable con cambios acotados, una prueba sobre una copia restaurada de producción y un corte coordinado de aplicación y BD. La ausencia actual de tareas reduce el volumen de datos a trasladar, pero no elimina los riesgos sobre usuarios, pilares y funcionamiento.

## Alcance y evidencia

Se revisaron ambas carpetas, modelos, rutas, plantillas, scripts de migración y el archivo adjunto. Se consultaron las bases indicadas en cada `.env`, usando conexiones independientes con `START TRANSACTION READ ONLY`, consultas `SELECT`/`SHOW` y cierre mediante `ROLLBACK`.

No se ejecutaron migraciones, escrituras en las bases, respaldos, restauraciones ni pruebas funcionales que creen datos. No se modificó código de la aplicación. Esta revisión genera únicamente este informe y un inventario local de esquemas y conteos, sin contraseñas ni registros personales.

La evidencia completa está en [evidencia_esquemas_2026-09-14.json](C:/sites/pendientes_toplabel_dev/revision_migracion/evidencia_esquemas_2026-09-14.json). Los conteos son `COUNT(*)`, no estimaciones de `information_schema.TABLES`. Son una fotografía del momento de consulta; deben repetirse antes del cambio. Se verificaron los destinos configurados en disco, no la configuración efectiva del proceso web en ejecución.

## 1. Estructura del proyecto

Es una aplicación Flask con Flask-SQLAlchemy, Flask-Login y PyMySQL. Cada carpeta contiene su propio `.env`, `venv`, punto de entrada `wsgi.py`, configuración Apache y paquete `app`.

| Elemento | Función |
|---|---|
| `app/__init__.py` | Crea Flask, registra extensiones, rutas y filtros de plantillas. |
| `app/config.py` | Lee configuración y construye la conexión a MySQL. |
| `app/models.py` | Define usuarios, pilares, tareas, bitácora y relaciones ORM. |
| `app/routes/` | Autenticación, administración, tableros, tareas y API. |
| `app/templates/`, `app/static/` | Interfaz HTML, JavaScript y CSS. |
| `init_db.py`, `setup_db_prod.py` | Inicialización y siembra; no constituyen actualizadores seguros de una BD existente. |
| `migrar_admin*.py`, `sincronizar.py` | Cambios manuales de esquema/datos, sin historial de versiones de migración. |

No se encontró un repositorio Git en la raíz de desarrollo ni una configuración de Alembic/Flask-Migrate. Las migraciones dependen del estado inicial y del orden en que se ejecutaron los scripts.

| Entorno | Carpeta | BD indicada en `.env` |
|---|---|---|
| Desarrollo | `C:\sites\pendientes_toplabel_dev` | `toplabel_pendientes` |
| Producción | `C:\sites\pendientes_toplabel` | `toplabel_pendientes_prod` |

Ambas conexiones configuradas apuntan a `127.0.0.1:3306`. El servidor consultado es MySQL Community **9.5.0**, con InnoDB y modo SQL estricto.

## 2. Estado real de las bases

| Tabla | Desarrollo: filas | Producción: filas |
|---|---:|---:|
| `usuarios` | 11 | 19 |
| `pilares` | 9 | 9 |
| `tareas` | 18 | 0 |
| `bitacora_tareas` | 30 | 0 |
| `usuarios_pilares` | 10 | No existe |
| `tareas_dependencias` | 12 | No existe |

### Cambios necesarios para las nuevas funciones

| Elemento | Estado actual de producción | Acción mínima |
|---|---|---|
| `usuarios.email` | `VARCHAR(100) NULL`, con índice único | Ya cumple; omitir ALTER redundante. |
| `usuarios.rol` | `VARCHAR(20) DEFAULT 'COLABORADOR'` | Ya cumple; conservar roles existentes. |
| `usuarios.es_responsable` | Existe | Usarlo como fuente histórica para el traslado. |
| `pilares.responsable_id` | Existe, FK `ON DELETE SET NULL` | Usarlo como segunda fuente de asignaciones/liderazgo. |
| `tareas.pilar_id` | `INT NOT NULL` | Permitir `NULL` para tareas generales. |
| `usuarios_pilares` | No existe | Crear con FK e índice único `(usuario_id, pilar_id)`; trasladar asignaciones. |
| `tareas_dependencias` | No existe | Crear con las tres FK; trasladar apoyos históricos si los hay al ejecutar. |

En producción hay **10 usuarios con pilar histórico** y **7 pilares con titular**. La unión de ambas fuentes contiene **10 pares usuario–pilar: 7 líderes y 3 colaboradores**. No aparecieron referencias huérfanas en las comprobaciones de usuarios/pilares y pilares/dependencias de tareas. Los valores de roles existentes tampoco requieren la normalización general de `migrar_admin_2.py`.

### Diferencias adicionales que conviene documentar

- Desarrollo usa `utf8mb4_unicode_ci`; producción usa `utf8mb4_0900_ai_ci`, tanto en el esquema como en las tablas observadas. Conservar el cotejamiento de producción en esta migración.
- Desarrollo usa `VARCHAR` para prioridad, estatus y tipo de bitácora; producción usa `ENUM`. Los valores ofrecidos por la interfaz y los cambios de estado de las rutas caben en los ENUM actuales. No hay evidencia de que convertirlos sea necesario para estas funciones. Las entradas libres de API/formulario requieren validación de valores permitidos.
- Producción usa `TIMESTAMP` con valores predeterminados donde desarrollo usa `DATETIME` y valores generados por el ORM. Conservar por ahora y verificar fechas/horas en el ensayo.
- Las FK de `tareas.pilar_id` y `tareas.pilar_dependencia_id` tienen `NO ACTION` **en ambas bases reales**, aunque el modelo de desarrollo declara `SET NULL`. Cambiar la nulabilidad no cambia esta política de borrado. No añadir cambios de borrado sin definir el comportamiento deseado.
- La FK de bitácora a tarea tiene `CASCADE` en producción y `NO ACTION` en desarrollo; la FK del pilar histórico del usuario tiene `SET NULL` en producción y `NO ACTION` en desarrollo. Igualar todo automáticamente modificaría comportamientos existentes.
- El modelo `UsuarioPilar` no declara el índice único ni `created_at` que sí existen en la tabla real de desarrollo. Deben quedar expresados en la definición versionada del esquema para que instalaciones futuras no diverjan.

## 3. Problemas del archivo consolidado

### A. Omite tres asignaciones productivas

El [bloque final del adjunto](C:/Users/ti/Downloads/code-migracion.py:64) solo copia `pilares.responsable_id`. Falta la copia de `usuarios.pilar_id` presente en [migrar_admin_4.py](C:/sites/pendientes_toplabel_dev/migrar_admin_4.py:33) y [sincronizar.py](C:/sites/pendientes_toplabel_dev/sincronizar.py:26).

Los datos antiguos no se borrarían físicamente, pero el [nuevo listado de miembros](C:/sites/pendientes_toplabel_dev/app/routes/admin.py:212) y la serialización de usuarios leen `usuarios_pilares`. Por eso es una pérdida de relación visible para la aplicación.

### B. No traslada apoyos históricos

Debe copiarse cada `tareas.pilar_dependencia_id` a `tareas_dependencias`, sin duplicar pares existentes y dejando `responsable_id = NULL`: el campo histórico no identifica una persona responsable del apoyo.

Hoy producción tiene cero tareas, por lo que este defecto no omite apoyos allí en este momento. En desarrollo sí hay **2 tareas con apoyo histórico sin equivalente en la tabla nueva**. El [detalle nuevo](C:/sites/pendientes_toplabel_dev/app/routes/tareas.py:149) solo devuelve la relación nueva; cualquier reconciliación de desarrollo debe revisar si esos valores antiguos siguen vigentes o fueron retirados deliberadamente.

### C. El rollback no revierte toda la migración

El [manejador de errores](C:/Users/ti/Downloads/code-migracion.py:78) llama `conn.rollback()`, pero los `ALTER TABLE` y `CREATE TABLE` causan confirmaciones implícitas en MySQL. Si falla un paso posterior, pueden quedar tablas o columnas ya modificadas. La atomicidad de una sentencia DDL no convierte toda la secuencia en una única transacción reversible. [Documentación de MySQL](https://dev.mysql.com/doc/refman/9.7/en/implicit-commit.html).

Además, el error se imprime sin relanzarlo ni devolver un código de salida distinto de cero. Un ejecutor automático podría interpretar como éxito una ejecución incompleta.

### D. No verifica el estado anterior ni el resultado

`CREATE TABLE IF NOT EXISTS` solo evita el error de existencia; no comprueba columnas, índices ni FK de una tabla previa. [Documentación de MySQL](https://dev.mysql.com/doc/refman/9.7/en/create-table.html).

`INSERT IGNORE` tampoco actualiza una asignación existente con `es_lider = 0` cuando el usuario es titular. Deben validarse conflictos, corregir liderazgo según una regla explícita y comprobar relaciones faltantes, duplicados y advertencias.

### E. Destino y credenciales implícitos

El script usa `load_dotenv()` sin ruta, tiene valores de conexión predeterminados y fija la BD productiva. Ejecutarlo desde Downloads no acredita que esté leyendo el `.env` de producción; además, las variables del proceso pueden prevalecer sobre las del archivo.

La versión corregida debe recibir explícitamente archivo de configuración y BD destino, exigir las variables necesarias, comprobar identidad del servidor/base y evitar contraseñas predeterminadas en el código. El ensayo debe poder seleccionar una BD independiente sin editar constantes arriesgadamente.

La fase 1 también está omitida, pero sus columnas y FK **ya existen en esta producción**. No es un bloqueo actual. No ejecutar [migrar_admin.py](C:/sites/pendientes_toplabel_dev/migrar_admin.py:43) para completarla: incluye reasignaciones por IDs fijos de usuarios/pilares. Tampoco usar los inicializadores que siembran catálogos y cuentas.

## 4. Código que debe corregirse antes del despliegue

1. **“Mis pendientes” consulta el campo antiguo.** [dashboard.py:86](C:/sites/pendientes_toplabel_dev/app/routes/dashboard.py:86) usa `current_user.pilar_id`, mientras crear/editar usuarios escribe `UsuarioPilar`. Debe consultar todos los pilares asignados mediante la nueva relación y conservar la visibilidad de tareas directamente asignadas. Probar usuario nuevo, varios pilares y reasignación: el pilar anterior no debe seguir dando visibilidad por un dato obsoleto.
2. **Edición de líderes inconsistente.** [admin.py:100](C:/sites/pendientes_toplabel_dev/app/routes/admin.py:100) reemplaza asignaciones sin limpiar la titularidad anterior. [models.py:70](C:/sites/pendientes_toplabel_dev/app/models.py:70) puede volver a mostrar al usuario como líder desde `pilares.responsable_id`. Definir si titular y líder son conceptos distintos y reconciliar alta, baja y cambio en una sola operación.
3. **Altas con confirmaciones parciales.** Crear [usuario](C:/sites/pendientes_toplabel_dev/app/routes/admin.py:53), [pilar](C:/sites/pendientes_toplabel_dev/app/routes/admin.py:171) y [tarea](C:/sites/pendientes_toplabel_dev/app/routes/tareas.py:52) confirma el registro principal antes de las relaciones. Usar `flush()` para obtener IDs y un solo `commit()` por operación, con rollback ante fallos.
4. **Referencia de interfaz antigua.** [base.html:58](C:/sites/pendientes_toplabel_dev/app/templates/base.html:58) todavía consulta `pilar_asignado`, relación eliminada del modelo nuevo. Adaptar a la lista de pilares.

El código productivo anterior solo mantiene los campos antiguos. Si sigue recibiendo escrituras después del traslado, las nuevas tablas quedan desactualizadas. Migración y activación deben coordinarse durante la misma ventana sin escrituras, salvo que se implemente previamente una sincronización de transición.

## 5. Procedimiento recomendado

### Paso 1. Preparar una versión verificable

- Corregir los puntos anteriores en desarrollo y preparar una migración con fases identificables: comprobación, estructura, traslado, validación.
- La comprobación inicial debe ser de solo lectura y abortar si el esquema difiere de lo previsto, hay relaciones inválidas o el destino no coincide. Verificar también permisos para crear/alterar tablas, insertar/actualizar relaciones y realizar el respaldo.
- Registrar versión/checksum y cada paso DDL completado. La repetición debe comprobar el estado ya aplicado y rechazar incompatibilidades; no asumir que la existencia de una tabla significa éxito.
- Mantener roles, usuarios, contraseñas, IDs y catálogos productivos. Las fuentes del traslado son las tablas de producción; no copiar los datos de desarrollo sobre ellas.

### Paso 2. Respaldar y demostrar que se puede restaurar

Se verificó que existe `C:\Program Files\MySQL\MySQL Server 9.5\bin\mysqldump.exe`, versión 9.5.0. Usar ese cliente. Ejemplo de respaldo lógico, para ejecución posterior con una cuenta que tenga los permisos necesarios:

```powershell
$backupDir = 'C:\sites\pendientes_toplabel_dev\revision_migracion\respaldos'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$backupFile = Join-Path $backupDir ('prod_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.sql')
$backupUser = Read-Host 'Usuario MySQL autorizado para respaldos'
& 'C:\Program Files\MySQL\MySQL Server 9.5\bin\mysqldump.exe' --host=127.0.0.1 --port=3306 --user=$backupUser --password --single-transaction --quick --routines --events --triggers --hex-blob --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 "--result-file=$backupFile" toplabel_pendientes_prod
if ($LASTEXITCODE -ne 0) { throw 'El respaldo falló; detener el procedimiento.' }
Get-Item -LiteralPath $backupFile | Select-Object FullName,Length
Get-FileHash -LiteralPath $backupFile -Algorithm SHA256
```

La contraseña se solicita interactivamente. `--single-transaction` corresponde a las tablas InnoDB observadas; durante el respaldo deben evitarse cambios de estructura. `--result-file` evita conversiones de codificación del shell. [Referencia de mysqldump](https://dev.mysql.com/doc/refman/9.7/en/mysqldump.html).

Guardar también una copia del código/configuración productiva y del respaldo fuera del servidor, con acceso restringido. El hash verifica identidad del archivo, no su restaurabilidad.

Restaurar el SQL en una **base de ensayo nueva y vacía**, por ejemplo `toplabel_pendientes_ensayo_20260914`, con el mismo charset/cotejamiento productivo. El ejemplo de dump omite `--databases` para no incluir automáticamente selección/creación del esquema original; revisar igualmente que el SQL no dirija escrituras a producción antes de importarlo. Verificar errores, conteos, esquema y relaciones de la restauración. No se ha realizado ese ensayo en esta revisión.

### Paso 3. Ensayar los cambios mínimos en el clon

1. Permitir `NULL` en `tareas.pilar_id`, preservando tipo y política FK observados.
2. Crear `usuarios_pilares` con las columnas del script, índice único de par y FK `CASCADE`; declarar explícitamente InnoDB y el cotejamiento productivo.
3. Crear `tareas_dependencias` con las FK del script. No imponer una nueva regla de unicidad de apoyos sin definir si se permiten varias personas del mismo pilar en una tarea.
4. Validar el esquema resultante. Si alguna tabla ya existe por un intento anterior, comparar su definición antes de continuar.
5. En una transacción de datos posterior al DDL, trasladar las dos fuentes de membresías, reconciliar liderazgo y trasladar apoyos históricos. Validar antes de confirmar.
6. Ejecutar la misma migración otra vez en el clon antes de habilitar la aplicación: debe conservar las mismas relaciones sin duplicados. Probar también una interrupción entre pasos y recuperación del estado parcial.

En una primera ejecución sobre la fotografía actual se esperan **10 filas en `usuarios_pilares`, 7 con liderazgo**, y **0 en `tareas_dependencias`**. Los 19 usuarios, 9 pilares, sus IDs, roles y credenciales deben conservarse. Si hay actividad previa a la ventana, recalcular estas expectativas a partir de las fuentes.

### Paso 4. Validación funcional del ensayo

- Iniciar una instancia aislada de la aplicación nueva apuntando explícitamente al clon y a otro puerto.
- Comprobar inicio de sesión, listados, miembros de pilares y conservación de las 10 asignaciones históricas.
- Crear un usuario colaborador en dos pilares, comprobar “Mis pendientes”, retirarlo de uno y comprobar que pierde la visibilidad correspondiente.
- Cambiar/quitar un líder y comprobar titularidad, listados y selector de responsables.
- Crear tareas con pilar y sin pilar; agregar varios apoyos, con y sin responsable; comprobar detalle, bitácora, cambios de estado, folios y fechas.
- Provocar en el clon un error de relación al crear usuario/tarea y comprobar que no queda el registro principal confirmado parcialmente.
- Para probar apoyos antiguos, crear un caso de prueba en el clon y comprobar que se traslada exactamente una vez.
- Medir duración del DDL y probar restauración/recuperación. Las verificaciones funcionales no fueron ejecutadas como parte de esta revisión de solo lectura.

### Paso 5. Ventana productiva

1. Detener las escrituras de aplicación, API, importadores y procesos externos; drenar peticiones/transacciones activas.
2. Confirmar el destino efectivo del servicio, repetir inventario y hacer el respaldo final, conservando la versión anterior de código/configuración.
3. Ejecutar la migración ensayada con límites de espera de bloqueos y registro de pasos. Ante cualquier fallo, detenerse e inspeccionar el estado parcial.
4. Validar esquema y relaciones, comparar datos originales y registrar el resultado.
5. Activar el conjunto coherente de código nuevo: modelos, rutas, inicialización, plantillas, JS y CSS. Mantener la configuración productiva; evitar copiar `.env` o `venv` de desarrollo indiscriminadamente.
6. Comprobar salud y casos críticos antes de reabrir escrituras; después vigilar errores y listados.

### Paso 6. Recuperación

Si falla antes de reabrir escrituras, conservar registros del intento y usar el procedimiento ensayado: completar de forma controlada el cambio o restaurar el respaldo en una base limpia de recuperación y volver al código/configuración anterior. Verificar antes de volver a servir tráfico.

Si ya se aceptaron escrituras nuevas, volver solo al código antiguo puede ocultar asignaciones múltiples, apoyos o tareas sin pilar. Restaurar el respaldo inicial también descartaría los cambios posteriores. Primero detener escrituras y preservar el estado actual; luego recuperar/reconciliar esos cambios o corregir hacia adelante. Se observó `log_bin=1`, pero eso no acredita retención suficiente ni recuperación a un instante probada.

No eliminar campos/tablas históricos en esta primera transición. El traslado desde campos antiguos debe quedar registrado como migración puntual: volver a ejecutarlo después de que la aplicación nueva retire asignaciones podría reintroducir relaciones obsoletas.

## Anexo. Consultas de aceptación

Ejecutar en el clon y, durante la ventana, en el destino productivo explícitamente seleccionado. Requieren que las tablas nuevas ya existan. Tras el traslado, todos los indicadores de faltantes/duplicados siguientes deben ser cero; el ejecutor debe evaluarlos y hacer rollback de la fase de datos si falla alguno, antes de confirmar esa fase.

```sql
SELECT DATABASE() AS base_actual, VERSION() AS version_mysql;

SELECT COUNT(*) AS membresias_historicas_faltantes
FROM usuarios u
LEFT JOIN usuarios_pilares a
  ON a.usuario_id = u.id AND a.pilar_id = u.pilar_id
WHERE u.pilar_id IS NOT NULL AND a.id IS NULL;

SELECT COUNT(*) AS titulares_sin_liderazgo
FROM pilares p
LEFT JOIN usuarios_pilares a
  ON a.usuario_id = p.responsable_id AND a.pilar_id = p.id
WHERE p.responsable_id IS NOT NULL
  AND (a.id IS NULL OR COALESCE(a.es_lider, 0) <> 1);

SELECT COUNT(*) AS lideres_historicos_sin_liderazgo
FROM usuarios u
LEFT JOIN usuarios_pilares a
  ON a.usuario_id = u.id AND a.pilar_id = u.pilar_id
WHERE u.pilar_id IS NOT NULL AND COALESCE(u.es_responsable, 0) <> 0
  AND (a.id IS NULL OR COALESCE(a.es_lider, 0) <> 1);

SELECT COUNT(*) AS apoyos_historicos_faltantes
FROM tareas t
LEFT JOIN tareas_dependencias d
  ON d.tarea_id = t.id AND d.pilar_id = t.pilar_dependencia_id
WHERE t.pilar_dependencia_id IS NOT NULL AND d.id IS NULL;

SELECT COUNT(*) AS pares_duplicados
FROM (
  SELECT usuario_id, pilar_id
  FROM usuarios_pilares
  GROUP BY usuario_id, pilar_id
  HAVING COUNT(*) > 1
) duplicados;

SELECT COUNT(*) AS asignaciones, SUM(es_lider = 1) AS lideres
FROM usuarios_pilares;
```

En la fotografía productiva actual, la última consulta debe devolver 10 asignaciones y 7 líderes después de la migración inicial. Complementar con comparación de conteos/datos originales, comprobación de FK e inspección del esquema. Estas consultas no sustituyen la prueba funcional ni la restauración del respaldo.

## Conclusión

La estructura nueva puede incorporarse a producción, pero **el adjunto necesita corregirse y el despliegue del código tiene bloqueos funcionales**. El siguiente paso seguro es preparar la migración corregida y ensayarla en una copia restaurada de la BD productiva. Este informe no certifica una migración ejecutada ni un respaldo restaurado.
