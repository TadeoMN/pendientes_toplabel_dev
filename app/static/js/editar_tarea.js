// El permiso de la interfaz es informativo; el servidor valida cada guardado.
let detalleEditable = null;
let detalleModificado = false;

function prepararEdicionTarea(tarea) {
  detalleEditable = tarea;
  document.getElementById('det_fecha_creacion').textContent = tarea.fecha_creacion;
  document.getElementById('det_editar').hidden = !tarea.puede_editar;
  document.getElementById('formEditarTarea').hidden = true;
  document.getElementById('det_lectura').hidden = false;
}

document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('modalDetalleTarea');
  if (!modal) return;
  const form = document.getElementById('formEditarTarea');
  const campos = document.getElementById('det_campos_edicion');
  const pilar = form.elements.pilar_id;
  const responsable = form.elements.responsable_id;
  const apoyos = document.getElementById('edit_apoyos');
  const error = document.getElementById('edit_error');
  let guardando = false;

  function agregarApoyo(apoyo = {}) {
    apoyos.appendChild(SelectoresTarea.filaApoyo(
      detalleEditable.opciones.pilares, detalleEditable.opciones.usuarios, apoyo));
  }

  function estadoCierre() {
    const cambio = form.elements.estatus.value !== detalleEditable.estatus;
    document.getElementById('edit_motivo_grupo').hidden = !cambio;
    form.elements.nota_estatus.required = cambio && (['BLOQUEADO','COMPLETADO'].includes(detalleEditable.estatus) || ['BLOQUEADO','COMPLETADO'].includes(form.elements.estatus.value));
    form.elements.fecha_cierre.disabled = form.elements.estatus.value !== 'COMPLETADO';
    if (form.elements.fecha_cierre.disabled) form.elements.fecha_cierre.value = '';
  }

  document.getElementById('det_editar').addEventListener('click', () => {
    if (!detalleEditable?.puede_editar) return;
    const valores = detalleEditable.campos;
    SelectoresTarea.pilares(pilar, detalleEditable.opciones.pilares, valores.pilar_id, 'Sin pilar asignado (General / Transversal)');
    SelectoresTarea.responsables(responsable, detalleEditable.opciones.usuarios, valores.pilar_id,
      {id: valores.responsable_id, nombre: valores.responsable});
    // Conservar un origen histórico aunque no esté entre las opciones nuevas.
    Array.from(form.elements.fuente.options).filter(o => o.dataset.historico).forEach(o => o.remove());
    if (valores.fuente && !Array.from(form.elements.fuente.options).some(o => o.value === valores.fuente)) {
      const opcion = new Option(valores.fuente, valores.fuente);
      opcion.dataset.historico = 'true';
      form.elements.fuente.add(opcion);
    }
    ['titulo', 'descripcion', 'prioridad', 'estatus', 'fecha_inicio', 'fecha_compromiso', 'fecha_cierre', 'fuente']
      .forEach(nombre => { form.elements[nombre].value = valores[nombre] ?? ''; });
    apoyos.replaceChildren();
    detalleEditable.dependencias.forEach(agregarApoyo);
    form.elements.nota_estatus.value = '';
    form.elements.estatus.disabled = !detalleEditable.puede_estatus;
    estadoCierre();
    error.hidden = true;
    form.hidden = false;
    document.getElementById('det_lectura').hidden = true;
    document.getElementById('det_editar').hidden = true;
    form.elements.titulo.focus();
  });
  pilar.addEventListener('change', () => SelectoresTarea.responsables(responsable, detalleEditable.opciones.usuarios, pilar.value));
  form.elements.estatus.addEventListener('change', estadoCierre);
  document.getElementById('edit_agregar_apoyo').addEventListener('click', () => agregarApoyo());
  document.getElementById('edit_cancelar').addEventListener('click', () => {
    prepararEdicionTarea(detalleEditable);
    document.getElementById('det_editar').focus();
  });
  modal.addEventListener('hide.bs.modal', event => {
    if (guardando) event.preventDefault();
  });
  modal.addEventListener('hidden.bs.modal', () => {
    // Refrescar también conteos, filtros y filas cuando cambió el pilar destino.
    if (detalleModificado) { detalleModificado = false; if (typeof refrescarPendientes === 'function') refrescarPendientes().catch(e => Swal.fire({icon:'error',text:e.message})); else window.location.reload(); }
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (guardando || !form.reportValidity()) return;
    const datos = {version: detalleEditable.version, nota_estatus: form.elements.nota_estatus.value};
    ['titulo', 'descripcion', 'prioridad', 'estatus', 'fecha_inicio', 'fecha_compromiso', 'fuente']
      .forEach(nombre => { datos[nombre] = form.elements[nombre].value; });
    datos.fecha_cierre = form.elements.fecha_cierre.value || null;
    datos.pilar_id = Number(pilar.value) || null;
    datos.responsable_id = Number(responsable.value);
    datos.apoyos = Array.from(apoyos.children).map(fila => ({
      pilar_id: Number(fila.querySelector('.select-apoyo-pilar').value),
      responsable_id: Number(fila.querySelector('.select-apoyo-resp').value) || null
    }));
    guardando = true;
    campos.disabled = true;
    error.hidden = true;
    try {
      const respuesta = await fetch(`/tareas/${detalleEditable.id}/editar`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(datos)
      });
      const resultado = await respuesta.json();
      if (!respuesta.ok || !resultado.success) throw new Error(resultado.message || 'No se pudo guardar la tarea.');
      detalleModificado ||= resultado.modificado;
      await verDetalleTarea(detalleEditable.id);
      Swal.fire({toast: true, position: 'top-end', icon: 'success',
        title: resultado.modificado ? 'Cambios guardados en la bitácora' : 'No hay cambios por guardar',
        showConfirmButton: false, timer: 2500});
    } catch (err) {
      error.textContent = err.message || 'No se pudo conectar con el servidor.';
      error.hidden = false;
    } finally {
      guardando = false;
      campos.disabled = false;
    }
  });
});
