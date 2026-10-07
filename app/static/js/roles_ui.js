(() => {
  const formulario = document.querySelector('.permisos-formulario');
  if (!formulario) return;
  const grupos = Array.from(formulario.querySelectorAll('.permisos-grupo'));
  const buscador = document.getElementById('buscar-permisos');
  const normalizar = texto => texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
  let abiertos;
  function contar() {
    let total = 0;
    grupos.forEach(grupo => {
      const cantidad = grupo.querySelectorAll('input[name="permisos"]:checked').length;
      total += cantidad;
      grupo.querySelector('.permisos-cantidad').textContent = `${cantidad} ${cantidad === 1 ? "seleccionado" : "seleccionados"}`;
    });
    document.getElementById('permisos-total').textContent = `${total} casillas de permisos seleccionadas`;
  }
  buscador.addEventListener('input', () => {
    const consulta = normalizar(buscador.value.trim());
    if (consulta && !abiertos) abiertos = grupos.map(grupo => grupo.open);
    let visibles = 0;
    grupos.forEach((grupo, indice) => {
      const filas = Array.from(grupo.querySelectorAll('.permiso-fila'));
      filas.forEach(fila => { fila.hidden = !normalizar(fila.dataset.busqueda).includes(consulta); });
      grupo.hidden = filas.every(fila => fila.hidden);
      if (!grupo.hidden) visibles++;
      if (consulta) grupo.open = !grupo.hidden;
      else if (abiertos) grupo.open = abiertos[indice];
    });
    if (!consulta) abiertos = undefined;
    document.getElementById('permisos-sin-resultados').hidden = visibles > 0;
  });
  formulario.addEventListener('change', contar);
  contar();
})();
