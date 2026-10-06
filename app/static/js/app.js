document.addEventListener('DOMContentLoaded', () => {
  const origenModal = new WeakMap();
  document.addEventListener('show.bs.modal', evento => {
    origenModal.set(evento.target, evento.relatedTarget || document.activeElement);
  });
  document.addEventListener('hidden.bs.modal', evento => {
    const origen = origenModal.get(evento.target);
    if (origen?.isConnected && origen !== document.body) origen.focus();
    origenModal.delete(evento.target);
  });
  // 1. Inicializar todas las tablas del sistema automáticamente
  initMotorTablasDinamicas();
  // 2. Inicializar cambio de estatus
  initCambioEstatus();
});

// ==========================================================
// MOTOR UNIVERSAL DE TABLAS (DESACOPLADO Y GENÉRICO)
// ==========================================================
function initMotorTablasDinamicas() {
  const modulos = document.querySelectorAll('.contenedor-tabla-modulo');

  modulos.forEach(modulo => {
    if (modulo.dataset.inicializado) return;
    modulo.dataset.inicializado = 'true';
    const table = modulo.querySelector('table.tabla-dinamica');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    // Fila especial de sin resultados (aislada por completo de los datos)
    const noResultRow = tbody.querySelector('.fila-sin-resultados');

    // Lista fija de filas de datos reales
    const originalRows = Array.from(tbody.querySelectorAll('tr:not(.fila-sin-resultados)'));
    let currentRows = [...originalRows];

    // Controles dentro de este módulo
    const searchInput = modulo.querySelector('.tabla-buscador');
    const selectFilters = modulo.querySelectorAll('.tabla-filtro-select');
    const clearBtn = modulo.querySelector('.tabla-btn-limpiar');
    const infoEl = modulo.querySelector('.tabla-info-paginacion');
    const controlsEl = modulo.querySelector('.tabla-controles-paginacion');

    const claveEstado = modulo.dataset.estadoClave;
    if (claveEstado) {
      try {
        const estado = JSON.parse(sessionStorage.getItem(claveEstado) || '{}');
        if (searchInput) searchInput.value = estado.q || '';
        selectFilters.forEach((sel,i) => { sel.value = estado.filtros?.[i] || ''; });
      } catch (_) {}
    }
    // Los enlaces anteriores del panel siguen funcionando, sin recortar datos en el servidor.
    const raizVistas = modulo.closest('[data-ambito="direccion"]');
    if (raizVistas && modulo.id === `panel-${raizVistas.dataset.inicial}`) {
      const params = new URLSearchParams(location.search);
      if (params.has('q') && searchInput) searchInput.value = params.get('q');
      selectFilters.forEach(sel => { if (params.has(sel.dataset.filtro)) sel.value = params.get(sel.dataset.filtro); });
    }
    function guardarFiltros() {
      if (claveEstado) try { sessionStorage.setItem(claveEstado, JSON.stringify({q:searchInput?.value || '', filtros:Array.from(selectFilters,s=>s.value)})); } catch (_) {}
    }
    const pageSize = 20;
    let currentPage = 1;
    let currentSortCol = -1;
    let sortAsc = true;

    function render() {
      const total = currentRows.length;
      const totalPages = Math.ceil(total / pageSize) || 1;
      if (currentPage > totalPages) currentPage = totalPages;
      if (currentPage < 1) currentPage = 1;

      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;

      // Ocultar todas las filas de datos
      originalRows.forEach(r => r.style.display = 'none');

      // Si no hay resultados coincidentes
      if (total === 0) {
        if (noResultRow) noResultRow.style.display = '';
        if (infoEl) infoEl.textContent = '0 registros encontrados';
        if (controlsEl) controlsEl.innerHTML = '';
        return;
      }

      // Si hay resultados, ocultar mensaje de vacío y mostrar página activa
      if (noResultRow) noResultRow.style.display = 'none';

      currentRows.forEach((r, idx) => {
        if (idx >= start && idx < end) {
          r.style.display = '';
        }
      });

      if (infoEl) {
        infoEl.textContent = `Mostrando ${start + 1} - ${Math.min(end, total)} de ${total} registros`;
      }

      // Controles de paginación con nombres accesibles y foco conservado.
      if (controlsEl) {
        controlsEl.replaceChildren();
        if (totalPages <= 1) return;
        function pagina(etiqueta, texto, destino, deshabilitada = false, actual = false, simbolo = false) {
          const item = document.createElement('li');
          item.className = `page-item ${deshabilitada ? 'disabled' : actual ? 'active' : ''}`;
          const enlace = document.createElement('a');
          enlace.className = 'page-link';
          enlace.href = '#';
          enlace.setAttribute('aria-label', etiqueta);
          if (actual) enlace.setAttribute('aria-current', 'page');
          if (deshabilitada) {
            enlace.setAttribute('aria-disabled', 'true');
            enlace.tabIndex = -1;
          }
          if (simbolo) {
            const span = document.createElement('span');
            span.setAttribute('aria-hidden', 'true');
            span.textContent = texto;
            enlace.appendChild(span);
          } else enlace.textContent = texto;
          enlace.addEventListener('click', evento => {
            evento.preventDefault();
            if (deshabilitada) return;
            currentPage = destino;
            render();
            controlsEl.querySelector('[aria-current="page"]')?.focus();
          });
          item.appendChild(enlace);
          controlsEl.appendChild(item);
        }
        pagina('Primera página', '««', 1, currentPage === 1, false, true);
        pagina('Página anterior', '«', currentPage - 1, currentPage === 1, false, true);
        let startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, startPage + 4);
        if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);
        for (let p = startPage; p <= endPage; p++) pagina(`Página ${p}`, String(p), p, false, p === currentPage);
        pagina('Página siguiente', '»', currentPage + 1, currentPage === totalPages, false, true);
        pagina('Última página', '»»', totalPages, currentPage === totalPages, false, true);
      }
    }

    function filtrar() {
      guardarFiltros();
      const q = searchInput ? searchInput.value.toLowerCase().trim() : '';

      currentRows = originalRows.filter(row => {
        // 1. Comprobar texto global de la fila con el input
        const textoFila = Array.from(row.cells, cell => cell.querySelector('select') ? cell.querySelector('select').selectedOptions[0]?.textContent || '' : cell.textContent).join(' ').toLowerCase();
        if (q && !textoFila.includes(q)) return false;

        // 2. Comprobar selectores específicos vinculados por data-col
        for (const sel of selectFilters) {
          const filterVal = sel.value.toLowerCase().trim();
          if (!filterVal) continue;

          if (sel.dataset.rowField) {
            if ((row.dataset[sel.dataset.rowField] || '').toLowerCase() !== filterVal) return false;
            continue;
          }
          const colIdx = sel.getAttribute('data-col');
          if (colIdx !== null) {
            const cell = row.children[parseInt(colIdx)];
            if (!cell) return false;

            // Extraer valor de celda (data-val, título del semáforo o texto directo)
            const cellVal = (
              cell.getAttribute('data-val') ||
              cell.querySelector('.semaphore-dot')?.getAttribute('title') ||
              cell.textContent
            ).toLowerCase().trim();

            if (cell.hasAttribute('data-val') ? cellVal !== filterVal : !cellVal.includes(filterVal)) return false;
          }
        }

        return true;
      });

      currentPage = 1;
      ordenarFilas();
      render();
      modulo.dispatchEvent(new CustomEvent('tabla:filtrada', {bubbles:true}));
    }

    // Eventos de Filtrado en Vivo
    if (searchInput) searchInput.addEventListener('input', filtrar);
    selectFilters.forEach(sel => sel.addEventListener('change', filtrar));

    // Botón Limpiar con icono de escoba
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        selectFilters.forEach(sel => sel.value = '');
        filtrar();
      });
    }

    function ordenarFilas() {
      if (currentSortCol < 0) return;
        currentRows.sort((a, b) => {
          const cellA = a.children[currentSortCol];
          const cellB = b.children[currentSortCol];
          if (!cellA || !cellB) return 0;
          const valA = (cellA.getAttribute('data-timestamp') || cellA.getAttribute('data-val') || cellA.textContent).trim().toLowerCase();
          const valB = (cellB.getAttribute('data-timestamp') || cellB.getAttribute('data-val') || cellB.textContent).trim().toLowerCase();
          return sortAsc
            ? valA.localeCompare(valB, undefined, { numeric: true })
            : valB.localeCompare(valA, undefined, { numeric: true });
        });

        currentRows.forEach(r => tbody.appendChild(r));
    }

    // Ordenamiento por Encabezados
    const headers = table.querySelectorAll('th.th-sortable');
    headers.forEach(th => {
      th.querySelector('.th-sort-btn')?.addEventListener('click', () => {
        const col = parseInt(th.getAttribute('data-col'));
        if (currentSortCol === col) {
          sortAsc = !sortAsc;
        } else {
          currentSortCol = col;
          sortAsc = true;
        }

        headers.forEach(h => {
          h.removeAttribute('aria-sort');
          const icon = h.querySelector('.sort-icon');
          if (icon) icon.textContent = '⇅';
        });
        th.setAttribute('aria-sort', sortAsc ? 'ascending' : 'descending');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.textContent = sortAsc ? '▲' : '▼';

        ordenarFilas();
        currentPage = 1;
        render();
      });
    });

    // Restaurar también el resultado de los filtros de esta pestaña.
    filtrar();
  });
}

// ==========================================================
// CAMBIO DE ESTATUS ASÍNCRONO CON SWEETALERT2
// ==========================================================
function initCambioEstatus() {
  document.querySelectorAll('.task-status-select').forEach(select => {
    if (select.dataset.inicializado) return;
    select.dataset.inicializado = 'true';
    select.dataset.anterior = select.value;
    select.addEventListener('change', async () => {
      const destino = select.value;
      select.value = select.dataset.anterior;
      if (destino === select.value) return;
      await abrirNotaTarea(Number(select.dataset.tareaId), {destino, anterior:select.value});
    });
  });
}

// ==========================================================
// FICHA TÉCNICA COMPLETA Y BITÁCORA DE NOTAS
// ==========================================================
async function verDetalleTarea(tareaId) {
  try {
    const res = await fetch(`/tareas/${tareaId}/detalle`);
    if (!res.ok) throw new Error("No se pudo cargar el detalle");
    const t = await res.json();

    // 1. Cargar Encabezado y Folio
    document.getElementById('det_folio').textContent = t.folio;
    document.getElementById('det_titulo').textContent = t.titulo;

    // Semáforo circular
    const dot = document.getElementById('det_semaforo_dot');
    dot.className = 'semaphore-dot ' + (
      t.semaforo === 'ROJO' ? 'dot-rojo' :
      t.semaforo === 'AMARILLO' ? 'dot-amarillo' :
      t.semaforo === 'VERDE' ? 'dot-verde' : 'dot-azul'
    );
    const estadosSemaforo = {
      ROJO: ['Vencida o bloqueada', 'exclamation'], AMARILLO: ['Por vencer', 'clock'],
      AZUL: ['En tiempo', 'minus'], VERDE: ['Completada', 'check']
    };
    const [etiquetaSemaforo, iconoSemaforo] = estadosSemaforo[t.semaforo] || estadosSemaforo.AZUL;
    dot.title = etiquetaSemaforo;
    dot.setAttribute('role', 'img');
    dot.setAttribute('aria-label', etiquetaSemaforo);
    const iconoEstado = document.createElement('i');
    iconoEstado.className = `fa-solid fa-${iconoSemaforo}`;
    iconoEstado.setAttribute('aria-hidden', 'true');
    dot.replaceChildren(iconoEstado);

    // Función auxiliar para contraste automático de texto (blanco o negro según fondo)
    function getContrast(hex) {
      if (!hex || !hex.startsWith('#')) return '#ffffff';
      const c = hex.replace('#', '');
      if (c.length === 6) {
        const r = parseInt(c.substr(0, 2), 16);
        const g = parseInt(c.substr(2, 2), 16);
        const b = parseInt(c.substr(4, 2), 16);
        const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return lum > 0.55 ? '#0f172a' : '#ffffff';
      }
      return '#ffffff';
    }

    // Badge del Pilar
    const badgePilar = document.getElementById('det_pilar');
    badgePilar.textContent = t.pilar;
    badgePilar.style.backgroundColor = t.pilar_color;
    badgePilar.style.color = getContrast(t.pilar_color);

    // Badge de Prioridad limpia (sin P0, P1...)
    const badgePrio = document.getElementById('det_prioridad');
    const prioClean = t.prioridad.includes('P0') ? 'Crítica' : t.prioridad.includes('P1') ? 'Alta' : t.prioridad.includes('P2') ? 'Media' : 'Baja';
    badgePrio.textContent = prioClean;
    badgePrio.className = 'badge ' + (
      t.prioridad.includes('P0') ? 'bg-danger' :
      t.prioridad.includes('P1') ? 'bg-warning text-dark' :
      t.prioridad.includes('P2') ? 'bg-info text-dark' : 'bg-secondary'
    );

    document.getElementById('det_estatus').textContent = t.estatus;

    // 2. Metadatos
    document.getElementById('det_responsable').textContent = t.responsable;
    document.getElementById('det_fecha_compromiso').textContent = t.fecha_compromiso;

    // 3. Pilares de Apoyo / Dependencias con contraste garantizado
    const contDeps = document.getElementById('det_dependencias_lista');
    contDeps.innerHTML = '';
    if (!t.dependencias || t.dependencias.length === 0) {
      contDeps.innerHTML = '<span class="text-muted small">Sin pilares de apoyo adicionales requeridos.</span>';
    } else {
      t.dependencias.forEach(d => {
        const badge = document.createElement('span');
        badge.className = 'badge p-2 border';
        badge.style.backgroundColor = d.pilar_color;
        badge.style.color = getContrast(d.pilar_color); // Contraste automático blanco/negro
        badge.textContent = `${d.pilar_nombre}: ${d.responsable_nombre}`;
        contDeps.appendChild(badge);
      });
    }

    // 4. Instrucciones Completas sin truncar
    document.getElementById('det_descripcion').textContent = t.descripcion;

    // 5. Historial de Notas
    mostrarAdjuntos(document.getElementById('det_adjuntos'), t.adjuntos || [], t);
    renderizarBitacoraModal(t.bitacora, t);
    prepararNotaTarea(t);
    document.getElementById('formAdjuntosTarea').hidden = !t.puede_subir;
    document.getElementById('nota_selector_archivos').hidden = !t.puede_subir;
    prepararEdicionTarea(t);

    // 6. Preparar Formulario de Nueva Nota
    document.getElementById('modal_nota_tarea_id').value = t.id;
    document.getElementById('modal_nota_comentario').value = '';

    // Mostrar ventana modal
    const modalEl = document.getElementById('modalDetalleTarea');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
    return t;

  } catch (err) {
    console.error(err);
    Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo cargar la información de la tarea.' });
  }
}

function renderizarBitacoraModal(bitacora, permisos = {}) {
  const contenedor = document.getElementById('det_lista_bitacora');
  const badgeConteo = document.getElementById('det_conteo_notas');
  badgeConteo.textContent = `${bitacora.length} registro(s)`;
  contenedor.innerHTML = '';

  if (bitacora.length === 0) {
    contenedor.innerHTML = `
      <div class="text-center py-3 text-muted small border rounded bg-white">
        No se han registrado notas ni bloqueos para esta tarea todavía.
      </div>
    `;
    return;
  }

  bitacora.forEach(b => {
    const item = document.createElement('div');
    item.className = 'p-3 border rounded bg-white shadow-xs';

    const badgeTipo = b.tipo === 'MODIFICACION'
      ? '<span class="badge bg-info-subtle text-dark border"><i class="fa-solid fa-pen-to-square fa-fw" aria-hidden="true"></i> Modificación de tarea</span>'
      : b.tipo === 'CAMBIO_ESTATUS'
      ? '<span class="badge bg-secondary-subtle text-dark border"><i class="fa-solid fa-arrows-rotate fa-fw" aria-hidden="true"></i> Cambio de estatus</span>'
      : b.tipo === 'BLOQUEO'
      ? '<span class="badge bg-danger-subtle text-danger border border-danger"><i class="fa-solid fa-triangle-exclamation fa-fw" aria-hidden="true"></i> Bloqueo</span>'
      : b.tipo === 'PROBLEMA'
      ? '<span class="badge bg-warning-subtle text-dark border">Problema</span>'
      : b.tipo === 'OBSERVACION'
      ? '<span class="badge bg-light text-dark border">Observación</span>'
      : ['NOTA_REUNION','ACUERDO'].includes(b.tipo)
      ? '<span class="badge bg-primary-subtle text-primary border border-primary"><i class="fa-solid fa-handshake fa-fw" aria-hidden="true"></i> Acuerdo</span>'
      : '<span class="badge bg-success-subtle text-success border border-success"><i class="fa-solid fa-chart-line fa-fw" aria-hidden="true"></i> Avance</span>';

    item.innerHTML = `
      <div class="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-1">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <strong class="bitacora-autor"></strong>
          ${badgeTipo}
        </div>
        <small class="text-muted bitacora-fecha"></small>
      </div>
      <div class="text-dark small bitacora-comentario" style="white-space: pre-wrap; overflow-wrap: anywhere;"></div>
    `;
    item.querySelector('.bitacora-autor').textContent = b.autor;
    item.querySelector('.bitacora-fecha').textContent = b.fecha;
    const efecto = document.createElement('div'); efecto.className = 'small fw-semibold text-muted mb-2';
    if (b.transicion) efecto.textContent = b.transicion.anterior === b.transicion.nuevo ? 'Sin cambio de estatus' : `${nombreEstatus(b.transicion.anterior)} → ${nombreEstatus(b.transicion.nuevo)}`;
    else if (b.tipo === 'BLOQUEO') efecto.textContent = 'Registro histórico · transición no registrada';
    item.querySelector('.bitacora-comentario').before(efecto);
    item.querySelector('.bitacora-comentario').textContent = b.comentario;
    if (b.adjuntos?.length) {
      const archivos = document.createElement('div');
      archivos.className = 'mt-2';
      mostrarAdjuntos(archivos, b.adjuntos, permisos);
      item.appendChild(archivos);
    }
    contenedor.appendChild(item);
  });
}
