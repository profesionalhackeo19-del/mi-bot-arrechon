import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)
from groq import Groq
from supabase import create_client

# Configuración de clientes (Render usará las variables de entorno)
CLIENT = Groq(api_key=os.environ["GROQ_API_KEY"])
SUPABASE = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
ADMIN_ID = 8616315480

# Configuración de personalidad
SYSTEM_PROMPT = (
    "Eres una mujer fascinante, inteligente y sumamente seductora. "
    "Tu tono es femenino, coqueto, seguro y siempre con un toque de picardía. "
    "Responde siempre de forma envolvente y mantén el misterio. No menciones que eres una IA."
)

# --- FUNCIÓN DE VERIFICACIÓN ---
def es_premium(user_id):
    user = SUPABASE.table("usuarios").select("plan", "vencimiento").eq("id", user_id).execute().data
    if not user: return False
    if user[0]['plan'] == 'premium':
        vencimiento = datetime.fromisoformat(user[0]['vencimiento'])
        if datetime.now() < vencimiento:
            return True
        else:
            SUPABASE.table("usuarios").update({"plan": "gratis"}).eq("id", user_id).execute()
    return False

# --- COMANDO ADMINISTRATIVO (ANUNCIOS Y VIDEOS) ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    usuarios = SUPABASE.table("usuarios").select("id").execute().data
    for u in usuarios:
        try:
            if update.message.photo:
                await context.bot.send_photo(u['id'], update.message.photo[-1].file_id, caption=update.message.caption)
            elif update.message.video:
                await context.bot.send_video(u['id'], update.message.video.file_id, caption=update.message.caption)
            else:
                texto = update.message.text.replace("/broadcast ", "")
                await context.bot.send_message(u['id'], texto)
        except: continue
    await update.message.reply_text("Contenido enviado a todos exitosamente.")

# --- MANEJO DE MENSAJES Y PAGOS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Recibir comprobante de pago
    if update.message.photo and user.id != ADMIN_ID:
        keyboard = [[InlineKeyboardButton("Activar Plan (1 Mes)", callback_data=f"activar_{user.id}")]]
        await context.bot.send_message(ADMIN_ID, f"Pago pendiente de @{user.username} (ID: {user.id})", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("Comprobante recibido. En breve activaré tu plan.")
        return

    # 2. Verificar acceso premium
    if not es_premium(user.id):
        await update.message.reply_text("Hola... Para hablar conmigo necesitas activar tu plan premium (10 soles). Envía la foto de tu comprobante de Yape aquí.")
        return

    # 3. Respuesta con IA (Personalidad seductora)
    respuesta = CLIENT.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}],
        model="llama3-8b-8192"
    ).choices[0].message.content
    await update.message.reply_text(respuesta)

# --- ACTIVACIÓN AUTOMÁTICA ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("activar_"):
        user_id = int(query.data.split("_")[1])
        vencimiento = (datetime.now() + timedelta(days=30)).isoformat()
        SUPABASE.table("usuarios").update({"plan": "premium", "vencimiento": vencimiento}).eq("id", user_id).execute()
        await context.bot.send_message(user_id, "¡Plan activo, querido usuario! Ya puedes disfrutar de todo por 30 días.")
        await query.edit_message_text("Usuario activado por 30 días.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
