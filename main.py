import os, json, logging, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# 1. Configuración
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN, GROQ_API_KEY = os.environ.get("BOT_TOKEN"), os.environ.get("GROQ_API_KEY")
ADMIN_ID = 8616315480 
USERS_FILE = "usuarios.json"
client = Groq(api_key=GROQ_API_KEY)

# 2. Persistencia
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f: return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(list(users), f)

users_db = load_users()

# 3. Servidor de Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Bot OK")
    def log_message(self, format, *args): return

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# 4. Funciones
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_db: users_db.add(user_id); save_users(users_db)
    await update.message.reply_text("Hola. Usa /ia para chatear o /pack18 para información de acceso.")

async def handle_chat_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Esto maneja texto normal y comandos /ia
    query = update.message.text.replace("/ia", "").strip()
    if not query: return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    try:
        chat = client.chat.completions.create(messages=[{"role": "user", "content": query}], model="llama3-8b-8192")
        await update.message.reply_text(chat.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text("Error de IA. Inténtalo más tarde.")

async def cmd_pack18(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Cambia este link por tu QR real
    qr_url = "https://i.imgur.com/TuCodigoQR.png"
    msg = "🔞 PACK VIP 18+ 🔞\nPrecio: 10 Soles\n\n1. Yapea al QR.\n2. Envía la captura de pantalla por este chat.\nEl sistema notificará el pago automáticamente."
    await update.message.reply_photo(photo=qr_url, caption=msg)

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reenvía foto/comprobante al admin sin mostrar al admin al usuario
    await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    await update.message.reply_text("✅ Comprobante enviado. En breve será verificado.")

async def cmd_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje/media que quieres difundir."); return
    
    count = 0
    for user_id in users_db:
        try:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            count += 1
        except: continue
    await update.message.reply_text(f"Anuncio enviado a {count} usuarios.")

# 5. Ejecución
if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pack18", cmd_pack18))
    app.add_handler(CommandHandler("anuncio", cmd_anuncio))
    
    # Manejadores automáticos (estables)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_chat_ia))
    app.add_handler(CommandHandler("ia", handle_chat_ia))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_payment_proof))
    
    app.run_polling()
