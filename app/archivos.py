import hashlib
import json
from pathlib import Path
import struct
from uuid import uuid4
import zipfile
from flask import current_app
from app import db
from app.modelos_acceso import Adjunto, ConfiguracionArchivos

MB = 1024 * 1024
LIMITES = {'imagenes': [10, 10], 'documentos': [10, 25], 'texto': [5, 5],
           'audio': [3, 25], 'video': [3, 100], 'total': [20, 500]}
TIPOS = {
    '.png': ('imagenes', 'image/png'), '.jpg': ('imagenes', 'image/jpeg'), '.jpeg': ('imagenes', 'image/jpeg'),
    '.webp': ('imagenes', 'image/webp'), '.pdf': ('documentos', 'application/pdf'),
    '.docx': ('documentos', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    '.xlsx': ('documentos', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '.txt': ('texto', 'text/plain'), '.csv': ('texto', 'text/csv'),
    '.mp3': ('audio', 'audio/mpeg'), '.mp4': ('video', 'video/mp4'), '.mov': ('video', 'video/quicktime'),
}


def limites():
    row = db.session.get(ConfiguracionArchivos, 1)
    return json.loads(row.valores) if row else {k: list(v) for k, v in LIMITES.items()}


def raiz():
    root = Path(current_app.config['UPLOAD_ROOT']).resolve()
    if root.is_relative_to(Path(current_app.root_path).parent.resolve()):
        raise ValueError('El almacenamiento de adjuntos debe estar fuera del proyecto.')
    return root


def ruta(clave):
    if len(clave) != 32 or any(c not in '0123456789abcdef' for c in clave):
        raise ValueError('Identificador de archivo inválido.')
    path = raiz() / clave
    if path.is_symlink() or path.resolve().parent != raiz():
        raise ValueError('Ruta de archivo inválida.')
    return path


def validar_contenido(path, extension):
    with path.open('rb') as stream:
        cabecera = stream.read(32)
        stream.seek(max(0, path.stat().st_size - 2048))
        final = stream.read()
    valido = False
    if extension == '.png':
        valido = cabecera.startswith(b'\x89PNG\r\n\x1a\n') and cabecera[12:16] == b'IHDR' and b'IEND' in final
    elif extension in ('.jpg', '.jpeg'):
        valido = cabecera.startswith(b'\xff\xd8\xff') and final.rstrip().endswith(b'\xff\xd9')
    elif extension == '.webp':
        valido = cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP'
    elif extension == '.pdf':
        valido = cabecera.startswith(b'%PDF-') and b'%%EOF' in final
    elif extension in ('.docx', '.xlsx'):
        try:
            with zipfile.ZipFile(path) as archivo:
                nombres = set(archivo.namelist())
                valido = '[Content_Types].xml' in nombres and ('word/document.xml' if extension == '.docx' else 'xl/workbook.xml') in nombres
                valido = valido and not any(i.flag_bits & 1 or 'vbaproject' in i.filename.lower() for i in archivo.infolist())
        except zipfile.BadZipFile:
            valido = False
    elif extension in ('.txt', '.csv'):
        try:
            texto = path.read_text(encoding='utf-8-sig')
            valido = '\x00' not in texto
        except UnicodeError:
            valido = False
    elif extension == '.mp3':
        valido = cabecera.startswith(b'ID3') or (len(cabecera) > 1 and cabecera[0] == 255 and cabecera[1] & 224 == 224)
    elif extension in ('.mp4', '.mov'):
        valido = len(cabecera) >= 12 and (cabecera[4:8] == b'ftyp' or
            (extension == '.mov' and cabecera[4:8] in (b'moov', b'mdat', b'wide')))
    if not valido:
        raise ValueError('El contenido de un archivo no coincide con el formato permitido.')


def guardar_archivos(files, usuario_id, *, tarea=None, nota=None, creados):
    if (tarea is None) == (nota is None):
        raise ValueError('Cada adjunto debe pertenecer a una tarea o a una nota.')
    elegidos = [f for f in files if f.filename]
    if not elegidos:
        return
    padre = tarea if tarea is not None else nota
    # El llamador mantiene un bloqueo de la tarea durante toda la carga.
    existentes = [a for a in padre.adjuntos if not a.retirado]
    reglas = limites()
    if len(existentes) + len(elegidos) > reglas['total'][0]:
        raise ValueError(f"Máximo {reglas['total'][0]} archivos por tarea o nota.")
    cantidad = {k: sum(a.categoria == k for a in existentes) for k in LIMITES if k != 'total'}
    total = sum(a.tamano for a in existentes)
    raiz().mkdir(parents=True, exist_ok=True)
    for file in elegidos:
        nombre = file.filename.replace('\\', '/').split('/')[-1]
        extension = Path(nombre).suffix.lower()
        if extension not in TIPOS or len(nombre) > 255 or any(ord(c) < 32 for c in nombre):
            raise ValueError('Nombre o formato de archivo no admitido.')
        categoria, mime = TIPOS[extension]
        cantidad[categoria] += 1
        if cantidad[categoria] > reglas[categoria][0]:
            raise ValueError(f'Se superó la cantidad permitida para {categoria}.')
        clave = uuid4().hex
        destino = ruta(clave)
        creados.append(destino)
        tamano = 0
        digest = hashlib.sha256()
        with destino.open('xb') as salida:
            while bloque := file.stream.read(MB):
                tamano += len(bloque)
                if tamano > reglas[categoria][1] * MB or total + tamano > reglas['total'][1] * MB:
                    raise ValueError('Se superó el tamaño permitido por archivo o por registro.')
                digest.update(bloque)
                salida.write(bloque)
        if not tamano:
            raise ValueError('No se admiten archivos vacíos.')
        validar_contenido(destino, extension)
        total += tamano
        db.session.add(Adjunto(tarea_id=tarea.id if tarea is not None else None, nota_id=nota.id if nota is not None else None,
            usuario_id=usuario_id, nombre=nombre, clave=clave, categoria=categoria, mime=mime,
            tamano=tamano, sha256=digest.hexdigest()))


def limpiar_archivos(creados):
    for path in creados:
        path.unlink(missing_ok=True)


def datos_adjunto(adjunto):
    return {'id': adjunto.id, 'nombre': adjunto.nombre, 'categoria': adjunto.categoria, 'tamano': adjunto.tamano,
            'url': f'/archivos/{adjunto.id}/descargar'}
