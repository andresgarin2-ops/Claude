# Bot SISFE - Guía de instalación

## Requisitos

- Python 3.11+
- Node.js 18+
- npm

---

## Instalación

### 1. Dependencias Python

```bash
cd sisfe-bot
pip install -r requirements.txt
playwright install chromium
```

### 2. Dependencias Node.js (servicio WhatsApp)

```bash
cd whatsapp_service
npm install
```

---

## Configuración

Editá `config.yaml` con tus datos:

```yaml
sisfe:
  username: "tu_usuario"
  password: "tu_contraseña"

expedientes:
  - codigo: "21-02343434-2"
    descripcion: "Mi expediente"

whatsapp:
  destinatarios:
    - "+5493412345678"   # tu número con código de país
```

---

## Uso

Necesitás dos terminales:

### Terminal 1 - Servicio WhatsApp

```bash
cd whatsapp_service
node server.js
```

La primera vez imprime un QR. **Escanealo con WhatsApp** (igual que WhatsApp Web).
La sesión queda guardada; no hace falta escanear de nuevo.

### Terminal 2 - Bot principal

```bash
cd sisfe-bot
python main.py
```

El bot se ejecuta cada 30 minutos (configurable en `config.yaml`).

### Probar una sola consulta

```bash
python main.py --once
```

---

## Cómo funciona

1. El bot abre un navegador Chromium invisible.
2. Hace login en el SISFE con tu usuario/contraseña.
3. Consulta cada expediente de la lista.
4. Compara el contenido actual con el guardado en `sisfe_bot.db`.
5. Si hay diferencias → manda un WhatsApp a los números configurados.

### Primera ejecución

En la primera ejecución **no se envía ninguna notificación**: solo se guarda
el estado inicial. A partir de la segunda, cualquier cambio dispara la alerta.

---

## Troubleshooting

| Problema | Solución |
|---|---|
| Error de login | Revisá usuario/contraseña. Se guarda un screenshot `debug_login_failed.png` |
| No encuentra campos | La UI del SISFE puede haber cambiado. Revisá `debug_*.png` |
| WhatsApp no conecta | Asegurate de haber escaneado el QR en el paso de la Terminal 1 |
| Errores de red | El bot reintenta automáticamente en la próxima ejecución programada |
