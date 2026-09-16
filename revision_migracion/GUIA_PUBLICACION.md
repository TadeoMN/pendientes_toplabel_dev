# Publicación de estructura y aplicación corregida

## Estado de entrega

Correcciones aplicadas en `C:\sites\pendientes_toplabel_dev`. Los scripts productivos están preparados y se ejecutaron contra producción **únicamente en diagnóstico**. No se modificó código ni BD del ambiente productivo.

Último diagnóstico del 14/09/2026: `toplabel_pendientes_prod`, MySQL 9.5.0, 19 usuarios, 9 pilares, **2 tareas**, 0 bitácoras. Faltan dos tablas nuevas y permitir tareas sin pilar. Repetir el diagnóstico en la ventana de publicación porque estos datos pueden cambiar.

## Correcciones incluidas

- “Mis pendientes” consulta todos los pilares efectivos del usuario y conserva las tareas asignadas directamente. Al retirar o reemplazar una asignación deja de usar el pilar anterior.
- Las lecturas de usuarios, miembros, encabezado y apoyos de tareas admiten los campos históricos. **La migración puede crear las tablas nuevas vacías y conservar el uso de los datos existentes.** No se importan registros desde desarrollo ni se copian relaciones en el script de BD.
- Cuando un administrador edita las asignaciones de un usuario o la titularidad de un pilar, la aplicación conserva las relaciones necesarias en el formato nuevo y limpia los campos históricos de los usuarios afectados dentro de esa operación. Quitar la última asignación no la vuelve a activar por el dato antiguo.
- Se permiten varios líderes y un titular por pilar. Cambiar titular conserva al anterior como líder secundario. Elegir “Sin asignar” en el titular lo deja como colaborador. Retirar el pilar o degradar al titular desde usuarios limpia la titularidad; no se elige automáticamente un reemplazo.
- Altas y ediciones de usuarios/pilares, creación de tareas y apoyos, notas y cambios de estado se guardan de forma atómica. Ante un error de BD se revierte la operación de datos.
- Se validan IDs, duplicados y valores permitidos por los ENUM productivos. La API de ingesta guarda el lote completo o lo rechaza; fechas inválidas, áreas/personas ambiguas y prioridades desconocidas devuelven error en vez de crear un lote parcial. Se implementó la serialización de tareas que la API ya invocaba.
- El modelo de `usuarios_pilares` declara el índice único del par y `created_at`; se corrigieron las relaciones ORM redundantes y la dependencia circular entre usuarios/pilares.

Las pruebas de visibilidad conservan la regla previa: tareas de los pilares del usuario y tareas de las que es responsable directo. La participación como apoyo no añade por sí sola otra regla de visibilidad.

## Opción recomendada: un comando para BD y código

Script: [desplegar_produccion.ps1](C:/sites/pendientes_toplabel_dev/scripts/desplegar_produccion.ps1).

### 1. Diagnóstico, sin aplicar

En PowerShell:

```powershell
& 'C:\sites\pendientes_toplabel_dev\scripts\desplegar_produccion.ps1'
```

Compara los archivos `app` de desarrollo con producción y ejecuta el diagnóstico del esquema. Guarda un informe en `revision_migracion\publicaciones`. En la comparación realizada se identificaron **12 archivos** distintos, incluyendo los cambios previos de interfaz de desarrollo y las correcciones de esta entrega.

### 2. Preparar la ventana

Detener el proceso de la aplicación productiva y cualquier importador/API/worker que pueda escribir en esa base; esperar a que terminen peticiones y transacciones activas. Mantener detenido el acceso de escritura hasta terminar la validación. El switch de mantenimiento declara que este paso se hizo; no detiene servicios automáticamente.

Conservar una copia del respaldo fuera del servidor. Para una validación final con datos reales, restaurar un respaldo reciente de producción en un clon independiente y probar allí la versión nueva. Los ensayos de esta entrega usaron **el esquema productivo observado y datos sintéticos**, no una copia de los registros productivos.

### 3. Aplicar durante mantenimiento

```powershell
& 'C:\sites\pendientes_toplabel_dev\scripts\desplegar_produccion.ps1' -Aplicar -MantenimientoConfirmado
```

La secuencia es:

1. Crear un respaldo ZIP del `app` productivo y comprobar que puede leerse, en una carpeta con ACL privada.
2. Ejecutar la migración de BD. Si hay pasos pendientes, obtener primero un respaldo SQL con `mysqldump` 9.5; verificar salida, tablas, marcador de finalización y SHA256.
3. Crear `usuarios_pilares`, crear `tareas_dependencias` y permitir `NULL` en `tareas.pilar_id`, según los pasos que falten.
4. Comprobar estructura, FK, conteos y huellas SHA256 de los datos originales. Las tablas recién creadas deben quedar vacías.
5. Copiar los archivos modificados de `app` y verificar sus hashes. Se conserva la configuración productiva: `.env`, `app/config.py`, `venv`, `wsgi.py` y Apache. No se copian cachés Python.
6. Guardar `publicacion.json` con respaldo, archivos previstos, hashes, archivos copiados y resultado. El informe de BD está en otra subcarpeta del mismo directorio de publicaciones.

El script no inicia/reinicia servicios ni reabre tráfico. Una copia de archivos incompleta se registra como fallo y exige mantener el mantenimiento hasta recuperar/verificar el código.

### 4. Reiniciar y validar

Reiniciar el proceso que ejecuta la aplicación para cargar el código nuevo. Antes de reabrir escrituras generales, verificar:

- Inicio de sesión, dashboard, administración de usuarios/pilares y “Mis pendientes”.
- Conservación de los usuarios, pilares y las **dos tareas existentes** (o el conteo obtenido al inicio de la ventana).
- Membresías y titulares actuales visibles aunque las tablas nuevas se hayan creado vacías.
- Detalle de tareas y apoyos; ausencia de errores en logs.
- En el clon, creación de tareas generales, varios apoyos y usuarios con varios pilares. Las pruebas que crean registros deben planearse expresamente si se repiten en producción.

## Opción: aplicar solo el esquema

Script: [migracion_estructura.py](C:/sites/pendientes_toplabel_dev/scripts/migracion_estructura.py).

Diagnóstico:

```powershell
& 'C:\sites\pendientes_toplabel_dev\venv\Scripts\python.exe' 'C:\sites\pendientes_toplabel_dev\scripts\migracion_estructura.py' --env-file 'C:\sites\pendientes_toplabel\.env' --database toplabel_pendientes_prod --output-dir 'C:\sites\pendientes_toplabel_dev\revision_migracion\publicaciones' --dry-run
```

Aplicación del esquema, después de detener escritores:

```powershell
& 'C:\sites\pendientes_toplabel_dev\venv\Scripts\python.exe' 'C:\sites\pendientes_toplabel_dev\scripts\migracion_estructura.py' --env-file 'C:\sites\pendientes_toplabel\.env' --database toplabel_pendientes_prod --output-dir 'C:\sites\pendientes_toplabel_dev\revision_migracion\publicaciones' --apply --confirm-database toplabel_pendientes_prod --maintenance-confirmed
```

Esta opción no copia código. Para habilitar los métodos nuevos también se debe publicar la aplicación corregida. Si se mantienen activos los archivos anteriores, estos continuarán trabajando con sus campos históricos; las funciones nuevas se habilitan con el cambio de código.

## Controles y límites del migrador

- Sin `--apply`, solo hace consultas y crea informes locales. Lee exclusivamente el `.env` absoluto indicado, sin interpolación ni credenciales predeterminadas; `DB_NAME` debe coincidir exactamente con `--database`.
- Está definido para **MySQL 9.5 y el esquema productivo inspeccionado**. Rechaza desviaciones de columnas, FK, índices únicos, motor, cotejamiento, tablas adicionales, triggers, rutinas, eventos o CHECK no contemplados. No intenta transformar la BD de desarrollo, que tiene otras diferencias.
- Conserva los ENUM, timestamps, valores predeterminados y políticas de borrado actuales. Los únicos cambios de negocio emitidos son los tres DDL previstos; no ejecuta INSERT, UPDATE ni DELETE de registros.
- Usa un bloqueo entre ejecuciones de este migrador y límites de espera para DDL. Ese bloqueo no impide escrituras externas; por eso se requiere mantenimiento.
- Verifica cada paso, detecta cambios de datos durante la ejecución y termina con error si algo difiere. Nunca imprime contraseñas ni filas de usuarios.
- Si se reejecuta con todo aplicado, informa `already_applied` y conserva los datos. Si un intento quedó a medias, valida el esquema antes de completar los pasos pendientes.
- Los respaldos SQL contienen datos productivos sensibles. Se guardan en carpetas privadas; la contraseña temporal del cliente se elimina al terminar. Verificar salida y hash no sustituye probar una restauración.

## Recuperación ante un fallo

MySQL confirma los DDL implícitamente: no existe rollback global de toda la migración. Mantener escritores detenidos y revisar `informe.json`/`publicacion.json`.

- **Falló el respaldo:** no se inicia DDL ni copia de código.
- **Falló un DDL:** pueden existir pasos confirmados. Conservar el respaldo del primer intento. Corregir la causa y reintentar después de revisar el plan, o restaurar el respaldo en una base nueva de recuperación y validar antes de cambiar la conexión.
- **Falló la copia de código:** consultar la lista `copied` del manifiesto. Restaurar el ZIP completo en una carpeta temporal, comprobarlo y recuperar la versión anterior con el servicio detenido. Revisar también archivos que el manifiesto marque como nuevos (`before: null`), pues no estaban en el ZIP. El script no borra archivos automáticamente.
- **Ya hubo escrituras con la versión nueva:** conservar primero una copia del estado actual y reconciliar esas operaciones. Volver solo al código viejo puede ocultar asignaciones múltiples; restaurar un respaldo anterior descartaría los cambios posteriores. Favorecer corregir hacia adelante o una recuperación validada que preserve esas escrituras.

## Pruebas realizadas

- **25 pruebas automatizadas**: visibilidad multipilar y reasignación, conservación de lectura histórica sin insertar, quitar/degradar/cambiar titular, validación, rollback de altas incompletas, apoyos, notas, estados y lotes API; precondiciones, destino, integridad del plan y reintento del migrador.
- MySQL Community **9.5.0 en una instancia separada**, puerto 33316, con el esquema observado y registros sintéticos: respaldo, aplicación de los 3 DDL, hashes de datos conservados y segunda ejecución sin cambios.
- Restauración del respaldo en otra base de ensayo: esquema original recuperado y huellas de datos idénticas.
- Fallo simulado de respaldo: ningún cambio de esquema. Fallo tras el primer DDL: registrado; reintento completó únicamente los dos pasos pendientes.
- Aplicación Flask sobre MySQL migrado: rutas principales, lectura histórica sin backfill, edición multipilar/titular, tarea general, apoyos, ENUM de bitácora y cambio de estado.
- Script de publicación completa probado en una **carpeta de ensayo**, conservando `.env` y `app/config.py`.
- Diagnóstico en producción: correcto, sin cambios. No se realizó despliegue productivo.

Para repetir las pruebas automatizadas desde desarrollo:

```powershell
Set-Location 'C:\sites\pendientes_toplabel_dev'
& '.\venv\Scripts\python.exe' -m unittest discover -v
```

Los resúmenes del ensayo están en `revision_migracion\ensayos`. Los archivos originales de desarrollo previos a esta corrección están en `revision_migracion\originales_dev`; el análisis previo quedó en `INFORME_MIGRACION.md` como referencia histórica.
