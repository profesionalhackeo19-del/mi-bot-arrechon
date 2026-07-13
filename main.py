import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)
from groq import Groq
from supabase import create_client

# --- CONFIGURACIÓN ---
# Render leerá estas variables desde su pestaña "Environment"
CLIENT = Groq(api_key=os.environ["GROQ_API_KEY"])
SUPABASE = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
ADMIN_ID = 8616315480  # Tu ID de Telegram
QR_URL = "https://tu-enlace-de-imagen-aqui.jpg" 

SYSTEM_PROMPT = (
    "Eres una mujer fascinante, inteligente y sumamente seductora. "
    "Tu tono es femenino, coqueto, seguro y siempre con un toque de picardía. "
    "Responde siempre de forma envolvente y mantén el misterio. No menciones que eres una IA."
)

# --- LÓGICA DE BASE DE DATOS ---
def es_premium(user_id):
    user = SUPABASE.table("usuarios").select("plan", "vencimiento").eq("id", user_id).execute().data
    if not user: return False
    if user[0]['plan'] == 'premium':
        vencimiento = datetime.fromisoformat(user[0]['vencimiento'])
        if datetime.now() < vencimiento:
            return True
        else:
            # Plan vencido, actualizar a gratis
            SUPABASE.table("usuarios").update({"plan": "gratis"}).eq("id", user_id).execute()
    return False

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Registrar automáticamente si es nuevo
    usuario_existente = SUPABASE.table("usuarios").select("id").eq("id", user.id).execute().data
    if not usuario_existente:
        SUPABASE.table("usuarios").insert({"id": user.id, "username": user.username, "plan": "gratis"}).execute()
    
    keyboard = [
        [InlineKeyboardButton("💳 Comprar Pack NSFW (10 Soles)", callback_data='comprar')],
        [InlineKeyboardButton("💬 Chatear con la IA", callback_data='chat')]
    ]
    await update.message.reply_text("¡Hola! Soy tu compañera virtual. ¿En qué puedo complacerte hoy?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Si es foto, es comprobante
    if update.message.photo:
        keyboard = [[InlineKeyboardButton("✅ Activar Plan (1 Mes)", callback_data=f"activar_{user.id}")]]
        await context.bot.send_message(ADMIN_ID, f"Pago pendiente de @{user.username} (ID: {user.id})", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("¡Recibido! Estoy verificando tu pago... te avisaré en cuanto estés listo.")
        return

    # 2. Verificar acceso
    if not es_premium(user.id):
        await update.message.reply_text("Para hablar conmigo debes activar tu acceso premium. Usa el botón de comprar en /start.")
        return

    # 3. Respuesta con IA
    respuesta = CLIENT.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}],
        model="llama3-8b-8192"
    ).choices[0].message.content
    await update.message.reply_text(respuesta)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'comprar':
        texto = "💰 *Pack NSFW - 10 Soles*\n\nRealiza el Yape al QR y envíame el comprobante por aquí."
        await query.message.reply_photo(photo=QR_URL, caption=texto, parse_mode='Markdown')
        
    elif query.data == 'chat':
        await query.message.reply_text("Escríbeme cualquier cosa para empezar a charlar (debes ser usuario premium).")
        
    elif query.data.startswith("activar_"):
        user_id = int(query.data.split("_")[1])
        vencimiento = (datetime.now() + timedelta(days=30)).isoformat()
        SUPABASE.table("usuarios").update({"plan": "premium", "vencimiento": vencimiento}).eq("id", user_id).execute()
        await context.bot.send_message(user_id, "¡Plan activado! Ya puedes disfrutar de nuestra compañía digital por 30 días.")
        await query.edit_message_text("✅ Usuario activado exitosamente.")

if __name__ == '__main__':
    # Asegúrate de poner tu token de bot aquí o en las variables de entorno de Render
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    app.run_polling()
