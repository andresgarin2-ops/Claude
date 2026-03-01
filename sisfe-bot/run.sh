#!/bin/bash
# ============================================================
#  Bot SISFE - Lanzador para Linux/Mac
#  Agregá al crontab: crontab -e
#  Ejemplo (cada hora):  0 * * * * /ruta/al/sisfe-bot/run.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activar entorno virtual si existe
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

LOG_FILE="sisfe_bot.log"
echo "" >> "$LOG_FILE"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG_FILE"
python main.py >> "$LOG_FILE" 2>&1

# Mantener solo las últimas 5000 líneas del log
tail -5000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
