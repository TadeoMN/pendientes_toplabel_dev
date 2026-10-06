"""Validación y auditoría de la edición completa, sin cambiar el esquema de BD."""
from datetime import date, datetime
from hashlib import sha256
import json

from app import db
from app.models import Pilar, Usuario, TareaDependencia, BitacoraTarea

ETIQUETAS = {
    'titulo': 'Título', 'descripcion': 'Descripción', 'pilar_id': 'Pilar',
    'responsable_id': 'Responsable', 'prioridad': 'Prioridad', 'estatus': 'Estatus',
    'fecha_inicio': 'Fecha de inicio', 'fecha_compromiso': 'Fecha límite',
    'fecha_cierre': 'Fecha de cierre', 'fuente': 'Origen',
}
ESTATUS = {'PENDIENTE', 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO'}
FUENTES = {'DIRECCION', 'INICIATIVA_PROPIA', 'REUNION_AUDIO_IA'}


def version_tarea(tarea):
    estado = tarea.to_dict()
    estado.pop('semaforo')  # El paso del tiempo no es una edición.
    estado['updated_at'] = tarea.updated_at.isoformat() if tarea.updated_at else None
    return sha256(json.dumps(estado, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def opciones_edicion():
    return {
        'pilares': [{'id': p.id, 'nombre': p.nombre} for p in Pilar.query.order_by(Pilar.nombre).all()],
        'usuarios': [{'id': u.id, 'nombre_completo': u.nombre_completo,
                      'username': u.username, 'activo': u.activo, 'pilares': u.pilares_info()}
                     for u in Usuario.query.filter_by(activo=True).order_by(Usuario.nombre_completo).all()],
    }


def aplicar_edicion(tarea, datos, actor_id):
    """Valida todo antes de mutar. El llamador confirma tarea y auditoría juntas."""
    from app.routes.tareas import PRIORIDADES

    if set(datos) - {'nota_estatus'} != set(ETIQUETAS) | {'version', 'apoyos'}:
        raise ValueError('Envía todos los campos editables. El código, la creación y la autoría no se pueden modificar.')
    nuevos = {}
    for campo in ('titulo', 'descripcion', 'prioridad', 'estatus', 'fuente'):
        valor = datos[campo]
        if not isinstance(valor, str):
            raise ValueError(f'{ETIQUETAS[campo]} inválido.')
        nuevos[campo] = valor.strip()
    if not nuevos['titulo'] or len(nuevos['titulo']) > 200:
        raise ValueError('El título es obligatorio y admite hasta 200 caracteres.')
    if nuevos['prioridad'] not in PRIORIDADES or nuevos['estatus'] not in ESTATUS:
        raise ValueError('Prioridad o estatus inválido.')
    if nuevos['fuente'] not in FUENTES and nuevos['fuente'] != tarea.fuente:
        raise ValueError('Origen inválido.')

    for campo in ('fecha_inicio', 'fecha_compromiso', 'fecha_cierre'):
        valor = datos[campo]
        if campo == 'fecha_cierre' and valor in (None, ''):
            nuevos[campo] = None
            continue
        try:
            nuevos[campo] = date.fromisoformat(valor)
        except (ValueError, TypeError):
            raise ValueError(f'{ETIQUETAS[campo]} inválida.') from None
    if nuevos['fecha_compromiso'] < nuevos['fecha_inicio']:
        raise ValueError('La fecha límite no puede ser anterior al inicio.')
    if nuevos['estatus'] == 'COMPLETADO':
        nuevos['fecha_cierre'] = nuevos['fecha_cierre'] or date.today()
        if nuevos['fecha_cierre'] < nuevos['fecha_inicio'] or nuevos['fecha_cierre'] > date.today():
            raise ValueError('La fecha de cierre debe estar entre el inicio y hoy.')
    elif nuevos['fecha_cierre'] is not None:
        raise ValueError('Solo una tarea completada puede tener fecha de cierre.')

    def identificador(valor, obligatorio=False):
        if valor is None and not obligatorio:
            return None
        if type(valor) is not int or valor <= 0:
            raise ValueError('Pilar o responsable inválido.')
        return valor

    def asignacion(p_id, r_id, anteriores, permitir_sin_pilar=False):
        if p_id is not None and db.session.get(Pilar, p_id) is None:
            raise ValueError('El pilar seleccionado no existe.')
        if r_id is not None:
            usuario = db.session.get(Usuario, r_id)
            if usuario is None:
                raise ValueError('El responsable no existe.')
            # Conservar asignaciones históricas al editar otros datos, sin permitir
            # nuevas asignaciones a usuarios inactivos o ajenos al pilar.
            if (p_id, r_id) not in anteriores:
                if not usuario.activo:
                    raise ValueError('El responsable está inactivo.')
                membresias = {p['id'] for p in usuario.pilares_info()}
                if p_id is not None and p_id not in membresias and not (permitir_sin_pilar and not membresias):
                    raise ValueError('El responsable debe pertenecer al pilar seleccionado.')

    nuevos['pilar_id'] = identificador(datos['pilar_id'])
    nuevos['responsable_id'] = identificador(datos['responsable_id'], obligatorio=True)
    asignacion(nuevos['pilar_id'], nuevos['responsable_id'], {(tarea.pilar_id, tarea.responsable_id)}, permitir_sin_pilar=True)
    anteriores = {(d['pilar_id'], d['responsable_id']) for d in tarea.dependencias_info()}
    if not isinstance(datos['apoyos'], list):
        raise ValueError('La lista de apoyos es inválida.')
    apoyos = set()
    for apoyo in datos['apoyos']:
        if not isinstance(apoyo, dict) or set(apoyo) != {'pilar_id', 'responsable_id'}:
            raise ValueError('Un apoyo es inválido.')
        p_id = identificador(apoyo['pilar_id'], obligatorio=True)
        r_id = identificador(apoyo['responsable_id'])
        asignacion(p_id, r_id, anteriores)
        apoyos.add((p_id, r_id))

    def mostrar(campo, valor):
        if valor is None or valor == '':
            return 'Sin asignar'
        if campo == 'pilar_id':
            return db.session.get(Pilar, valor).nombre
        if campo == 'responsable_id':
            return db.session.get(Usuario, valor).nombre_completo
        if isinstance(valor, date):
            return valor.strftime('%d/%m/%Y')
        return str(valor)

    cambios = []
    for campo, valor in nuevos.items():
        anterior = getattr(tarea, campo)
        if (anterior or '') != (valor or ''):
            cambios.append(f'{ETIQUETAS[campo]}: «{mostrar(campo, anterior)}» → «{mostrar(campo, valor)}».')
    if apoyos != anteriores:
        def resumen(valores):
            return '; '.join(f'{mostrar("pilar_id", p)} / {mostrar("responsable_id", r) if r else "Área general"}'
                             for p, r in sorted(valores, key=lambda par: (par[0], par[1] or 0))) or 'Sin apoyos'
        cambios.append(f'Pilares de apoyo: «{resumen(anteriores)}» → «{resumen(apoyos)}».')
    if not cambios:
        return False
    from app.notas import validar_transicion, registrar_contexto
    anterior_estatus = tarea.estatus
    motivo = validar_transicion(tarea, nuevos['estatus'], datos.get('nota_estatus', ''))
    for campo, valor in nuevos.items():
        setattr(tarea, campo, valor)
    if apoyos != anteriores:
        tarea.dependencias[:] = [TareaDependencia(pilar_id=p, responsable_id=r) for p, r in sorted(apoyos, key=lambda par: (par[0], par[1] or 0))]
        tarea.pilar_dependencia_id = None  # Evita reactivar el apoyo histórico al quitar el último.
    tarea.updated_at = datetime.utcnow()
    # AVANCE ya existe en los ENUM de producción. El prefijo distingue la
    # auditoría de edición sin exigir una migración para ampliar ese ENUM.
    nota = BitacoraTarea(tarea_id=tarea.id, usuario_id=actor_id, tipo='AVANCE',
                         comentario='Modificación de tarea:\n' + '\n'.join(cambios) + ('\nMotivo: ' + motivo if motivo else ''))
    registrar_contexto(nota, anterior_estatus, tarea.estatus, 'EDICION')
    db.session.add(nota)
    return True
