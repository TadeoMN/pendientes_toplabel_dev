// Mismas opciones, grupos y cascadas para crear y editar tareas.
const SelectoresTarea = (() => {
  const pertenece = (usuario, pilarId) => (usuario.pilares || []).some(p => String(p.id) === String(pilarId));
  const esLider = (usuario, pilarId) => (usuario.pilares || []).some(p => p.es_lider && (!pilarId || String(p.id) === String(pilarId)));
  const nombre = usuario => usuario.nombre_completo;
  function ordenar(usuarios, pilarId) {
    return [...usuarios].sort((a, b) => Number(esLider(b, pilarId)) - Number(esLider(a, pilarId))
      || nombre(a).localeCompare(nombre(b), 'es', {sensitivity: 'base'}) || Number(a.id) - Number(b.id));
  }
  function etiqueta(usuario, pilarId) {
    return `${nombre(usuario)} (${esLider(usuario, pilarId) ? 'Líder' : 'Colaborador'})`;
  }
  function conservarActual(select, actual) {
    if (actual?.id && !Array.from(select.options).some(o => o.value === String(actual.id))) {
      const grupo = document.createElement('optgroup');
      grupo.label = 'Asignación actual';
      grupo.appendChild(new Option(`${actual.nombre} (asignación actual)`, actual.id));
      select.appendChild(grupo);
    }
    select.value = actual?.id ?? '';
  }
  function responsables(select, usuarios, pilarId, actual = null) {
    select.replaceChildren(new Option('Seleccionar Responsable...', ''));
    select.disabled = false;
    const activos = usuarios.filter(u => u.activo);
    const sinPilar = activos.filter(u => !(u.pilares || []).length);
    function grupo(titulo, lista, incluirUsuario = false) {
      if (!lista.length) return;
      const elemento = document.createElement('optgroup');
      elemento.label = titulo;
      ordenar(lista, pilarId).forEach(u => elemento.appendChild(new Option(
        `${etiqueta(u, pilarId)}${incluirUsuario ? ` (@${u.username})` : ''}`, u.id)));
      select.appendChild(elemento);
    }
    if (!pilarId) {
      grupo('Personal sin Pilar Asignado', sinPilar, true);
      grupo('Colaboradores del Sistema', activos.filter(u => (u.pilares || []).length));
    } else {
      const miembros = activos.filter(u => pertenece(u, pilarId));
      grupo('Miembros del Pilar', miembros);
      if (!miembros.length) {
        const aviso = new Option('Este pilar aún no tiene miembros asignados', '');
        aviso.disabled = true;
        select.appendChild(aviso);
      }
      grupo('Personal sin Pilar Asignado', sinPilar);
    }
    conservarActual(select, actual);
  }
  function responsablesApoyo(select, usuarios, pilarId, actual = null) {
    const miembros = ordenar(usuarios.filter(u => u.activo && pertenece(u, pilarId)), pilarId);
    select.replaceChildren(new Option(pilarId && !miembros.length
      ? 'A nivel área (Sin miembros registrados)' : 'A nivel área (Sin responsable específico)', ''));
    select.disabled = !pilarId;
    if (pilarId) miembros.forEach(u => select.add(new Option(etiqueta(u, pilarId), u.id)));
    conservarActual(select, actual);
  }
  function pilares(select, lista, seleccionado, texto) {
    select.replaceChildren(new Option(texto, ''));
    lista.forEach(p => select.add(new Option(p.nombre, p.id)));
    select.value = seleccionado ?? '';
  }
  function filaApoyo(listaPilares, usuarios, apoyo = {}) {
    const fila = document.createElement('div');
    fila.className = 'row g-2 align-items-center p-2 bg-white rounded border mx-0';
    fila.innerHTML = `
      <div class="col-sm-5">
        <select name="apoyo_pilar_id[]" class="form-select form-select-sm select-apoyo-pilar" aria-label="Pilar de apoyo" required></select>
      </div>
      <div class="col-sm-6">
        <select name="apoyo_responsable_id[]" class="form-select form-select-sm select-apoyo-resp" aria-label="Responsable de apoyo"></select>
      </div>
      <div class="col-sm-1 text-end">
        <button type="button" class="btn btn-outline-danger btn-sm p-1" title="Quitar apoyo" aria-label="Quitar apoyo">
          <i class="fa-solid fa-trash-can fa-fw" aria-hidden="true"></i>
        </button>
      </div>`;
    const pilar = fila.querySelector('.select-apoyo-pilar');
    const responsable = fila.querySelector('.select-apoyo-resp');
    pilares(pilar, listaPilares, apoyo.pilar_id, 'Seleccionar Pilar de Apoyo...');
    responsablesApoyo(responsable, usuarios, apoyo.pilar_id,
      {id: apoyo.responsable_id, nombre: apoyo.responsable_nombre});
    pilar.addEventListener('change', () => responsablesApoyo(responsable, usuarios, pilar.value));
    fila.querySelector('button').addEventListener('click', () => fila.remove());
    return fila;
  }
  return {ordenar, responsables, responsablesApoyo, pilares, filaApoyo};
})();
