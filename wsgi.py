from app import create_app

app = create_app()

if __name__ == '__main__':
    # Configurado en puerto 5005 para evitar colisiones
    print("Iniciando Top Label Pendientes en http://192.168.100.24:5010 ...")
    app.run(host='0.0.0.0', port=5010, debug=True)
