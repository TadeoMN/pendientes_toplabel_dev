# Revisión de Lighthouse — 6 de octubre de 2026

## Reportes recibidos

Fuente: `pilares.json`, `usuarios.json`, `mis_pendientes.json` y `panel_direccion.json`, entregados por el usuario desde Downloads. Lighthouse 13.4.1, configuración de escritorio. Las URL finales corresponden a las páginas autenticadas de `http://192.168.100.24:5010`; no son mediciones de la pantalla de inicio de sesión.

Estos puntajes son anteriores a las correcciones L1–L3:

| Pantalla | Rendimiento | Accesibilidad | Buenas prácticas | SEO |
|---|---:|---:|---:|---:|
| Pilares | 97 | 96 | 74 | 91 |
| Usuarios | 97 | 97 | 74 | 91 |
| Mis pendientes | 98 | 100 | 74 | 91 |
| Panel de Dirección | 97 | 94 | 74 | 91 |

## Correcciones aplicadas en desarrollo

- **L1 (`b6008d8`):** el filtro de contraste de Jinja y el cálculo de JavaScript usan negro cuando ni blanco ni el oscuro de marca alcanzan 4.5:1. Diseño conserva su fondo violeta `#8b5cf6`; el texto pasa de blanco (4.23:1) a negro (4.96:1). Esto corrige los elementos señalados en Pilares, Usuarios y Panel de Dirección, sin modificar los colores almacenados.
- **L2 (`efdc97d`):** “Sin titular asignado” usa `text-danger-emphasis`. El texto real en Edge es `#58151c`, frente al fondo claro `#f8f9fa`, en lugar del rojo anterior que no alcanzaba el contraste requerido.
- **L3 (`c07de2c`):** los controles de paginación tienen una superficie mínima de 36 × 36 px en escritorio y conservan los 44 px de móvil. Primera/anterior/siguiente/última página usan iconos decorativos y mantienen sus nombres accesibles. Se eliminan los caracteres de flecha que Lighthouse interpretaba como texto visible distinto del nombre accesible.

## Verificación posterior de las correcciones

En la sesión autenticada de Edge se recargó Pilares y se comprobó el color calculado de ambos elementos corregidos. Se verificó también el texto negro sobre el badge violeta en Usuarios y en los pilares de apoyo del Panel de Dirección.

Los seis controles visibles de paginación del panel miden 36 × 36 px. La página 2 muestra “Mostrando 21 - 23 de 23 registros”; Primera página vuelve a los primeros 20. Las flechas ya no contienen texto visible y conservan sus etiquetas accesibles. Las 20 filas del panel siguen midiendo exactamente 84 px.

Las comprobaciones existentes de Python y JavaScript, incluido XSS y prevención de doble envío, pasaron; la sintaxis de `app.js` también se verificó. No se cambiaron permisos, rutas, esquema ni dependencias de la aplicación. Producción no se modificó.

Evidencia visual: `C:/Users/ti/.codex/visualizations/2026/10/06/01a112b4-b9aa-7b21-b31a-3e07e6249d81/lighthouse-fixes-pilares.png`.

## Pendientes y límites

Se necesita repetir Lighthouse en Pilares, Usuarios y Panel de Dirección para confirmar los puntajes después de los cambios. No se atribuye un nuevo 100 a ninguna pantalla. Los cuatro archivos recibidos son de escritorio: falta la medición móvil, y Lighthouse no sustituye las pruebas manuales de accesibilidad.

El 74 en Buenas prácticas incluye hallazgos de transporte HTTP y políticas de seguridad. HTTPS/CSP requieren revisar la configuración de despliegue; quedan fuera de esta corrección de interfaz. El 91 de SEO incluye ausencia de metadescripción. Los reportes también señalan optimización del tamaño del logo y recursos sin utilizar; parte del JavaScript proviene de extensiones del navegador, por lo que no debe atribuirse a la aplicación y limita la comparación de rendimiento. Estos hallazgos permanecen abiertos.

La ejecución automática autenticada mediante conexión directa Puppeteer/CDP a Edge fue rechazada por la revisión automática de aprobación porque evitaba el canal permitido de control del navegador. No se usó otro transporte para eludir ese bloqueo. La nueva medición queda disponible mediante Lighthouse de DevTools y exportación de JSON por el usuario.
