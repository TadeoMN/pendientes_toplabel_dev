// Interacciones comunes de las tablas de Dirección y Mis pendientes.
function iniciarArrastre(root = document) {
  root.querySelectorAll('[data-drag-scroll]').forEach(track => {
    if (track.dataset.dragListo) return;
    track.dataset.dragListo = 'true';
    let drag = null, bloquearClick = false;
    const actualizar = () => track.classList.toggle('puede-arrastrar', track.scrollWidth > track.clientWidth + 1);
    new ResizeObserver(actualizar).observe(track);
    actualizar();
    track.addEventListener('pointerdown', e => {
      bloquearClick = false;
      if (e.pointerType !== 'mouse' || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || track.scrollWidth <= track.clientWidth + 1) return;
      if (e.target.closest('select,input,textarea,[data-no-detalle],.tarea-nota')) return;
      drag = {id:e.pointerId, x:e.clientX, y:e.clientY, left:track.scrollLeft, moved:false};
    });
    track.addEventListener('pointermove', e => {
      if (!drag || e.pointerId !== drag.id) return;
      const dx = e.clientX-drag.x, dy = e.clientY-drag.y;
      if (!drag.moved) {
        if (Math.abs(dx) < 6) return;
        if (Math.abs(dy) > Math.abs(dx)) { drag=null; return; }
        drag.moved=true; track.setPointerCapture(e.pointerId); track.classList.add('is-dragging');
      }
      e.preventDefault(); track.scrollLeft=drag.left-dx;
    });
    function terminar(e) {
      if (!drag || drag.id !== e.pointerId) return;
      bloquearClick=drag.moved;
      if (track.hasPointerCapture(e.pointerId)) track.releasePointerCapture(e.pointerId);
      track.classList.remove('is-dragging'); drag=null;
    }
    track.addEventListener('pointerup',terminar);
    track.addEventListener('pointercancel',terminar);
    track.addEventListener('lostpointercapture',terminar);
    track.addEventListener('pointerleave',e=>{if(drag && !drag.moved) terminar(e);});
    track.addEventListener('dragstart',e=>e.preventDefault());
    track.addEventListener('click', e=>{
      if (!bloquearClick) return;
      bloquearClick=false; e.preventDefault(); e.stopImmediatePropagation();
    },true);
  });
}
function iniciarVistasTareas(root, elegida) {
  if (!root || root.dataset.vistasListas) return;
  root.dataset.vistasListas='true';
  initMotorTablasDinamicas(); initCambioEstatus(); iniciarArrastre(root);
  const direccion = root.dataset.ambito === 'direccion';
  const tabs = Array.from(root.querySelectorAll('[data-pestana]'));
  const panelActivo = () => root.querySelector('[role=tabpanel]:not([hidden])');
  const desplazarTabla = panel => panel.querySelector('.tareas-filtros').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  function sincronizar(panel) {
    const pilar = panel.querySelector('[data-filtro=pilar_id]');
    panel.querySelectorAll('[data-pilar-filtro]').forEach(button=>{
      const activo=button.dataset.pilarFiltro === pilar?.value;
      button.classList.toggle('active',activo); button.setAttribute('aria-pressed',String(activo));
    });
    if (pilar) {
      const alerta=panel.querySelector('.tareas-pilar-alert');
      const texto=pilar.selectedOptions[0]?.textContent || '';
      alerta.hidden=!texto.includes('vencidas/bloqueadas'); alerta.textContent=texto.includes('vencidas/bloqueadas') ? texto : '';
    }
    if (!direccion || panel.hidden) return;
    const semaforo=panel.querySelector('[data-filtro=semaforo]');
    document.querySelectorAll('.dashboard-kpi').forEach(button=>{
      button.setAttribute('aria-pressed',String(button.dataset.semaforo===semaforo.value));
      button.querySelector('[data-kpi-total]').textContent=Array.from(panel.querySelectorAll('tr[data-semaforo]')).filter(row=>row.dataset.semaforo===button.dataset.semaforo && (!pilar.value || row.dataset.pilar===pilar.value)).length;
    });
    const url=new URL(location.href);
    url.searchParams.set('vista',panel.id.replace('panel-',''));
    url.searchParams.delete('q');
    if (panel.querySelector('.tabla-buscador').value) url.searchParams.set('q',panel.querySelector('.tabla-buscador').value);
    panel.querySelectorAll('[data-filtro]').forEach(sel=>{url.searchParams.delete(sel.dataset.filtro);if(sel.value)url.searchParams.set(sel.dataset.filtro,sel.value);});
    history.replaceState(null,'',url);
  }
  function activar(clave, mover=false) {
    tabs.forEach(tab=>{
      const activo=tab.dataset.pestana===clave;
      tab.classList.toggle('active',activo);tab.setAttribute('aria-selected',String(activo));tab.tabIndex=activo?0:-1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden=!activo;
      if(activo) {
        if(mover) tab.scrollIntoView({inline:'nearest',block:'nearest'});
        else {
          const track=tab.parentElement, item=tab.getBoundingClientRect(), visible=track.getBoundingClientRect();
          if(item.left<visible.left) track.scrollLeft+=item.left-visible.left;
          else if(item.right>visible.right) track.scrollLeft+=item.right-visible.right;
        }
      }
    });
    sincronizar(panelActivo());
  }
  root.addEventListener('tabla:filtrada',e=>sincronizar(e.target));
  tabs.forEach((tab,i)=>{
    tab.addEventListener('click',()=>activar(tab.dataset.pestana,true));
    tab.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
      e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
      tabs[n].click();tabs[n].focus();
    });
  });
  root.querySelectorAll('[data-pilar-filtro]').forEach(button=>button.addEventListener('click',()=>{
    const panel=button.closest('[role=tabpanel]');const sel=panel.querySelector('[data-filtro=pilar_id]');sel.value=button.dataset.pilarFiltro;
    sel.dispatchEvent(new Event('change',{bubbles:true}));
  }));
  root.querySelectorAll('[data-filtro=pilar_id]').forEach(sel=>sel.addEventListener('change',()=>desplazarTabla(sel.closest('[role=tabpanel]'))));
  if(direccion) document.querySelectorAll('.dashboard-kpi').forEach(button=>button.addEventListener('click',()=>{
    const panel=panelActivo(),sel=panel.querySelector('[data-filtro=semaforo]');sel.value=sel.value===button.dataset.semaforo?'':button.dataset.semaforo;
    sel.dispatchEvent(new Event('change',{bubbles:true}));desplazarTabla(panel);
  }));
  const inicial=elegida||root.dataset.inicial;
  activar(tabs.some(t=>t.dataset.pestana===inicial)?inicial:tabs[0].dataset.pestana);
  if(direccion && location.hash==='#tablaFiltrada')desplazarTabla(panelActivo());
}
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.vistas-tareas').forEach(root=>iniciarVistasTareas(root));
  document.addEventListener('click',e=>{
    const row=e.target.closest('tr[data-tarea-detalle]');
    if(!row || e.defaultPrevented || e.target.closest('[data-no-detalle]'))return;
    const titulo=e.target.closest('[data-ver-tarea]');
    if(!titulo && e.target.closest('button,a,input,select,textarea,label'))return;
    if(window.getSelection()?.toString())return;
    verDetalleTarea(Number(row.dataset.tareaDetalle));
  });
});
