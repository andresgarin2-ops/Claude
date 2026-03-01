"""
Notificador de WhatsApp.
Llama al servicio Node.js (whatsapp_service/server.js) que mantiene
la sesión de WhatsApp Web abierta.
"""

import logging
import aiohttp

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    def __init__(self, config: dict):
        self.service_url = config.get("service_url", "http://localhost:3000/send")
        self.destinatarios: list[str] = config.get("destinatarios", [])

    async def send(self, mensaje: str):
        """Envía un mensaje a todos los destinatarios configurados."""
        for numero in self.destinatarios:
            await self._send_one(numero, mensaje)

    async def _send_one(self, numero: str, mensaje: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.service_url,
                    json={"to": numero, "message": mensaje},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Mensaje enviado a {numero}")
                    else:
                        body = await resp.text()
                        logger.error(
                            f"Error al enviar a {numero}: HTTP {resp.status} - {body}"
                        )
        except aiohttp.ClientConnectorError:
            logger.error(
                "No se pudo conectar al servicio WhatsApp. "
                "Asegurate de que 'whatsapp_service/server.js' esté corriendo."
            )
        except Exception as exc:
            logger.error(f"Excepción enviando WhatsApp a {numero}: {exc}")

    async def is_service_up(self) -> bool:
        """Verifica si el servicio de WhatsApp está activo."""
        health_url = self.service_url.replace("/send", "/health")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
