"""
Notificador WhatsApp vía Twilio.
Reemplaza el servicio Node.js anterior (WhatsApp Web) por la API de Twilio.
"""

import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    def __init__(self, config: dict):
        self.client = Client(config["account_sid"], config["auth_token"])
        self.from_number = config["from_number"]  # "whatsapp:+14155238886"
        self.to_number = config["to_number"]       # "whatsapp:+5493415154942"

    async def send(self, mensaje: str):
        """Envía el mensaje vía Twilio WhatsApp Sandbox."""
        try:
            message = self.client.messages.create(
                from_=self.from_number,
                body=mensaje,
                to=self.to_number,
            )
            logger.info(f"WhatsApp enviado correctamente. SID: {message.sid}")
        except Exception as exc:
            logger.error(f"Error enviando WhatsApp vía Twilio: {exc}")
            raise
