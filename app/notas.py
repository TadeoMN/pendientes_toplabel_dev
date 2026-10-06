"""Reglas compartidas de notas y transiciones. El llamador confirma la transacción."""
from datetime import date
from app import db
from app.models import BitacoraTarea
from app.modelos_acceso import TransicionNota
from app.permisos import exigir

TIPOS_NOTA = {'AVANCE', 'PROBLEMA', 'BLOQUEO', 'ACUERDO', 'OBSERVACION'}
ESTATUS = {'PENDIENTE', 'EN_PROCESO', 'BLOQUEADO', 'COMPLETADO'}


def validar_transicion(tarea, nuevo, comentario):
    if not isinstance(nuevo, str) or nuevo not in ESTATUS:
        raise ValueError('Estatus inválido.')
    if not isinstance(comentario, str):
        raise ValueError('El comentario debe ser texto.')
    comentario = comentario.strip()
    if tarea.estatus == nuevo:
        return comentario
    exigir('tareas.estatus', tarea)
    if tarea.estatus == 'COMPLETADO' and nuevo != 'EN_PROCESO':
        raise ValueError('Para reabrir una tarea completada selecciona En proceso y explica el motivo.')
    if (nuevo in {'BLOQUEADO', 'COMPLETADO'} or tarea.estatus in {'BLOQUEADO', 'COMPLETADO'}) and not comentario:
        raise ValueError('Es obligatorio explicar el bloqueo, cierre, desbloqueo o reapertura.')
    if nuevo == 'COMPLETADO' and tarea.fecha_inicio > date.today():
        raise ValueError('No puedes completar una tarea antes de su fecha de inicio.')
    return comentario


def registrar_contexto(nota, anterior, nuevo, origen):
    nota.transicion = TransicionNota(estatus_anterior=anterior, estatus_nuevo=nuevo, origen=origen)


def registrar_nota(tarea, actor_id, tipo, comentario, nuevo=None, origen='NOTA'):
    if not isinstance(comentario, str):
        raise ValueError('Comentario inválido.')
    comentario = comentario.strip()
    if origen == 'NOTA':
        if not isinstance(tipo, str) or tipo not in TIPOS_NOTA:
            raise ValueError('Tipo de nota inválido.')
        if not comentario:
            raise ValueError('El comentario no puede estar vacío.')
        if nuevo and tipo != 'BLOQUEO':
            raise ValueError('Solo una nota de bloqueo permite cambiar también a Bloqueado.')
        if nuevo and nuevo != 'BLOQUEADO':
            raise ValueError('Una nota de bloqueo solo puede cambiar a Bloqueado.')
    anterior = tarea.estatus
    destino = nuevo or anterior
    comentario = validar_transicion(tarea, destino, comentario)
    if origen == 'ESTATUS' and anterior == destino:
        raise ValueError('La tarea ya tiene ese estatus.')
    if destino != anterior:
        tarea.estatus = destino
        tarea.fecha_cierre = date.today() if destino == 'COMPLETADO' else None
    nota = BitacoraTarea(tarea_id=tarea.id, usuario_id=actor_id,
                        tipo=tipo if origen == 'NOTA' else ('BLOQUEO' if destino == 'BLOQUEADO' else 'CAMBIO_ESTATUS'),
                        comentario=comentario or f'Cambio de estatus: {anterior} → {destino}.')
    registrar_contexto(nota, anterior, destino, origen)
    db.session.add(nota)
    return nota
