document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modalDetalleTarea')?.addEventListener('hidden.bs.modal', () => {
    document.getElementById('formAdjuntosTarea')?.reset();
    document.getElementById('formNotaDirecta')?.reset();
  });
  document.querySelectorAll('.selector-archivos').forEach(contenedor => {
    const input = contenedor.querySelector('input[type=file]');
    const lista = contenedor.querySelector('ul');
    let archivos = [];
    function mostrar() {
      const transferencia = new DataTransfer();
      lista.replaceChildren();
      archivos.forEach((archivo, indice) => {
        transferencia.items.add(archivo);
        const fila = document.createElement('li');
        fila.className = 'list-group-item d-flex justify-content-between gap-2 align-items-center';
        const texto = document.createElement('span');
        texto.className = 'small text-break';
        texto.textContent = `${archivo.name} · ${(archivo.size / 1048576).toFixed(2)} MB`;
        const quitar = document.createElement('button');
        quitar.type = 'button'; quitar.className = 'btn btn-outline-danger btn-sm'; quitar.textContent = 'Quitar';
        quitar.onclick = () => { archivos.splice(indice, 1); mostrar(); };
        fila.append(texto, quitar); lista.appendChild(fila);
      });
      input.files = transferencia.files;
    }
    input.addEventListener('change', () => {
      for (const archivo of input.files) {
        if (!archivos.some(a => a.name === archivo.name && a.size === archivo.size && a.lastModified === archivo.lastModified)) archivos.push(archivo);
      }
      mostrar();
    });
    input.form?.addEventListener('reset', () => { archivos = []; mostrar(); });
  });
  document.getElementById('formAdjuntosTarea')?.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const boton = form.querySelector('button[type=submit]');
    boton.disabled = true;
    try {
      const res = await fetch(`/archivos/tarea/${document.getElementById('modal_nota_tarea_id').value}`, {
        method: 'POST', headers: {'X-Requested-With': 'XMLHttpRequest'}, body: new FormData(form)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'No se pudieron adjuntar los archivos.');
      form.reset();
      await verDetalleTarea(document.getElementById('modal_nota_tarea_id').value);
    } catch (error) { Swal.fire({icon: 'error', text: error.message}); }
    finally { boton.disabled = false; }
  });
});

function mostrarAdjuntos(contenedor, adjuntos, permisos) {
  contenedor.replaceChildren();
  if (!adjuntos.length) { contenedor.textContent = 'Sin archivos adjuntos.'; return; }
  adjuntos.forEach(a => {
    const fila = document.createElement('div');
    fila.className = 'd-flex flex-wrap align-items-center gap-2 border rounded p-2 mb-2';
    const nombre = document.createElement(permisos.puede_descargar ? 'a' : 'span');
    nombre.textContent = `${a.nombre} · ${(a.tamano / 1048576).toFixed(2)} MB`;
    nombre.className = 'text-break small';
    if (permisos.puede_descargar) { nombre.href = a.url; nombre.download = a.nombre; }
    fila.appendChild(nombre);
    if (permisos.puede_retirar) {
      const boton = document.createElement('button');
      boton.type = 'button'; boton.className = 'btn btn-outline-danger btn-sm ms-auto'; boton.textContent = 'Retirar';
      boton.onclick = async () => {
        const ok = await Swal.fire({title:'¿Retirar este archivo?', text:a.nombre, showCancelButton:true, confirmButtonText:'Retirar', cancelButtonText:'Cancelar'});
        if (!ok.isConfirmed) return;
        boton.disabled = true;
        try {
          const respuesta = await fetch(`/archivos/${a.id}/retirar`, {method:'POST', headers:{'X-Requested-With':'XMLHttpRequest'}});
          if (!respuesta.ok) throw new Error('No se pudo retirar el archivo.');
          await verDetalleTarea(document.getElementById('modal_nota_tarea_id').value);
        } catch(error) { boton.disabled=false; Swal.fire({icon:'error',text:error.message}); }
      };
      fila.appendChild(boton);
    }
    contenedor.appendChild(fila);
  });
}
