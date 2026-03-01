"""
Orquestador principal del bot SISFE.

Uso:
    python main.py           # corre el bot en modo continuo
    python main.py --once    # consulta una sola vez y termina (útil para probar)
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import Database
from notifier import WhatsAppNotifier
from scraper import SISFEScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sisfe_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_mensaje(expediente: dict, state: dict) -> str:
    codigo = expediente["codigo"]
    descripcion = expediente.get("descripcion", codigo)
    timestamp = datetime.fromisoformat(state["timestamp"]).strftime("%d/%m/%Y %H:%M")

    lines = [
        "📋 *Nuevo movimiento detectado en SISFE*",
        f"Expediente: *{codigo}*",
        f"Descripción: {descripcion}",
        f"Detectado: {timestamp}",
    ]
    if state.get("last_movement"):
        lines.append(f"Última actuación: {state['last_movement']}")

    return "\n".join(lines)


async def check_expedientes(config: dict):
    db = Database(config["database"]["path"])
    notifier = WhatsAppNotifier(config["whatsapp"])

    if not await notifier.is_service_up():
        logger.warning(
            "El servicio de WhatsApp no está activo. "
            "Iniciá 'node whatsapp_service/server.js' antes de correr el bot."
        )

    async with SISFEScraper(config["sisfe"]) as scraper:
        logged_in = await scraper.login()
        if not logged_in:
            logger.error(
                "No se pudo hacer login en SISFE. "
                "Revisá usuario/contraseña en config.yaml."
            )
            return

        for exp in config["expedientes"]:
            codigo = exp["codigo"]
            logger.info(f"Procesando expediente: {codigo}")

            state = await scraper.get_expediente_state(codigo)
            if state is None:
                logger.warning(f"No se pudo obtener estado de {codigo}, se omite.")
                continue

            prev = db.get_last_state(codigo)

            if prev is None:
                # Primera vez que se consulta este expediente
                db.save_state(codigo, state)
                logger.info(
                    f"[{codigo}] Estado inicial registrado. "
                    "No se envía notificación (sin estado previo para comparar)."
                )
            elif prev["hash"] != state["hash"]:
                # Hay un cambio real
                logger.info(f"[{codigo}] *** CAMBIO DETECTADO ***")
                db.save_state(codigo, state)
                mensaje = build_mensaje(exp, state)
                await notifier.send(mensaje)
            else:
                logger.info(f"[{codigo}] Sin cambios.")


async def run_once():
    config = load_config()
    await check_expedientes(config)


async def run_continuous():
    config = load_config()
    interval = config["scheduler"]["intervalo_minutos"]

    logger.info(f"Bot iniciado. Revisando cada {interval} minutos.")
    logger.info(f"Expedientes monitoreados: {[e['codigo'] for e in config['expedientes']]}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_expedientes,
        "interval",
        minutes=interval,
        args=[config],
        id="check_sisfe",
        next_run_time=datetime.now(),  # Primera ejecución inmediata
    )
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Deteniendo bot...")
        scheduler.shutdown()


if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(run_once())
    else:
        asyncio.run(run_continuous())
