# Verificación de correcciones de interfaz

Fecha: 6 de octubre de 2026. Copia: C:\sites\pendientes_toplabel_dev.
Rama: mejoras-ui-accesibilidad. Sitio de pruebas: http://192.168.100.24:5010.

Este informe complementa VERIFICACION_UI_FINAL.md. La revisión anterior no detectó adecuadamente el desplazamiento horizontal de la página a partir de 768 px ni la pérdida de acceso a acciones durante el desplazamiento móvil. Las correcciones siguientes responden a las capturas y a las instrucciones posteriores del usuario. Estas instrucciones sustituyen la X de encabezado solicitada en A7 y el botón de error de A14 por un cierre en el pie.

## Cambios aplicados

| ID | Resultado | Archivos principales |
| --- | --- | --- |
| C1 | La página no se desplaza horizontalmente; la tabla y las barras de pestañas/pilares mantienen su desplazamiento interno. | main.css |
| C2 | Semáforo de 24 px con icono centrado, fondo integrado y columna de 96 px. Filas de tareas y usuarios de escritorio de 84 px, contenido de 60 px y relleno vertical de 12 px por lado. Separadores sin aumentar la altura. | main.css, tabla_tareas.html, usuarios.html |
| C3 | Cinco tarjetas por página en móvil; barra persistente con filtros desplegables y crear tarea. Veinte filas por página en escritorio. El cambio de ancho conserva la posición aproximada del registro. | app.js, filtros_tareas.html, main.css |
| C4 | Indicadores de bitácora y archivos a .9rem. Archivos cuenta adjuntos activos directamente asociados a la tarea, excluye retirados y respeta archivos.ver. Bitácora respeta notas.ver. | tabla_tareas.html, main.css |
| C5 | Los ocho modales de tarea, usuario y pilar cierran desde su pie. Formularios largos tienen cuerpo desplazable y pie accesible. Errores flash permanecen sin temporizador y se cierran con Cerrar; el cierre del menú lateral se conserva. | nueva_tarea.html, detalle_tarea.html, usuarios.html, pilares.html, base.html, main.css |
| C6 | Miembros: líderes primero, luego colaboradores; ambos grupos ordenados alfabéticamente con configuración es-MX. Estrellas de liderazgo amarillas en usuarios, titulares y miembros. Los selectores nativos conservan la leyenda Líder. | pilares.html, usuarios.html, main.css |
| C7 | Leyenda y paginación encima de las tablas de tareas y usuarios. La paginación se distribuye en varias líneas cuando no cabe. | tabla_tareas.html, usuarios.html, main.css |
| C8 | Iconos locales coherentes para crear, guardar, cancelar, cerrar, retirar/eliminar, editar, buscar, limpiar y cerrar sesión. Tooltips por ratón o foco de teclado en escritorio; icono y leyenda siempre visibles en pantallas táctiles. Nombres accesibles independientes del tooltip. Títulos distinguen Detalle de tarea y Editar tarea. | acciones.js, base.html, main.css, app.js, editar_tarea.js, filtros_tareas.html, usuarios.html |

## Verificación realizada

- Navegador integrado basado en Chromium, sitio de desarrollo autorizado. No había Chrome conectado para ejecutar la prueba en Chrome externo.
- Panel de Dirección a 1440, 768 y 375 px; Mis pendientes con Colaborador a 1440, 768 y 375 px; gestión de usuarios a 1440 y 768 px; miembros y modales de pilares a 768 px; consulta y edición con Administrador y consulta con Líder.
- A 768 px se midieron veinte filas de tareas exactamente de 84 px y sus contenedores interiores de 60 px. Las once filas de usuarios midieron 84 px. Las filas visibles de Colaborador también midieron 84 px. A 1440 px se verificaron veinte filas de 84 px.
- Desplazamiento horizontal fuera de la tabla: window.scrollX permaneció en 0. Dentro de la tabla: scrollLeft pasó de 0 a 658, sin desplazar la página. El ancho del cuerpo coincide con el ancho útil del navegador a 768 y 375 px. El scrollWidth de la raíz puede contabilizar contenido interno de barras desplazables; se verificó el movimiento real y los límites visibles, además de medidas.
- A 375 px: cinco tarjetas, controles superiores, paginación dentro del ancho útil, barra de herramientas persistente a 56 px al desplazar la página, búsqueda y limpiar operativos. El formulario de crear tarea mantiene el pie dentro de los 812 px de alto del viewport, con cuerpo desplazable.
- Indicadores de .9rem medidos en 14.4 px. Tarea TL-CALI-004: dos registros de bitácora y dos archivos; la pestaña Archivos muestra los dos adjuntos activos correspondientes.
- Lista Producción Flexo: Juan Muñoz (Líder) antes de Guadalupe Segundo (Colaborador). Estrella medida rgb(250, 204, 21).
- Foco de teclado sobre Limpiar muestra su tooltip. Esc cierra el modal de miembros y devuelve el foco al botón de apertura. En móvil las acciones llevan texto visible y dimensiones mínimas de 44 px.
- Administrador dispone de Editar tarea; para la cuenta de Líder consultada la acción permanece ausente según el permiso recibido. El menú de Colaborador conserva solo Mis pendientes. No se cambiaron reglas de autorización ni se guardaron cambios en tareas durante esta revisión.
- El título cambia a Editar tarea al activar edición y vuelve a Detalle de tarea al cancelar. Los botones dinámicos de adjuntos y confirmación de cerrar sesión reciben sus iconos.
- Sin errores de consola en las consultas realizadas.
- `venv\Scripts\python.exe scripts/verificar_ui_etapa1.py`: cinco pruebas aprobadas, incluida la comprobación del nuevo cierre del error flash sin temporizador.
- `node scripts/verificar_ui_etapa1.cjs`: pruebas XSS, lista vacía, doble envío, validación, GET, fetch, preventDefault y restauración aprobadas. Se agregó comprobación de líderes primero y orden con acentos, conservando los datos originales.
- Sintaxis JavaScript verificada con `node --check` para acciones.js, app.js y editar_tarea.js. `git diff --check` sin errores.

## Límites pendientes

Lighthouse se mantiene para la revisión final por instrucción del usuario. No se ejecutó ni se inventaron puntajes: no hay Lighthouse instalado ni Chrome conectado. NVDA sigue sin estar disponible. Las pruebas de teclado y nombres accesibles no sustituyen estas auditorías. Tampoco se hizo una nueva prueba de creación, carga o eliminación de datos; las regresiones de envío se verificaron con las pruebas existentes y la revisión de permisos fue de interfaz.

No se modificaron rutas, modelos, permisos, CSRF, esquema ni lógica de negocio. No se instalaron dependencias ni se tocó producción. Se conservó el commit del usuario 5e19702. No se hizo push, merge ni despliegue.

## Evidencia

Capturas en C:\Users\ti\.codex\visualizations\2026\10\06\01a112b4-b9aa-7b21-b31a-3e07e6249d81:

- correcciones-768.png: tabla, semáforo, filtros y paginación a 768 px.
- correcciones-escritorio.png: Panel de Dirección a 1440 px.
- correcciones-movil.png: controles móviles y paginación a 375 px.
- correcciones-modal-movil.png: formulario largo con cierre en el pie a 375 px.
