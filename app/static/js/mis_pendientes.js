function iniciarPendientes(activa = 'mias') { iniciarVistasTareas(document.getElementById('pendientes'), activa); }
async function refrescarPendientes() {
  const activa = document.querySelector('#pendientes [aria-selected="true"]')?.dataset.pestana || 'mias';
  const res = await fetch('/mis-pendientes', {cache:'no-store'});
  if (!res.ok) throw new Error('No se pudo actualizar la lista de tareas.');
  const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
  const root = doc.getElementById('pendientes');
  if (!root) throw new Error('Actualiza la página para revisar tu sesión.');
  document.getElementById('pendientes').replaceWith(root);
  iniciarPendientes(activa); initMotorTablasDinamicas(); initCambioEstatus();
}
document.addEventListener('DOMContentLoaded', () => iniciarPendientes());
