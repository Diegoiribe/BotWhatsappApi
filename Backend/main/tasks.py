import requests
import json
from datetime import datetime
from flask import current_app
from main import db
from main.models.Usuario import Usuario as UsuarioModel  # Importación correcta del modelo

def update_dias_para_cita():
    with current_app.app_context():
        usuarios = UsuarioModel.query.all()
        for usuario in usuarios:
            dias_para_cita = (usuario.date.date() - datetime.utcnow().date()).days  # Usa el atributo 'date'
            usuario.dias_para_cita = dias_para_cita
            if dias_para_cita == 0:
                send_whatsapp_message(
                    usuario.telephone,  # Asegúrate de usar 'telephone' en lugar de 'telefono'
                    f"Hola {usuario.name}, tu cita es mañana."  # Asegúrate de usar 'name' en lugar de 'nombre'
                )
        db.session.commit()

def send_whatsapp_message(to_number, message_body):
    url = "https://api.gupshup.io/wa/api/v1/msg"

    payload = {
        "channel": "whatsapp",
        "source": 5216675014303,
        "destination": int(to_number),
        "message": json.dumps({
            "type": "text",
            "text": message_body
        }),
        "src.name": "myapp",
        "disablePreview": False,
        "encode": False
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": "o6botgtule9omsamb70z42udlyzp3cql"
    }

    response = requests.post(url, data=payload, headers=headers)

    print(response.text)
