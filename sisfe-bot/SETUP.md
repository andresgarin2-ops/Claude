# Bot SISFE - Guía de instalación

## Cómo funciona

1. El bot abre un Chromium invisible, hace login en SISFE y consulta cada expediente.
2. Compara el contenido actual con el guardado en `state.json`.
3. Si hay un cambio → manda un **WhatsApp vía Twilio**.
4. El estado se guarda localmente en `state.json`.

---

## Instalación desde cero (una sola vez)

### Requisitos
- Python 3.10 o superior → https://www.python.org/downloads/
- Durante la instalación de Python en Windows: **tildar "Add Python to PATH"**

### Pasos

```bash
# 1. Ir a la carpeta del bot
cd sisfe-bot

# 2. (Opcional pero recomendado) Crear entorno virtual
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar el navegador Chromium
playwright install chromium
```

---

## Configurar credenciales

Copiá el archivo `.env.example` y renombralo como `.env`:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Abrí `.env` con el Bloc de notas y completá los valores:

```
SISFE_MATRICULA=XLVIII338        ← tu matrícula
SISFE_PASSWORD=tu_contraseña
TWILIO_ACCOUNT_SID=ACxxxxxxxx...
TWILIO_AUTH_TOKEN=xxxxxxxx...
```

> **Importante:** el archivo `.env` está en `.gitignore` y nunca se sube a GitHub.

---

## Agregar expedientes a monitorear

Editá `config.yaml`:

```yaml
expedientes:
  - codigo: "21-25448313-0"
    descripcion: "Censi c/ Gomez s/ ejecutivo"
  - codigo: "21-XXXXXXXX-X"
    descripcion: "Otro expediente"
```

La circunscripción y el colegio también se configuran ahí:

```yaml
sisfe:
  circunscripcion: "Rosario"
  colegio: "Abogados"
```

---

## Activar el sandbox de Twilio WhatsApp (una sola vez)

Antes de recibir mensajes tenés que unirte al sandbox:

1. Desde tu WhatsApp, mandá un mensaje a **+1 415 523 8886**
2. El texto debe ser: `join <palabra-del-sandbox>`
   (la encontrás en Twilio Console → Messaging → Try it out → Send a WhatsApp message)

---

## Ejecutar el bot

### Prueba manual (una sola vez para verificar)

```bash
cd sisfe-bot
python main.py
```

El log aparece en pantalla. La primera vez registra el estado inicial (no envía WhatsApp). Las siguientes veces envía WhatsApp solo si hubo cambios.

---

## Programar ejecución automática (cada 1 hora)

### Windows — Programador de tareas

1. Buscá **"Programador de tareas"** en el menú inicio
2. Clic en **"Crear tarea básica..."**
3. Nombre: `Bot SISFE`
4. Desencadenador: **Diariamente**, repetir cada **1 hora**
5. Acción: **Iniciar un programa**
   - Programa: ruta completa al `run.bat`, por ejemplo:
     `C:\Users\TuNombre\Documents\Claude\sisfe-bot\run.bat`
6. En **"Condiciones"**: desmarcá "Iniciar la tarea solo si el equipo está conectado a la corriente"
7. Finalizá

El log queda en `sisfe-bot\sisfe_bot.log`.

### Linux/Mac — cron

```bash
crontab -e
```

Agregá esta línea (reemplazá la ruta):

```
0 * * * * /home/tuusuario/Claude/sisfe-bot/run.sh
```

---

## Troubleshooting

| Problema | Solución |
|---|---|
| Error de login | Revisá `SISFE_MATRICULA` y `SISFE_PASSWORD` en el archivo `.env` |
| No encuentra campos | La UI del SISFE puede haber cambiado. Aparecen screenshots `debug_*.png` en la carpeta |
| WhatsApp no llega | Verificá que te hayas unido al sandbox de Twilio |
| `python` no se reconoce (Windows) | Reinstalá Python tildando "Add to PATH", o usá `py` en lugar de `python` |
| Error de módulo `dotenv` | Corré `pip install -r requirements.txt` de nuevo |
