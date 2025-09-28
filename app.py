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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
