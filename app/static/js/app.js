// Motor Universal de Tablas Dinámicas, Paginación, Ordenamiento e Implementación de SweetAlert2
document.addEventListener('DOMContentLoaded', () => {
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

      // Generar Controles de Paginación
      if (controlsEl) {
        controlsEl.innerHTML = '';
        if (totalPages <= 1) return;

        // 1. Ir a Primera Página (««)
        const firstLi = document.createElement('li');
        firstLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        firstLi.innerHTML = `<a class="page-link" href="#" title="Primera página">&laquo;&laquo;</a>`;
        firstLi.onclick = (e) => { e.preventDefault(); if (currentPage > 1) { currentPage = 1; render(); } };
        controlsEl.appendChild(firstLi);

        // 2. Ir a Página Anterior («)
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" title="Página anterior">&laquo;</a>`;
        prevLi.onclick = (e) => { e.preventDefault(); if (currentPage > 1) { currentPage--; render(); } };
        controlsEl.appendChild(prevLi);

        // 3. Ventana de Páginas Numeradas (máximo 5 visibles)
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        if (endPage - startPage < 4) {
          startPage = Math.max(1, endPage - 4);
        }

        for (let p = startPage; p <= endPage; p++) {
          const pLi = document.createElement('li');
          pLi.className = `page-item ${p === currentPage ? 'active' : ''}`;
          pLi.innerHTML = `<a class="page-link" href="#">${p}</a>`;
          pLi.onclick = ((num) => (e) => { e.preventDefault(); currentPage = num; render(); })(p);
          controlsEl.appendChild(pLi);
        }

        // 4. Ir a Página Siguiente (»)
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" title="Página siguiente">&raquo;</a>`;
        nextLi.onclick = (e) => { e.preventDefault(); if (currentPage < totalPages) { currentPage++; render(); } };
        controlsEl.appendChild(nextLi);

        // 5. Ir a Última Página (»»)
        const lastLi = document.createElement('li');
        lastLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        lastLi.innerHTML = `<a class="page-link" href="#" title="Última página">&raquo;&raquo;</a>`;
        lastLi.onclick = (e) => { e.preventDefault(); if (currentPage < totalPages) { currentPage = totalPages; render(); } };
        controlsEl.appendChild(lastLi);
      }
    }

    function filtrar() {
      const q = searchInput ? searchInput.value.toLowerCase().trim() : '';

      currentRows = originalRows.filter(row => {
        // 1. Comprobar texto global de la fila con el input
        const textoFila = row.textContent.toLowerCase();
        if (q && !textoFila.includes(q)) return false;

        // 2. Comprobar selectores específicos vinculados por data-col
        for (const sel of selectFilters) {
          const filterVal = sel.value.toLowerCase().trim();
          if (!filterVal) continue;

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

            if (!cellVal.includes(filterVal)) return false;
          }
        }

        return true;
      });

      currentPage = 1;
      render();
    }

    // Eventos de Filtrado en Vivo
    if (searchInput) searchInput.addEventListener('input', filtrar);
    selectFilters.forEach(sel => sel.addEventListener('change', filtrar));

    // Botón Limpiar con icono de escoba
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        selectFilters.forEach(sel => sel.value = '');
        currentRows = [...originalRows];
        currentPage = 1;
        render();
      });
    }

    // Ordenamiento por Encabezados
    const headers = table.querySelectorAll('th.th-sortable');
    headers.forEach(th => {
      th.addEventListener('click', () => {
        const col = parseInt(th.getAttribute('data-col'));
        if (currentSortCol === col) {
          sortAsc = !sortAsc;
        } else {
          currentSortCol = col;
          sortAsc = true;
        }

        headers.forEach(h => {
          const icon = h.querySelector('.sort-icon');
          if (icon) icon.textContent = '⇅';
        });
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.textContent = sortAsc ? '▲' : '▼';

        currentRows.sort((a, b) => {
          const cellA = a.children[col];
          const cellB = b.children[col];
          if (!cellA || !cellB) return 0;
          const valA = (cellA.getAttribute('data-timestamp') || cellA.getAttribute('data-val') || cellA.textContent).trim().toLowerCase();
          const valB = (cellB.getAttribute('data-timestamp') || cellB.getAttribute('data-val') || cellB.textContent).trim().toLowerCase();
          return sortAsc 
            ? valA.localeCompare(valB, undefined, { numeric: true }) 
            : valB.localeCompare(valA, undefined, { numeric: true });
        });

        currentRows.forEach(r => tbody.appendChild(r));
        currentPage = 1;
        render();
      });
    });

    // Render Inicial
    render();
  });
}

// ==========================================================
// CAMBIO DE ESTATUS ASÍNCRONO CON SWEETALERT2
// ==========================================================
function initCambioEstatus() {
  document.querySelectorAll('.task-status-select').forEach(select => {
    select.addEventListener('change', async () => {
      const tareaId = select.getAttribute('data-tarea-id');
      const nuevoEstatus = select.value;

      let notaBloqueo = "";
      if (nuevoEstatus === 'BLOQUEADO') {
        const { value: texto, isConfirmed } = await Swal.fire({
          title: '¿Cuál es el motivo del bloqueo?',
          input: 'textarea',
          inputPlaceholder: 'Describe el material, persona o área que te detiene...',
          showCancelButton: true,
          confirmButtonText: 'Reportar Bloqueo',
          cancelButtonText: 'Cancelar',
          confirmButtonColor: '#dc3545',
          inputValidator: (val) => {
            if (!val) return 'Debes ingresar una descripción del bloqueo.';
          }
        });

        if (!isConfirmed) {
          location.reload();
          return;
        }
        notaBloqueo = texto;
      }

      try {
        const res = await fetch(`/tareas/${tareaId}/actualizar-estatus`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ estatus: nuevoEstatus, nota: notaBloqueo })
        });

        const data = await res.json();
        if (data.success) {
          const dot = document.querySelector(`#semaforo-${tareaId}`);
          if (dot && data.semaforo) {
            dot.className = 'semaphore-dot ' + (
              data.semaforo === 'ROJO' ? 'dot-rojo' :
              data.semaforo === 'AMARILLO' ? 'dot-amarillo' :
              data.semaforo === 'VERDE' ? 'dot-verde' : 'dot-azul'
            );
            dot.title = data.semaforo;
          }

          Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: `Estatus actualizado a ${nuevoEstatus}`,
            showConfirmButton: false,
            timer: 2000
          });
        }
      } catch (err) {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Error al conectar con el servidor.' });
      }
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
    dot.title = t.semaforo;

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
        badge.innerHTML = `<strong>${d.pilar_nombre}</strong>: ${d.responsable_nombre}`;
        contDeps.appendChild(badge);
      });
    }

    // 4. Instrucciones Completas sin truncar
    document.getElementById('det_descripcion').textContent = t.descripcion;

    // 5. Historial de Notas
    renderizarBitacoraModal(t.bitacora);

    // 6. Preparar Formulario de Nueva Nota
    document.getElementById('modal_nota_tarea_id').value = t.id;
    document.getElementById('modal_nota_comentario').value = '';

    // Mostrar ventana modal
    const modalEl = document.getElementById('modalDetalleTarea');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();

  } catch (err) {
    console.error(err);
    Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo cargar la información de la tarea.' });
  }
}

function renderizarBitacoraModal(bitacora) {
  const contenedor = document.getElementById('det_lista_bitacora');
  const badgeConteo = document.getElementById('det_conteo_notas');
  badgeConteo.textContent = `${bitacora.length} nota(s)`;
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

    const badgeTipo = b.tipo === 'BLOQUEO' 
      ? '<span class="badge bg-danger-subtle text-danger border border-danger">⚠️ Bloqueo Reportado</span>'
      : b.tipo === 'NOTA_REUNION'
      ? '<span class="badge bg-primary-subtle text-primary border border-primary">Acuerdo de Reunión</span>'
      : '<span class="badge bg-success-subtle text-success border border-success">Avance Operativo</span>';

    item.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-1">
        <div class="d-flex align-items-center gap-2">
          <strong>${b.autor}</strong>
          ${badgeTipo}
        </div>
        <small class="text-muted">${b.fecha}</small>
      </div>
      <div class="text-dark small" style="white-space: pre-wrap;">${b.comentario}</div>
    `;
    contenedor.appendChild(item);
  });
}

async function enviarNotaModal(e) {
  e.preventDefault();
  const tareaId = document.getElementById('modal_nota_tarea_id').value;
  const tipo = document.getElementById('modal_nota_tipo').value;
  const comentario = document.getElementById('modal_nota_comentario').value.trim();

  if (!comentario) return;

  try {
    const res = await fetch(`/tareas/${tareaId}/agregar-nota`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ tipo, comentario })
    });

    const data = await res.json();
    if (data.success) {
      const resDetalle = await fetch(`/tareas/${tareaId}/detalle`);
      const t = await resDetalle.json();
      renderizarBitacoraModal(t.bitacora);
      document.getElementById('modal_nota_comentario').value = '';

      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: 'Nota agregada al historial',
        showConfirmButton: false,
        timer: 2000
      });
    } else {
      Swal.fire({ icon: 'error', title: 'Error', text: data.message });
    }
  } catch (err) {
    Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo guardar la nota.' });
  }
}