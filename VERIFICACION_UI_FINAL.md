# Verificación final de interfaz Top Label

Fecha: 6 de octubre de 2026. Rama: `mejoras-ui-accesibilidad`, desde `main` limpio.
Única copia modificada: `C:\sites\pendientes_toplabel_dev`.
Acceso autorizado: http://192.168.100.24:5010. Sin push, merge ni despliegue.
No se agregaron dependencias ni se cambiaron rutas, modelos, permisos o esquema.
La única modificación Python de la aplicación es el filtro de contraste de A2.
Las pruebas funcionales sí crearon datos identificados como verificación en desarrollo.

## Etapas, tareas y archivos

| Etapa | Tareas realizadas | Archivos principales |
|---|---|---|
| 1 | B1, B2, B3, A3, A6, A11, A14, N1 | admin/pilares.html, admin/usuarios.html, login.html, base.html, dashboard_direccion.html, formularios.js; pruebas en scripts/verificar_ui_etapa1.* |
| 2 | A1, A7, A12, A13, A4, A8, A5, A9, A10 | Plantillas de tareas, usuarios, pilares y páginas; selector_archivos.html; app.js, selectores_tarea.js, dashboard_responsive.js, main.css |
| 3 | D1, A2, D2, D3, D4, D5, A16, A15, N4 | main.css, app/__init__.py, color.js, app.js, notas.js, dashboard_responsive.js y plantillas |
| 4 | R1 y R2 juntos, R3, R4, R5 y N2 juntos, N3 | tabla_tareas.html, main.css, modales, usuarios.html, pilares.html, selectores_tarea.js |
| Opcional final | M1 | detalle_tarea.html y notas.js; informe actualizado |

Los nombres de plantilla anteriores son relativos a `app/templates`; los JS y CSS,
a `app/static/js` y `app/static/css`. D4 quedó cubierto por A12; no tiene commit duplicado.
La rama contiene 31 commits de tareas, sin commits fixup pendientes.
R1/R2 y R5/N2 se agruparon porque comparten implementación. M1 queda como último
commit funcional y se puede revertir por separado. Las correcciones de revisión
se integraron en sus commits mediante autosquash.

**Etapa 1:** pruebas de renderizado y de JavaScript; XSS mostrado como texto,
estados exactos, todos los roles, autocomplete, flash seguro y bloqueo de doble
submit. La tarea TL-GRAL-006 se creó una sola vez con doble clic.

**Etapa 2:** IDs únicos, etiquetas de campos y archivos, títulos de modales,
retorno de foco, ordenación con Enter, paginación anunciada y navegación al
contenido. Recorrido de Dirección, pendientes, usuarios y pilares a tres anchos.
Los encabezados y semáforos conservan la información accesible.

**Etapa 3:** capturas antes y después, paleta calculada, contraste Python/JS,
fuentes de al menos 12.8 px en texto visible, movimiento reducido y ausencia de
selectores muertos. SweetAlert tiene z-index 1060 y el modal 1055; se comprobó
una confirmación real encima del modal. SweetAlert inyecta sus estilos locales;
por eso sus variables de marca se aplican en `.swal2-container`.

**Etapa 4:** tarjetas grid conservando nueve celdas y sus atributos, paginación
con tres registros visibles en la página 2, mensaje sin resultados, controles de
44 px, modales de 375 px y filas dinámicas que se ajustan. Crear, editar,
cambiar estatus, agregar nota, adjuntar y retirar se verificaron con ambos roles.

**M1:** flechas entre Detalle, Bitácora y Archivos; apertura inicial en Detalle;
cambio de estatus abre Bitácora y enfoca el comentario. El número de registros se
actualiza; archivos se adjuntan y retiran desde su pestaña. No hay IDs duplicados.

## Lista de aceptación final

| Punto solicitado | Resultado |
|---|---|
| Lighthouse >=95, antes y después | **Pendiente.** Lighthouse no está instalado y Chrome no está conectado. No se inventaron puntajes ni se instalaron paquetes. El usuario autorizó aplazarlo al cierre. |
| Sin scroll horizontal de página a 375 px | **Verificado** en login, Dirección, pendientes, usuarios, pilares, roles, auditoría y límites de archivos. La tabla de tareas tampoco tiene scroll horizontal. Las tablas administrativas mantienen su contenedor responsive. |
| Uso por teclado y foco visible | **Verificado en los recorridos realizados**: Tab/Shift+Tab, Enter, Espacio, Esc y flechas; filtros, ordenación, paginación, modales, pestañas, menú, roles y campos de límites. NVDA no está disponible; no se declara una auditoría completa con lector de pantalla. |
| Todo texto con contraste >=4.5 | **Excepción:** Diseño #8b5cf6 alcanza 4.23 con blanco. Se conservaron los colores de la base. La revisión de estilos calculados del texto visible no encontró otra excepción en las pantallas revisadas. No sustituye Lighthouse/axe. |
| Sin emojis en plantillas y JS propios | **Verificado** por búsqueda Unicode, excluyendo bibliotecas locales de terceros. Los iconos son Font Awesome con aria-hidden. |
| Flujo completo con Dirección y Colaborador | **Verificado** en TL-GRAL-007 y TL-GRAL-008, incluyendo notas y archivo de texto desechable. |
| Permisos del Colaborador | **Verificado:** solo ve Mis pendientes; Dirección y usuarios devuelven «No tienes permiso para acceder a esta función». Su creación permite únicamente asignarse a sí mismo. |
| Sesión y enlaces vista/q | **Verificado:** `/dashboard?vista=otros_directores&q=Verificación`, recarga, sesión y limpieza de filtros; se conservaron sus hooks. |
| Consola sin errores | **Verificado** en las pantallas y flujos revisados mediante el registro de errores del navegador integrado. |

## Lighthouse y lector de pantalla

| Pantalla | Antes | Después |
|---|---|---|
| Mis pendientes | No medido | No medido |
| Panel de Dirección | No medido | No medido |
| Gestión de usuarios | No medido | No medido |

No se omitió ninguna tarea de implementación. Quedan pendientes las mediciones
externas con Lighthouse/Chrome y la validación NVDA. El navegador disponible fue
el integrado de Codex; las pruebas responsive se hicieron a 1440, 768 y 375 px,
no mediante Chrome DevTools. Tampoco se emuló visión acromatópsica: se comprobaron
los cuatro iconos y sus etiquetas independientes del color.

## Contraste de pilares y diferencia de A2

| Pilar | Fondo | Texto elegido | Contraste |
|---|---|---|---|
| Calidad | #059669 | #0f172a | 4.74 |
| Dirección | #000000 | #ffffff | 21.00 |
| Diseño | #8b5cf6 | #ffffff | **4.23** |
| Mantenimiento | #abd908 | #0f172a | 10.76 |
| Procesos | #4b5563 | #ffffff | 7.56 |
| Producción Flexo | #ad1de2 | #ffffff | 5.18 |
| Producion Empaque | #24ebc9 | #0f172a | 11.73 |
| Recursos Humanos | #d97706 | #0f172a | 5.60 |
| SAC | #0891b2 | #0f172a | 4.85 |
| Sistemas | #2563eb | #ffffff | 5.17 |

Para Diseño el usuario debe elegir otro fondo; no se cambió su registro.
Resultados de consola Python y JS: #10b981, #14b8a6, #22c55e y #0284c7 devuelven
#0f172a; #1e40af y #000 devuelven #ffffff; #fff devuelve #0f172a; valores inválidos
(devuelve oscuro) y hex de tres dígitos comprobados.

La aceptación original de A2 pide blanco para #0284c7, pero contradice el algoritmo:
blanco da 4.10 y #0f172a da 4.36. Se aplicó el algoritmo solicitado de mayor contraste.
Los controles fijos de marca usan negro (#000, 5.13:1), evitando esa limitación.

## Diferencias con el código real

- `#tablaFiltrada` solo aparece como ancla histórica en JS: no existe un elemento
  con ese ID. Se quitó el CSS sin uso y se mantuvo su comportamiento de enlace.
- Auditoría conserva usuario_id: el modelo no tiene la relación para obtener su
  nombre y el encargo prohíbe cambiar la consulta.
- La insignia sintética «Sin pilar» del detalle usa fondo neutro y texto oscuro;
  no depende de que el usuario tenga permiso de edición.
- Los tres usos del selector de archivos necesitaban IDs distintos; se asignaron
  prefijos nt_archivos, det_archivos y nota_archivos y sus ayudas correspondientes.
- En móvil los encabezados son visualmente ocultos; al recibir foco por teclado
  vuelven a mostrarse para mantener la ordenación visible y operable.
- Los atributos de región/tabindex de apoyos permanecen, como permite R2; en móvil
  desaparecen el límite de alto y el scroll. El arrastre no se activa sin desbordamiento.
- Se conservó el bloqueo nativo síncrono de N1; el estado visual se actualiza tras
  serializar el formulario para no perder valores de botones en el envío POST.

## Datos de prueba y evidencia

- ID 26 / TL-GRAL-006: verificación N1; también se usó para M1.
- ID 28 / TL-GRAL-007: Dirección (Tadeo).
- ID 29 / TL-GRAL-008: Colaborador (Guadalupe).
- `prueba-ui.txt`: archivo sin datos personales ni credenciales, adjuntado y
  retirado mediante la interfaz. Los registros de bitácora permanecen.
- No se eliminaron las tareas ni datos ajenos. No se almacenaron contraseñas.

Capturas antes/después y finales en:
`C:\Users\ti\.codex\visualizations\2026\10\06\01a112b4-b9aa-7b21-b31a-3e07e6249d81`.
Incluyen etapa2-* (antes de color/limpieza), etapa4-*, final-detalle-375.png,
final-direccion-1440.png, prueba-direccion.png y prueba-colaborador.png.

Verificación automatizada final:
`venv\Scripts\python.exe scripts/verificar_ui_etapa1.py` (cinco pruebas OK) y
`node scripts/verificar_ui_etapa1.cjs` (XSS, lista vacía, submit duplicado,
validación, GET, fetch, preventDefault y restauración OK).
