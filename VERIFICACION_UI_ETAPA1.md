# Mejoras de interfaz: etapa 1

Fecha: 6 de octubre de 2026 (México).
Rama: `mejoras-ui-accesibilidad`, creada desde `main` con el repositorio limpio.
Se modificó exclusivamente `C:\sites\pendientes_toplabel_dev`.
No se hizo merge, push ni despliegue; no se modificó la copia de producción.

## Estado de la etapa

Las ocho tareas están implementadas y verificadas con las pruebas disponibles.
Actualización posterior: el usuario proporcionó la cuenta de Dirección, confirmó
el acceso por `http://192.168.100.24:5010` y pidió dejar Lighthouse para el final.
Se continuó en ese orden con las etapas 2, 3 y 4. El resultado vigente y las
limitaciones de Chrome, Lighthouse y NVDA se encuentran en `VERIFICACION_UI_FINAL.md`.

## Tareas y archivos

| ID | Resultado | Archivos |
| --- | --- | --- |
| B1 | Filas de miembros con elementos DOM y `textContent`; opciones dinámicas de pilares con JSON y `new Option`. | `app/templates/admin/pilares.html`, `app/templates/admin/usuarios.html` |
| B2 | Celda de Estado con `data-val` exacto; el motor de filtros no cambió. | `app/templates/admin/usuarios.html` |
| B3 | Opciones del filtro generadas con todos los roles activos suministrados por la ruta. | `app/templates/admin/usuarios.html` |
| A3 | Cierre del offcanvas con `btn-close`, visible sobre fondo claro. | `app/templates/base.html` |
| A6 | KPI amarillo con `text-warning-emphasis`; conserva el icono de reloj de arena. | `app/templates/dashboard_direccion.html` |
| A11 | Autocompletado de usuario, contraseña actual y contraseñas nuevas. | `app/templates/login.html`, `app/templates/admin/usuarios.html` |
| A14 | Errores sin timer y con botón para cerrar; otros flashes a 5 s con progreso; mensajes con `tojson` y `titleText`. | `app/templates/base.html` |
| N1 | Bloqueo de envíos POST repetidos, spinner, texto original conservado, `aria-busy` y restauración al regresar desde la caché. Ignora los tres formularios con fetch y los envíos cancelados. Incluye botones submit implícitos de roles y límites. | `app/static/js/formularios.js`, `app/templates/base.html`, `scripts/verificar_ui_etapa1.cjs`, `scripts/verificar_ui_etapa1.py` |

Un commit por tarea, en el orden solicitado, con B1 primero. Las pruebas y este
informe se incluyen en el commit N1.

## Seguridad y compatibilidad

- El segundo punto inseguro encontrado fue `OPCIONES_PILARES_HTML` en usuarios:
  los nombres del servidor se insertaban en un literal JavaScript y luego en HTML.
  Ahora se serializan con `tojson` y se asignan como texto de opciones DOM.
- Se revisaron los `innerHTML` y `insertAdjacentHTML` en las plantillas y el JS propio.
  Los restantes insertan HTML fijo, insignias seleccionadas entre constantes o
  números de paginación locales. Los datos de la bitácora, adjuntos, dependencias
  y selectores de tareas ya utilizan texto u opciones DOM.
- El flash usaba una cadena JavaScript entre comillas y el campo HTML `title` de
  SweetAlert. A14 también corrige ese punto con JSON y `titleText`.
- Sin cambios en rutas, modelos, consultas, permisos, configuración, estructura de
  base de datos, `app.js` ni `csrf.js`. Se conservaron los IDs, clases y `data-*`.

## Pruebas realizadas

Servidor del proyecto: `http://192.168.100.24:5010`, indicado por el usuario.
Se confirmó que el proceso ejecuta el Python de `pendientes_toplabel_dev` con `wsgi.py`.
El navegador verificó que recibe el nuevo script y los atributos de autocompletado.

- `python scripts/verificar_ui_etapa1.py`: cinco pruebas aprobadas. Compila todas las
  plantillas Jinja y comprueba estado, roles, JSON seguro, autocompletado, flashes,
  carga de scripts, cierre y KPI. Usa fixtures sin leer ni escribir una base de datos.
- `node scripts/verificar_ui_etapa1.cjs`: regresiones aprobadas para XSS, lista vacía,
  doble envío incluso antes del timer, formularios inválidos y GET, los tres IDs de
  fetch, `preventDefault` posterior, botones implícitos, conservación de valores,
  spinner, `aria-busy` y restauración de botones.
- `node --check app/static/js/formularios.js` y `git diff --check`: aprobados.
- XSS en navegador con fixtures: nombre, username, email, título de pilar y opciones
  con `<img src=x onerror=alert(1)>`, backticks, `${alert(2)}` y `</script>` aparecen
  como texto. Ninguna imagen de esos datos se creó y no apareció ningún alert.
- Activos e inactivos se separaron en fixtures. En el proyecto real hay 11 usuarios
  activos y ningún inactivo; «Inactivos» devuelve cero. Cada rol disponible filtró
  correctamente; el rol sin usuarios devolvió cero resultados.
- Color calculado del KPI: `rgb(102, 77, 3)` (`#664d03`). Contraste WCAG sobre blanco:
  **7.99:1**. Su icono conserva forma y color oscuro independiente del número.
- Error de login real: permanece más de cinco segundos, con cierre mediante teclado.
  Mensaje de éxito en fixtures: muestra barra y desaparece automáticamente.
- Envío POST de login aceptado con CSRF después del ajuste final del bloqueo.
- Doble clic en «Guardar y Asignar Tarea»: una sola tarea creada, confirmada tanto
  en pantalla como con consulta de solo lectura. **TL-GRAL-006, ID 26**, título
  «Verificación UI N1 · doble envío · 2026-10-06», asignada a la cuenta administradora.
  Se deja identificada como dato de prueba; no se eliminó.
- Se revisaron y capturaron login, Mis pendientes, Panel de Dirección, usuarios y
  pilares a **1440, 768 y 375 px**. No hubo scroll horizontal de la página; las tablas
  todavía tienen scroll interno, cuya adaptación corresponde a la etapa 4.
- Se probaron Enter y Esc en accesos, cierre de menú, confirmación de salida,
  formularios de nueva tarea/nuevo usuario y cierre de mensajes; Tab en nueva tarea.
  Esto no sustituye un recorrido exhaustivo con teclado ni NVDA.
- No se observaron errores de consola JavaScript en las pantallas inspeccionadas.

## Roles comprobados

| Cuenta de prueba | Rol real | Resultado |
| --- | --- | --- |
| direccion | Administrador del sistema | Panel, usuarios y pilares disponibles. |
| alexis | Líder | Mis pendientes disponible; sin Administración ni Panel en menú. |
| lupitas | Colaborador | Mis pendientes disponible; sin Administración ni Panel. Acceso directo a usuarios y dashboard denegado. |

La cuenta `alexis` tiene rol Líder, no Dirección. No se alteraron asignaciones de
roles para probar. Falta acceso de prueba a una cuenta con rol Dirección.

## Lighthouse y pendientes

| Pantalla | Antes | Después |
| --- | --- | --- |
| Mis pendientes | No medido | No medido |
| Panel de Dirección | No medido | No medido |
| Gestión de usuarios | No medido | No medido |

Solo está conectado el navegador integrado. Chrome y Lighthouse no están disponibles
en las herramientas conectadas, y no se instalaron dependencias nuevas. No se
inventaron puntajes ni se certifica el umbral de 95.

También quedan pendientes: oferta real de guardar/rellenar contraseña en Chrome,
recorrido exhaustivo con teclado/NVDA, pruebas con Dirección, y el checklist final
de CRUD, notas, estatus, archivos, filtros guardados y enlaces parametrizados.
La medición y corrección de todos los colores de pilar corresponde a A2 en la etapa 3;
no se han declarado colores aprobados o rechazados en esta etapa.

## Evidencias

Capturas locales en:
`C:\Users\ti\.codex\visualizations\2026\10\06\01a112b4-b9aa-7b21-b31a-3e07e6249d81`.

- `etapa1-doble-envio.png`: tarea de prueba única.
- `etapa1-login-{1440,768,375}.png`: error persistente en login.
- `etapa1-pendientes-{1440,768,375}.png`.
- `etapa1-direccion-{1440,768,375}.png`.
- `etapa1-usuarios-{1440,768,375}.png`.
- `etapa1-pilares-{1440,768,375}.png`.

## Diferencias respecto del plan

- La paginación y el filtro actual ya comparan exactamente celdas con `data-val`;
  no fue necesario modificar `app.js` para B2.
- Se corrigió en B1 la construcción de opciones de pilares de usuarios, además de
  la lista de miembros indicada originalmente.
- Se usa `titleText` además de `tojson`: codificar JSON protege el contexto de
  JavaScript, pero por sí solo no impide que SweetAlert interprete un `title` como HTML.
- Roles y límites usan botones sin atributo `type`; su tipo DOM es `submit`, por lo
  que N1 obtiene los controles de `form.elements` para cubrirlos también.
- N1 bloquea de inmediato el segundo evento, pero retrasa la desactivación visual
  hasta después del envío nativo para preservar los datos del botón submit y permitir
  que todos los listeners terminen antes de comprobar `defaultPrevented`.
