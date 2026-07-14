import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)
from groq import Groq
from supabase import create_client

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURACIÓN ---
# Asegúrate de tener estas variables configuradas en Render (Environment)
CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY"))
SUPABASE = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
ADMIN_ID = 8616315480 

SYSTEM_PROMPT = (
    "Eres una modelo fascinante, inteligente y seductora. Tu tono es adulto, picante y directo. "
    "Manejas un lenguaje sensual, siempre manteniendo el rol de una mujer que ofrece contenido premium. "
    "No menciones que eres una IA, mantén el aura de exclusividad."
)

# --- LÓGICA PREMIUM ---
def es_premium(user_id):
    try:
        response = SUPABASE.table("usuarios").select("plan", "vencimiento").eq("id", user_id).execute()
        if not response.data: return False
        user = response.data[0]
        if user['plan'] == 'premium':
            if datetime.now() < datetime.fromisoformat(user['vencimiento']):
                return True
    except Exception as e:
        logging.error(f"Error en base de datos: {e}")
    return False

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    SUPABASE.table("usuarios").upsert({"id": user.id, "username": user.username, "plan": "gratis"}).execute()
    
    keyboard = [
        [InlineKeyboardButton("🔥 Comprar Pack Hot 18🔞", callback_data='comprar')],
        [InlineKeyboardButton("💬 Chatear con la IA", callback_data='chat')]
    ]
    await update.message.reply_text("✨ *Bienvenida a tu espacio exclusivo*\n\n¿Qué deseas explorar hoy?", 
                                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si envían foto, es un comprobante
    if update.message.photo:
        await context.bot.send_message(ADMIN_ID, f"🔔 Nuevo comprobante de @{update.effective_user.username}")
        await update.message.reply_text("📸 Comprobante recibido. Estoy verificando tu pago...")
        return

    # Si es texto, chat con IA
    if not es_premium(update.effective_user.id):
        await update.message.reply_text("🔒 *Acceso restringido*. Debes comprar el Pack para chatear conmigo.", parse_mode='Markdown')
        return

    try:
        response = CLIENT.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}],
            model="llama3-8b-8192"
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Error Groq: {e}")
        await update.message.reply_text("...Estoy procesando demasiadas emociones ahora. Intenta de nuevo en un momento.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'comprar':
        # ENVÍO DE ARCHIVO LOCAL
        try:
            with open('yape.png', 'rb') as foto:
                await query.message.reply_photo(photo=foto, caption="💰 *Pack Hot 18🔞*\n\nRealiza el pago y envíame la foto del comprobante aquí.", parse_mode='Markdown')
        except FileNotFoundError:
            await query.message.reply_text("⚠️ Error técnico: Imagen de pago no encontrada.")
            
    elif query.data == 'chat':
        await query.edit_message_text("✅ Escríbeme cualquier cosa para empezar a charlar...")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    app.run_polling()
