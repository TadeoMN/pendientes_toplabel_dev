document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-logout-url]').forEach(button => {
    button.addEventListener('click', async () => {
      const menu = document.getElementById('navbarContent');
      const menuWasOpen = menu?.classList.contains('show');
      if (menuWasOpen) {
        // Cerrar primero el panel para liberar su control del foco.
        await new Promise(resolve => {
          menu.addEventListener('hidden.bs.offcanvas', resolve, { once: true });
          bootstrap.Offcanvas.getOrCreateInstance(menu).hide();
        });
      }
      const result = await Swal.fire({
        title: '¿Cerrar sesión?',
        text: '¿Estás seguro de que quieres cerrar tu sesión?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, cerrar sesión',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#0284c7',
        focusCancel: true,
        returnFocus: !menuWasOpen
      });
      if (result.isConfirmed) {
        window.location.assign(button.dataset.logoutUrl);
      } else if (menuWasOpen) {
        menu.addEventListener('shown.bs.offcanvas', () => button.focus(), { once: true });
        bootstrap.Offcanvas.getOrCreateInstance(menu).show();
      }
    });
  });
});
