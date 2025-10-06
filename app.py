# app.py
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
import base64
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

app = Flask(__name__)

# Alcance de la API (permite enviar correos)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    creds = None
    if os.path.exists('confidencial/token.pickle'):
        with open('confidencial/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'confidencial/credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open('confidencial/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw_message.decode()}

def create_message_html(sender, to, subject, html_content):
    """📨 Crea un mensaje HTML válido para Gmail API"""
    message = MIMEText(html_content, "html")
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw_message.decode()}


def send_message(service, user_id, message):
    return service.users().messages().send(userId=user_id, body=message).execute()


@app.route("/api/v1/send-email", methods=["POST"])
def send_email():
    try:
        data = request.get_json()
        to = data.get("to")
        subject = data.get("subject")
        message_text = data.get("message")

        if not to or not subject or not message_text:
            return jsonify({"error": "Faltan campos: 'to', 'subject', 'message'"}), 400

        creds = authenticate_gmail()
        service = build('gmail', 'v1', credentials=creds)

        mensaje = create_message(
            sender="me",  # Gmail entiende "me" como la cuenta autenticada
            to=to,
            subject=subject,
            message_text=message_text
        )

        sent_message = send_message(service, 'me', mensaje)

        return jsonify({
            "status": "success",
            "message_id": sent_message["id"],
            "to": to,
            "subject": subject
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500
    
    
    
@app.route("/api/v1/login-notification", methods=["POST"])
def send_login_notification():
    try:
        data = request.get_json()
        to = data.get("to")
        name = data.get("name")
        ip = data.get("ip", "Desconocida")
        browser = data.get("browser", "Desconocido")

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
              <h2 style="color: #222;">Hola, {name} 👋</h2>
              <p>Hemos detectado un nuevo inicio de sesión en tu cuenta.</p>
              <p>Si fuiste tú, no necesitas hacer nada más.</p>
              <p>Si <b>no reconoces este inicio de sesión</b>, te recomendamos cambiar tu contraseña inmediatamente.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
              <p style="font-size: 0.95em; color: #555;">
                📅 <b>Fecha:</b> Ahora mismo<br>
                🌐 <b>IP:</b> {ip}<br>
                🧭 <b>Navegador:</b> {browser}
              </p>
              <p style="font-size: 0.9em; color: #888; margin-top: 20px;">
                — Equipo de Seguridad | <b>Travel Agency</b>
              </p>
            </div>
          </body>
        </html>
        """

        creds = authenticate_gmail()
        service = build('gmail', 'v1', credentials=creds)

        message = create_message_html(
            sender="me",
            to=to,
            subject="🔔 Nuevo inicio de sesión detectado",
            html_content=html_content
        )

        sent_message = send_message(service, 'me', message)

        return jsonify({
            "status": "success",
            "message_id": sent_message["id"],
            "to": to
        }), 200

    except Exception as e:
        print("Error enviando correo:", e)
        return jsonify({"status": "error", "details": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)