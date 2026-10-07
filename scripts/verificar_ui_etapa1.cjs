// Sin dependencias: node scripts/verificar_ui_etapa1.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const raiz = path.resolve(__dirname, '..');

class Elemento {
  constructor(tag = 'div') {
    this.tag = tag;
    this.childNodes = [];
    this.atributos = new Map();
    this.disabled = false;
    this.value = '';
  }
  append(...nodos) { this.childNodes.push(...nodos); }
  appendChild(nodo) { this.append(nodo); return nodo; }
  replaceChildren(...nodos) { this.childNodes = nodos; }
  setAttribute(nombre, valor) { this.atributos.set(nombre, valor); }
  getAttribute(nombre) { return this.atributos.get(nombre) ?? null; }
  removeAttribute(nombre) { this.atributos.delete(nombre); }
  set textContent(valor) { this.replaceChildren(String(valor)); }
  get textContent() { return this.childNodes.map(n => typeof n === 'string' ? n : n.textContent).join(''); }
  set innerHTML(valor) {
    assert.ok(!valor.includes('<img'), 'Un dato del servidor se insertó como HTML');
    this.htmlFijo = valor;
    this.replaceChildren();
  }
}
class Formulario extends Elemento {
  constructor(id = '', method = 'post', valido = true) {
    super('form'); this.id = id; this.method = method; this.valido = valido;
    this.elements = [new Elemento('button')];
    this.elements[0].type = 'submit';
    this.elements[0].append('Guardar y asignar tarea');
  }
  checkValidity() { return this.valido; }
}
class Campo extends Elemento {}
const manejadores = {};
const pendientes = [];
const completarEvento = () => { while (pendientes.length) pendientes.shift()(); };
const contexto = {
  HTMLFormElement: Formulario, HTMLInputElement: Campo,
  document: {
    addEventListener: (tipo, fn) => { manejadores[tipo] = fn; },
    createElement: tag => new Elemento(tag), createTextNode: texto => texto,
  },
  window: {
    addEventListener: (tipo, fn) => { manejadores[tipo] = fn; },
    setTimeout: fn => pendientes.push(fn),
  },
};
vm.runInNewContext(fs.readFileSync(path.join(raiz, 'app/static/js/formularios.js'), 'utf8'), contexto);
const enviar = formulario => {
  const evento = {target: formulario, submitter: formulario.elements[0], defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; }};
  manejadores.submit(evento);
  return evento;
};

(async () => {
  const form = new Formulario();
  form.elements[0].name = 'accion'; form.elements[0].value = 'crear';
  const primero = enviar(form);
  assert.equal(form.elements[0].disabled, false, 'Conservar datos durante el envío nativo');
  assert.equal(enviar(form).defaultPrevented, true, 'Bloquear también reenvíos antes del timer');
  completarEvento();
  assert.equal(primero.defaultPrevented, false);
  assert.equal(form.elements[0].disabled, true);
  assert.equal(form.elements[0].textContent, 'Guardando…');
  assert.equal(form.elements[0].value, 'crear');
  assert.equal(form.elements[0].childNodes[0].getAttribute('aria-hidden'), 'true');
  assert.equal(form.getAttribute('aria-busy'), 'true');
  assert.equal(enviar(form).defaultPrevented, true, 'Bloquear segundo envío');
  manejadores.pageshow();
  assert.equal(form.elements[0].disabled, false);
  assert.equal(form.elements[0].textContent, 'Guardar y asignar tarea');
  assert.equal(form.getAttribute('aria-busy'), null);

  for (const ignorado of [new Formulario('', 'get'), new Formulario('', 'post', false),
    ...['formNotaDirecta', 'formAdjuntosTarea', 'formEditarTarea'].map(id => new Formulario(id))]) {
    enviar(ignorado); completarEvento();
    assert.equal(ignorado.elements[0].disabled, false);
    assert.equal(ignorado.getAttribute('aria-busy'), null);
  }
  const propio = new Formulario();
  const cancelado = enviar(propio);
  cancelado.preventDefault(); // Otro listener ejecutado después del listener global.
  completarEvento();
  assert.equal(propio.elements[0].disabled, false);
  const implicit = new Formulario();
  const alternativo = new Campo('input'); alternativo.type = 'submit'; alternativo.value = 'Guardar';
  implicit.elements.push(alternativo);
  enviar(implicit); completarEvento();
  assert.ok(implicit.elements.every(b => b.disabled));
  manejadores.pageshow();
  assert.equal(alternativo.value, 'Guardar');
  console.log('N1: doble envío, validación, GET, fetch, preventDefault, botones implícitos y restauración: OK');

  const carga = '<img src=x onerror=alert(1)>';
  const nodos = Object.fromEntries(['miembros_pilar_titulo', 'miembros_color_dot', 'lista_miembros_contenedor',
    'modalVerMiembros'].map(id => [id, new Elemento()]));
  nodos.miembros_color_dot.style = {};
  const datos = {pilar: carga, color: '#0284c7', miembros: [{nombre_completo: carga,
    username: carga, email: carga, es_responsable: true}]};
  const plantilla = fs.readFileSync(path.join(raiz, 'app/templates/admin/pilares.html'), 'utf8');
  const script = plantilla.match(/<script>([\s\S]*?)<\/script>/)[1];
  let mostrado = false;
  const seguro = {
    document: {getElementById: id => nodos[id], createElement: tag => new Elemento(tag)},
    fetch: async () => ({ok: true, json: async () => datos}),
    bootstrap: {Modal: class {show() { mostrado = true; }}},
    Swal: {fire() { assert.fail('No debe fallar el renderizado de miembros'); }},
  };
  vm.runInNewContext(script, seguro);
  await seguro.verMiembrosPilar(1);
  assert.ok(mostrado);
  assert.equal(nodos.miembros_pilar_titulo.textContent, `Miembros: ${carga}`);
  const lista = nodos.lista_miembros_contenedor;
  assert.equal(lista.childNodes.length, 1);
  assert.ok(lista.textContent.includes(carga));
  datos.miembros = [
    {nombre_completo:'Zoé',username:'zoe',email:'',es_responsable:false},
    {nombre_completo:'Zeta',username:'zeta',email:'',es_responsable:true},
    {nombre_completo:'Ángel',username:'angel',email:'',es_responsable:false},
    {nombre_completo:'María',username:'maria',email:'',es_responsable:true}
  ];
  await seguro.verMiembrosPilar(1);
  assert.deepEqual(lista.childNodes.map(n => n.textContent.match(/María|Zeta|Ángel|Zoé/)[0]),
    ['María','Zeta','Ángel','Zoé'], 'Líderes primero y nombres alfabéticos en español');
  assert.equal(datos.miembros[0].nombre_completo, 'Zoé', 'No modificar los datos recibidos');
  console.log('C6: líderes primero; orden alfabético con acentos; datos originales conservados: OK');
  datos.miembros = [];
  await seguro.verMiembrosPilar(1);
  assert.ok(lista.htmlFijo.includes('No hay colaboradores'));
  console.log('B1: nombre, usuario, correo y título con payload XSS; lista vacía: OK');
})().catch(error => {console.error(error); process.exitCode = 1;});
