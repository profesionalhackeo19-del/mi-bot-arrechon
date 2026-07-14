import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)
from groq import Groq
from supabase import create_client

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURACIÓN ---
# Asegúrate de que las variables estén en Render (Environment)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
SUPA_URL = os.environ.get("SUPABASE_URL")
SUPA_KEY = os.environ.get("SUPABASE_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8616315480 

CLIENT = Groq(api_key=GROQ_KEY)
SUPABASE = create_client(SUPA_URL, SUPA_KEY)

SYSTEM_PROMPT = (
    "Eres una modelo fascinante, inteligente y seductora. Tu tono es adulto, picante y directo. "
    "Manejas un lenguaje sensual, siempre manteniendo el rol de una mujer que ofrece contenido premium."
)

# --- SERVIDOR PARA EVITAR ERROR DE PUERTO EN RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- LÓGICA DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Guardar en base de datos
    SUPABASE.table("usuarios").upsert({"id": user.id, "username": user.username, "plan": "gratis"}).execute()
    
    keyboard = [
        [InlineKeyboardButton("🔥 Comprar Pack Hot 18🔞", callback_data='comprar')],
        [InlineKeyboardButton("💬 Chatear con la IA", callback_data='chat')]
    ]
    await update.message.reply_text("✨ *Bienvenida a tu espacio exclusivo*\n\n¿Qué deseas explorar hoy?", 
                                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'comprar':
        # Envío del archivo yape.png local
        try:
            with open('yape.png', 'rb') as foto:
                await query.message.reply_photo(photo=foto, caption="💰 *Pack Hot 18🔞*\n\nRealiza el pago y envíame la foto del comprobante aquí.")
        except FileNotFoundError:
            await query.message.reply_text("⚠️ Error: No se encontró la imagen de pago. Por favor avisa al admin.")
            
    elif query.data == 'chat':
        await query.edit_message_text("✅ Escríbeme cualquier cosa para empezar a charlar...")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        await context.bot.send_message(ADMIN_ID, f"🔔 Nuevo comprobante de @{update.effective_user.username}")
        await update.message.reply_text("📸 Comprobante recibido. Estoy verificando tu pago...")
        return

    try:
        response = CLIENT.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}],
            model="llama3-8b-8192"
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("...Estoy ocupada ahora. Intenta de nuevo.")

# --- INICIO ---
if __name__ == '__main__':
    # 1. Arrancamos el servidor web en un hilo (para que Render no se queje)
    threading.Thread(target=run_health_check, daemon=True).start()
    
    # 2. Arrancamos el bot de Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    
    print("Bot iniciado correctamente...")
    app.run_polling()
