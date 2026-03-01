# Bot SISFE - Guía de instalación (GitHub Actions + Twilio)

## Cómo funciona

1. GitHub Actions corre el bot **automáticamente cada hora**.
2. El bot abre un Chromium invisible, hace login en SISFE y consulta cada expediente.
3. Compara el contenido actual con el guardado en `state.json`.
4. Si hay un cambio → manda un **WhatsApp vía Twilio**.
5. `state.json` se commitea automáticamente al repo con el estado actualizado.

---

## Configuración (una sola vez)

### 1. Agregar los expedientes a monitorear

Editá `config.yaml` y reemplazá los valores de ejemplo:

```yaml
expedientes:
  - codigo: "21-02343434-2"   # ← tu número de expediente
    descripcion: "Mi expediente"
```

> El formato es `JUR-NUMERO-SUFIJO`. Si no sabés el formato exacto, consultá la URL
> que usa el SISFE cuando lo buscás manualmente.

### 2. Configurar los secretos en GitHub

En tu repositorio: **Settings → Secrets and variables → Actions → New repository secret**

| Secreto | Valor |
|---|---|
| `SISFE_MATRICULA` | Tu número de matrícula (ej: `XLVIII338`) |
| `SISFE_PASSWORD` | Tu contraseña del SISFE |
| `TWILIO_ACCOUNT_SID` | Account SID de Twilio |
| `TWILIO_AUTH_TOKEN` | Auth Token de Twilio |

> La Circunscripción (`Rosario`) y el Colegio (`Abogados`) están en `config.yaml`
> porque no son datos sensibles.

### 3. Activar el sandbox de Twilio WhatsApp

Antes de que puedas recibir mensajes, tenés que unirte al sandbox:

1. En tu WhatsApp, mandá un mensaje a **+1 415 523 8886**
2. El mensaje debe ser: `join <palabra-del-sandbox>`
   (la palabra la encontrás en Twilio Console → Messaging → Try it out → Send a WhatsApp message)

---

## Ejecutar manualmente

En GitHub: **Actions → Check SISFE Expedientes → Run workflow**

---

## Ejecutar en local (para probar)

```bash
cd sisfe-bot
pip install -r requirements.txt
playwright install chromium

SISFE_MATRICULA="XLVIII338" \
SISFE_PASSWORD="1397" \
TWILIO_ACCOUNT_SID="ACxxxxx" \
TWILIO_AUTH_TOKEN="xxxxx" \
python main.py
```

---

## Troubleshooting

| Problema | Solución |
|---|---|
| Error de login | Revisá `SISFE_USERNAME` y `SISFE_PASSWORD` en los secrets |
| No encuentra campos | La UI del SISFE puede haber cambiado. Revisá `debug_*.png` en los artefactos del Action |
| WhatsApp no llega | Verificá que te hayas unido al sandbox de Twilio |
| `state.json` no se commitea | Verificá que el workflow tenga `permissions: contents: write` |
