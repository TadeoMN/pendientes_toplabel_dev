// Los nombres accesibles y las leyendas táctiles no dependen de un tooltip.
(() => {
  const raton = window.matchMedia('(min-width: 768px) and (hover: hover) and (pointer: fine)');
  const iconos = [
    [/^(s[ií], )?cerrar sesi[oó]n/i, 'right-from-bracket'],
    [/^(crear|nuevo|nueva|asignar|agregar)/i, 'plus'],
    [/^(guardar|actualizar)/i, 'floppy-disk'],
    [/^cancelar/i, 'ban'], [/^cerrar/i, 'xmark'],
    [/^(eliminar|quitar|retirar)/i, 'trash-can'],
    [/^editar/i, 'pen-to-square'], [/^buscar/i, 'magnifying-glass'],
    [/^limpiar/i, 'eraser'], [/^(clave|cambiar contrase[ñn]a)/i, 'key'],
    [/^nota$/i, 'comment-medical'], [/^filtros$/i, 'filter'],
    [/^adjuntar/i, 'paperclip'], [/^ingresar/i, 'right-to-bracket']
  ];
  function preparar(root = document) {
    const botones = root.matches?.('.btn,.swal2-confirm,.swal2-cancel') ? [root] : root.querySelectorAll('.btn,.swal2-confirm,.swal2-cancel');
    botones.forEach(boton => {
      if (boton.dataset.accionLista || !boton.matches('button,a')) return;
      const copia = boton.cloneNode(true);
      copia.querySelectorAll('i,[aria-hidden="true"]').forEach(e => e.remove());
      const nombre = (boton.getAttribute('aria-label') || copia.textContent).trim().replace(/^\+\s*/, '');
      const accion = iconos.find(([patron]) => patron.test(nombre));
      if (!accion) return;
      boton.dataset.accionLista = 'true';
      boton.dataset.bsTitle = nombre;
      boton.setAttribute('aria-label', nombre);
      boton.classList.add('accion-icono');
      const icono = document.createElement('i');
      icono.className = `fa-solid fa-${accion[1]} fa-fw`;
      icono.setAttribute('aria-hidden', 'true');
      const leyenda = document.createElement('span');
      leyenda.className = 'accion-texto'; leyenda.textContent = nombre;
      boton.replaceChildren(icono, leyenda);
      actualizarTooltip(boton);
    });
  }
  function actualizarTooltip(boton) {
    if (raton.matches) bootstrap.Tooltip.getOrCreateInstance(boton, {trigger:'hover focus',container:'body'});
    else bootstrap.Tooltip.getInstance(boton)?.dispose();
  }
  raton.addEventListener('change', () => document.querySelectorAll('.accion-icono').forEach(actualizarTooltip));
  document.addEventListener('DOMContentLoaded', () => {
    preparar();
    new MutationObserver(cambios => cambios.forEach(cambio => cambio.addedNodes.forEach(nodo => {
      if (nodo.nodeType === 1) preparar(nodo);
    }))).observe(document.body, {childList:true,subtree:true});
    document.addEventListener('show.bs.modal', () => document.querySelectorAll('.accion-icono').forEach(b => bootstrap.Tooltip.getInstance(b)?.hide()));
  });
})();
