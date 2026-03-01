"""
Descarga la ultima version de los archivos del bot desde GitHub.
Correr desde la carpeta sisfe-bot:  python update.py
"""
import urllib.request

REPO = "https://raw.githubusercontent.com/andresgarin2-ops/Claude/refs/heads/claude/demo-capabilities-T6xv9/sisfe-bot"

ARCHIVOS = [
    "main.py",
    "scraper.py",
    "notifier.py",
    "state.py",
]

for archivo in ARCHIVOS:
    url = f"{REPO}/{archivo}"
    try:
        urllib.request.urlretrieve(url, archivo)
        print(f"OK  {archivo}")
    except Exception as e:
        print(f"ERROR  {archivo}: {e}")
