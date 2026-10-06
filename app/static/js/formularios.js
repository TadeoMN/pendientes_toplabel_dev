(() => {
  const formulariosFetch = new Set(['formNotaDirecta', 'formAdjuntosTarea', 'formEditarTarea']);
  const envios = new Map();

  document.addEventListener('submit', evento => {
    const formulario = evento.target;
    if (!(formulario instanceof HTMLFormElement) || formulario.method.toLowerCase() !== 'post'
        || formulariosFetch.has(formulario.id) || evento.defaultPrevented) return;
    if (envios.has(formulario)) {
      evento.preventDefault();
      return;
    }
    if (!formulario.checkValidity()) return;

    const envio = {originales: [], ocupado: formulario.getAttribute('aria-busy')};
    envios.set(formulario, envio);
    // La siguiente tarea espera a todos los listeners y al envío nativo.
    // Una microtarea puede ejecutarse antes de la acción predeterminada del navegador.
    window.setTimeout(() => {
      if (envios.get(formulario) !== envio) return;
      if (evento.defaultPrevented) {
        envios.delete(formulario);
        return;
      }
      const botones = Array.from(formulario.elements).filter(campo => campo.type === 'submit');
      if (evento.submitter && !botones.includes(evento.submitter)) botones.push(evento.submitter);
      const originales = botones.map(boton => ({
        boton, desactivado: boton.disabled,
        nodos: Array.from(boton.childNodes), valor: boton.value
      }));
      envio.originales = originales;
      formulario.setAttribute('aria-busy', 'true');
      originales.forEach(({boton}) => {
        boton.disabled = true;
        if (boton instanceof HTMLInputElement) {
          boton.value = 'Guardando…';
        } else {
          const spinner = document.createElement('span');
          spinner.className = 'spinner-border spinner-border-sm me-2';
          spinner.setAttribute('aria-hidden', 'true');
          boton.replaceChildren(spinner, document.createTextNode('Guardando…'));
        }
      });
    });
  });

  // El navegador puede recuperar la página anterior desde su caché de navegación.
  window.addEventListener('pageshow', () => {
    envios.forEach(({originales, ocupado}, formulario) => {
      originales.forEach(({boton, desactivado, nodos, valor}) => {
        boton.disabled = desactivado;
        if (boton instanceof HTMLInputElement) boton.value = valor;
        else boton.replaceChildren(...nodos);
      });
      if (ocupado === null) formulario.removeAttribute('aria-busy');
      else formulario.setAttribute('aria-busy', ocupado);
    });
    envios.clear();
  });
})();
