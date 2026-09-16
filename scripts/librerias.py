import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSS_DIR = os.path.join(BASE_DIR, "app", "static", "css")
JS_DIR = os.path.join(BASE_DIR, "app", "static", "js")

os.makedirs(CSS_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

ARCHIVOS = {
    # Bootstrap 5.3 (CSS y JS Bundle con Popper incluido)
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css": os.path.join(CSS_DIR, "bootstrap.min.css"),
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js": os.path.join(JS_DIR, "bootstrap.bundle.min.js"),
    
    # SweetAlert2 v11 (CSS y JS)
    "https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css": os.path.join(CSS_DIR, "sweetalert2.min.css"),
    "https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js": os.path.join(JS_DIR, "sweetalert2.all.min.js"),
}

print("Iniciando descarga de librerías para uso LOCAL...")
headers = {'User-Agent': 'Mozilla/5.0'}

for url, destino in ARCHIVOS.items():
    nombre = os.path.basename(destino)
    print(f"Descargando {nombre}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(destino, 'wb') as f:
            f.write(resp.read())
        print(f"✅ {nombre} guardado correctamente ({os.path.getsize(destino)} bytes).")
    except Exception as e:
        print(f"❌ Error descargando {nombre}: {e}")

print("\n¡Librerías instaladas localmente en app/static!")