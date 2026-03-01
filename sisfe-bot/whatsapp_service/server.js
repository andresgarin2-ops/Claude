/**
 * Servicio de WhatsApp para el bot SISFE.
 *
 * Cómo funciona:
 *   1. Al iniciar, imprime un QR en la terminal.
 *   2. Escaneás ese QR con tu WhatsApp (igual que WhatsApp Web).
 *   3. La sesión queda guardada en disco (no hace falta escanear cada vez).
 *   4. Expone un endpoint HTTP POST /send para enviar mensajes.
 *
 * Endpoints:
 *   POST /send   { "to": "+5493412345678", "message": "Hola!" }
 *   GET  /health  → { "status": "connected" | "disconnected" }
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const express = require("express");
const qrcode = require("qrcode-terminal");

const app = express();
app.use(express.json());

// -----------------------------------------------------------------------
// Cliente WhatsApp
// -----------------------------------------------------------------------

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: ".wwebjs_auth" }),
  puppeteer: {
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
    ],
  },
});

let isReady = false;

client.on("qr", (qr) => {
  console.log("\n========================================");
  console.log("  Escanea este QR con WhatsApp:");
  console.log("========================================");
  qrcode.generate(qr, { small: true });
  console.log("========================================\n");
});

client.on("ready", () => {
  isReady = true;
  console.log("✅ WhatsApp conectado y listo para enviar mensajes.");
});

client.on("disconnected", (reason) => {
  isReady = false;
  console.warn(`⚠️  WhatsApp desconectado: ${reason}`);
});

client.on("auth_failure", (msg) => {
  console.error("❌ Error de autenticación:", msg);
});

client.initialize();

// -----------------------------------------------------------------------
// HTTP API
// -----------------------------------------------------------------------

/**
 * POST /send
 * Body: { "to": "+5493412345678", "message": "Texto del mensaje" }
 */
app.post("/send", async (req, res) => {
  const { to, message } = req.body;

  if (!to || !message) {
    return res.status(400).json({ error: 'Se requieren los campos "to" y "message".' });
  }

  if (!isReady) {
    return res.status(503).json({
      error: "WhatsApp no está conectado aún. Esperá a que aparezca el QR y escanealo.",
    });
  }

  try {
    // Formato de chat ID para WhatsApp: número sin '+' + '@c.us'
    const chatId = to.replace(/^\+/, "") + "@c.us";
    await client.sendMessage(chatId, message);
    console.log(`[${new Date().toISOString()}] Mensaje enviado a ${to}`);
    return res.json({ success: true });
  } catch (err) {
    console.error(`Error enviando a ${to}:`, err.message);
    return res.status(500).json({ error: err.message });
  }
});

/**
 * GET /health
 * Devuelve el estado de la conexión.
 */
app.get("/health", (_req, res) => {
  res.json({ status: isReady ? "connected" : "disconnected" });
});

// -----------------------------------------------------------------------
// Arranque del servidor
// -----------------------------------------------------------------------

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n🚀 Servicio WhatsApp corriendo en http://localhost:${PORT}`);
  console.log("   Esperando conexión de WhatsApp...\n");
});
