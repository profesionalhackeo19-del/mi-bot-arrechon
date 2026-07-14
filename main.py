import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# 1. Configuración de Logging y Constantes
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ADMIN_ID = 8616315480 
USERS_FILE = "usuarios.json"

# 2. Inicialización de Groq y carga de usuarios persistentes
client = Groq(api_key=GROQ_API_KEY)
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f: return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(list(users), f)

users_db = load_users()

# 3. Servidor de Health Check (Mantiene el Web Service vivo en Render)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Bot OK")
def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# 4. Funciones de Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_db:
        users_db.add(user_id); save_users(users_db)
    await update.message.reply_text("Hola. Usa /ayuda para ver los comandos disponibles.")

async def cmd_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Uso: /ia [tu pregunta]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    try:
        chat = client.chat.completions.create(messages=[{"role": "user", "content": query}], model="llama3-8b-8192")
        await update.message.reply_text(chat.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"Error de IA: {e}")

async def cmd_pack18(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sustituye este link por tu URL real de imagen del QR
    qr_url = "https://i.imgur.com/TuCodigoQR.png" 
    caption = "🔞 PACK VIP 18+ 🔞\nPrecio: 10 Soles\n\n1. Escanea el QR.\n2. Yapea 10 soles.\n3. Envía el comprobante a @Dratsystim."
    await update.message.reply_photo(photo=qr_url, caption=caption)

async def cmd_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Solo para el Admin."); return
    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje/video que quieres difundir."); return
    
    count = 0
    for user_id in users_db:
        try:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            count += 1
        except: continue
    await update.message.reply_text(f"Anuncio enviado a {count} usuarios.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Bot Activo. Usuarios registrados: {len(users_db)}")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "/ia - Preguntar a IA\n/pack18 - Comprar acceso\n/status - Info\n/contacto - Admin"
    await update.message.reply_text(msg)

# 5. Ejecución del Bot
if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ia", cmd_ia))
    app.add_handler(CommandHandler("pack18", cmd_pack18))
    app.add_handler(CommandHandler("anuncio", cmd_anuncio))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    logging.info("Bot Iniciado...")
    app.run_polling()
