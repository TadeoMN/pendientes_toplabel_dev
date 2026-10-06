let contextoNota = null;
let notaGuardando = false;
const nombreEstatus = valor => ({PENDIENTE:'Pendiente',EN_PROCESO:'En proceso',BLOQUEADO:'Bloqueado',COMPLETADO:'Completado'}[valor] || valor);
function prepararNotaTarea(tarea, destino = null) {
  contextoNota = {tarea, destino};
  const form = document.getElementById('formNotaDirecta');
  form.reset();
  document.getElementById('modal_nota_tarea_id').value = tarea.id;
  document.getElementById('seccion_nota').hidden = destino ? !tarea.puede_estatus : !tarea.puede_notar;
  form.hidden = false;
  document.getElementById('nota_tipo_grupo').hidden = Boolean(destino);
  document.getElementById('nota_titulo').textContent = destino ? 'Nota del cambio de estatus' : 'Agregar nota';
  document.getElementById('nota_error').hidden = true;
  document.getElementById('nota_selector_archivos').hidden = !tarea.puede_subir;
  actualizarEfectoNota();
}
function actualizarEfectoNota() {
  if (!contextoNota) return;
  const {tarea, destino} = contextoNota;
  const bloquea = !destino && document.getElementById('modal_nota_tipo').value === 'BLOQUEO';
  const opcion = document.getElementById('nota_bloqueo_opcion');
  opcion.hidden = !bloquea || !tarea.puede_estatus || ['BLOQUEADO','COMPLETADO'].includes(tarea.estatus);
  const checkbox = document.getElementById('nota_cambiar_bloqueo');
  if (opcion.hidden) checkbox.checked = false;
  const nuevo = destino || (checkbox.checked ? 'BLOQUEADO' : null);
  document.getElementById('nota_efecto').textContent = nuevo ? `Se guardará la nota y cambiará el estatus: ${nombreEstatus(tarea.estatus)} → ${nombreEstatus(nuevo)}.` : `Se guardará la nota sin cambiar el estatus (${nombreEstatus(tarea.estatus)}).`;
  document.getElementById('modal_nota_comentario').required = !destino || ['BLOQUEADO','COMPLETADO'].includes(destino) || ['BLOQUEADO','COMPLETADO'].includes(tarea.estatus);
}
async function abrirNotaTarea(id, opciones = {}) {
  const t = await verDetalleTarea(id);
  if (!t) return;
  if (opciones.destino && t.estatus !== opciones.anterior) {
    await Swal.fire({icon:'warning',text:'El estatus cambió desde que se cargó la tabla. Revisa el detalle actualizado.'});
    detalleModificado = true;
    return;
  }
  if (opciones.destino && t.estatus === 'COMPLETADO' && opciones.destino !== 'EN_PROCESO') {
    await Swal.fire({icon:'info',text:'Para reabrir esta tarea selecciona En proceso y explica el motivo.'});
    return;
  }
  prepararNotaTarea(t, opciones.destino || null);
  const enfocar = () => document.getElementById('seccion_nota').scrollIntoView({block:'start',behavior:'smooth'});
  const modal = document.getElementById('modalDetalleTarea');
  modal.addEventListener('shown.bs.modal', enfocar, {once:true});
  enfocar();
}
async function enviarNotaModal(event) {
  event.preventDefault();
  if (notaGuardando || !contextoNota) return;
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const {tarea, destino} = contextoNota;
  const body = new FormData(form);
  body.set('version', tarea.version);
  if (destino) body.set('estatus', destino);
  else if (document.getElementById('nota_cambiar_bloqueo').checked) body.set('estatus','BLOQUEADO');
  const error = document.getElementById('nota_error'); error.hidden = true;
  const boton = form.querySelector('button[type=submit]');
  notaGuardando = true; boton.disabled = true;
  try {
    const res = await fetch(`/tareas/${tarea.id}/${destino ? 'actualizar-estatus' : 'agregar-nota'}`, {method:'POST',headers:{'X-Requested-With':'XMLHttpRequest'},body});
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'No se pudo guardar la nota.');
    detalleModificado = true;
    form.reset();
    if (typeof refrescarPendientes === 'function') { await refrescarPendientes(); detalleModificado = false; }
    await verDetalleTarea(tarea.id);
    Swal.fire({toast:true,position:'top-end',icon:'success',title:'Nota guardada',showConfirmButton:false,timer:2200});
  } catch (e) { error.textContent = e.message; error.hidden = false; }
  finally { notaGuardando = false; boton.disabled = false; }
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal_nota_tipo')?.addEventListener('change',actualizarEfectoNota);
  document.getElementById('nota_cambiar_bloqueo')?.addEventListener('change',actualizarEfectoNota);
  document.getElementById('modalDetalleTarea')?.addEventListener('hide.bs.modal', e => {if (notaGuardando) e.preventDefault();});
});
