"""
Orquestador principal del bot SISFE.
Puede ejecutarse en GitHub Actions o localmente desde una PC.

Las credenciales se leen desde un archivo .env (ejecución local)
o desde variables de entorno / GitHub Secrets (CI).

Uso local:
    1. Copiá .env.example a .env y completá los valores
    2. python main.py
"""

import asyncio
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Cargar .env si existe (ejecución local). En GitHub Actions no existe y se ignora.
load_dotenv(Path(__file__).parent / ".env")

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
    config["sisfe"]["matricula"] = os.environ.get(
        "SISFE_MATRICULA", config["sisfe"].get("matricula", "")
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
                "Revisá SISFE_MATRICULA y SISFE_PASSWORD en el archivo .env."
            )
            sys.exit(1)

        for i, exp in enumerate(config["expedientes"]):
            if i > 0:
                espera = random.uniform(8, 15)
                logger.info(f"Esperando {espera:.1f}s antes del siguiente expediente...")
                await asyncio.sleep(espera)

            codigo = exp["codigo"]
            localidad = exp.get("localidad")
            # Clave única por expediente+localidad para no mezclar estados
            state_key = f"{codigo}|{localidad}" if localidad else codigo
            label = f"{codigo} ({localidad})" if localidad else codigo
            logger.info(f"Procesando expediente: {label}")

            state = await scraper.get_expediente_state(codigo, localidad=localidad)
            if state is None:
                logger.warning(f"No se pudo obtener estado de {label}, se omite.")
                continue

            prev = store.get_last_state(state_key)

            if prev is None:
                store.save_state(state_key, state)
                logger.info(
                    f"[{label}] Estado inicial registrado. "
                    "No se envía notificación (sin estado previo para comparar)."
                )
            elif prev["hash"] != state["hash"]:
                logger.info(f"[{label}] *** CAMBIO DETECTADO ***")
                store.save_state(state_key, state)
                mensaje = build_mensaje(exp, state)
                await notifier.send(mensaje)
            else:
                logger.info(f"[{label}] Sin cambios.")


if __name__ == "__main__":
    config = load_config()
    asyncio.run(check_expedientes(config))
