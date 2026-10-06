(() => {
  const token = document.querySelector('meta[name=csrf-token]').content;
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
      if (form.method.toLowerCase() !== 'post') return;
      const campo = document.createElement('input');
      campo.type = 'hidden'; campo.name = 'csrf_token'; campo.value = token;
      form.appendChild(campo);
    });
  });
  const original = window.fetch.bind(window);
  window.fetch = (url, opciones = {}) => {
    const destino = new URL(url instanceof Request ? url.url : url, location.href);
    const metodo = (opciones.method || (url instanceof Request ? url.method : 'GET')).toUpperCase();
    if (destino.origin === location.origin && !['GET','HEAD','OPTIONS'].includes(metodo)) {
      const headers = new Headers(opciones.headers || (url instanceof Request ? url.headers : undefined));
      headers.set('X-CSRF-Token', token);
      opciones = {...opciones, headers};
    }
    return original(url, opciones);
  };
})();
