from flask_restful import Resource, reqparse
from flask import request, jsonify
from .. import db
from main.models.Usuario import Usuario as UsuarioModel
import datetime as dt
import requests
import json
from sqlalchemy.exc import OperationalError
import time

# Argument parser
usuario_parser = reqparse.RequestParser()
usuario_parser.add_argument('name', type=str, required=True, help='Name is required')
usuario_parser.add_argument('telephone', type=str, required=True, help='Telephone is required')
usuario_parser.add_argument('date', type=str, required=True, help='Date is required')
usuario_parser.add_argument('time', type=str, required=True, help='Time is required')

def retry(func):
    def wrapper(*args, **kwargs):
        retries = 3
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except OperationalError:
                db.session.rollback()
                time.sleep(2 ** attempt)  # Exponential backoff
        return jsonify({"error": "Database connection lost. Please try again later."}), 500
    return wrapper

class Usuario(Resource):
    @retry
    def get(self, id):
        usuario = db.session.query(UsuarioModel).get_or_404(id)
        return usuario.to_json()
    
    @retry
    def delete(self, id):
        usuario = db.session.query(UsuarioModel).get_or_404(id)
        db.session.delete(usuario)
        db.session.commit()
        return '', 204
    
    @retry
    def put(self, id):
        usuario = db.session.query(UsuarioModel).get_or_404(id)
        args = usuario_parser.parse_args()
        try:
            date = dt.datetime.fromisoformat(args['date'])
            time = dt.datetime.strptime(args['time'], "%H:%M:%S").time()
            usuario.name = args['name']
            usuario.telephone = args['telephone']
            usuario.date = date
            usuario.time = time
            usuario.dias_para_cita = (date.date() - usuario.fecha_registro.date()).days
            db.session.commit()
            return usuario.to_json(), 201
        except (ValueError, TypeError) as e:
            return {'error': str(e)}, 400

class Usuarios(Resource):
    @retry
    def get(self):
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        usuarios = UsuarioModel.query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'usuarios': [usuario.to_json() for usuario in usuarios.items],
            'total': usuarios.total,
            'pages': usuarios.pages,
            'page': page
        })
    
    @retry
    def post(self):
        args = usuario_parser.parse_args()
        try:
            usuario = UsuarioModel.from_json(args)
            db.session.add(usuario)
            db.session.commit()

            if usuario.dias_para_cita == 0:
                print(f"Enviando mensaje a {usuario.telephone}")
                send_whatsapp_message(usuario.telephone, f"Hola {usuario.name}, tu cita es mañana.")

            return usuario.to_json(), 201
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 400

def send_whatsapp_message(to_number, message_body):
    url = "https://api.gupshup.io/wa/api/v1/msg"

    payload = {
        "channel": "whatsapp",
        "source": 5216675014303,
        "destination": int(to_number),
        "message": json.dumps({"type": "text", "text": message_body}),
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
