"""
Orquestador principal del bot SISFE.
Diseñado para ejecutarse en GitHub Actions (modo one-shot).

Las credenciales se leen desde variables de entorno:
    SISFE_USERNAME, SISFE_PASSWORD
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

Uso local (para probar):
    SISFE_USERNAME=xxx SISFE_PASSWORD=yyy python main.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

from state import StateStore
from notifier import WhatsAppNotifier
from scraper import SISFEScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Inyectar credenciales desde variables de entorno (GitHub Secrets)
    config["sisfe"]["username"] = os.environ.get(
        "SISFE_USERNAME", config["sisfe"].get("username", "")
    )
    config["sisfe"]["password"] = os.environ.get(
        "SISFE_PASSWORD", config["sisfe"].get("password", "")
    )
    config["twilio"]["account_sid"] = os.environ.get(
        "TWILIO_ACCOUNT_SID", config["twilio"].get("account_sid", "")
    )
    config["twilio"]["auth_token"] = os.environ.get(
        "TWILIO_AUTH_TOKEN", config["twilio"].get("auth_token", "")
    )

    return config


def build_mensaje(expediente: dict, state: dict) -> str:
    codigo = expediente["codigo"]
    descripcion = expediente.get("descripcion", codigo)
    timestamp = datetime.fromisoformat(state["timestamp"]).strftime("%d/%m/%Y %H:%M")

    lines = [
        "Nuevo movimiento detectado en SISFE",
        f"Expediente: {codigo}",
        f"Descripcion: {descripcion}",
        f"Detectado: {timestamp}",
    ]
    if state.get("last_movement"):
        lines.append(f"Ultima actuacion: {state['last_movement']}")

    return "\n".join(lines)


async def check_expedientes(config: dict):
    state_path = Path(__file__).parent / config.get("state_file", "state.json")
    store = StateStore(str(state_path))
    notifier = WhatsAppNotifier(config["twilio"])

    async with SISFEScraper(config["sisfe"]) as scraper:
        logged_in = await scraper.login()
        if not logged_in:
            logger.error(
                "No se pudo hacer login en SISFE. "
                "Revisá SISFE_USERNAME y SISFE_PASSWORD en los secretos de GitHub."
            )
            sys.exit(1)

        for exp in config["expedientes"]:
            codigo = exp["codigo"]
            logger.info(f"Procesando expediente: {codigo}")

            state = await scraper.get_expediente_state(codigo)
            if state is None:
                logger.warning(f"No se pudo obtener estado de {codigo}, se omite.")
                continue

            prev = store.get_last_state(codigo)

            if prev is None:
                store.save_state(codigo, state)
                logger.info(
                    f"[{codigo}] Estado inicial registrado. "
                    "No se envía notificación (sin estado previo para comparar)."
                )
            elif prev["hash"] != state["hash"]:
                logger.info(f"[{codigo}] *** CAMBIO DETECTADO ***")
                store.save_state(codigo, state)
                mensaje = build_mensaje(exp, state)
                await notifier.send(mensaje)
            else:
                logger.info(f"[{codigo}] Sin cambios.")


if __name__ == "__main__":
    config = load_config()
    asyncio.run(check_expedientes(config))
