import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)
from groq import Groq
from supabase import create_client

# --- CONFIGURACIÓN ---
# Render leerá estas variables desde su pestaña "Environment"
CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY"))
SUPABASE = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
ADMIN_ID = 8616315480  # Tu ID de Telegram
QR_URL_AQUI = "https://tu-enlace-de-imagen-aqui.jpg" 

SYSTEM_PROMPT = (
    "Eres una modelo fascinante y atrevida, experta en contenido exclusivo y seductor. "
    "Tu tono es totalmente adulto, picante, sugerente y directo. "
    "Manejas un lenguaje muy sensual y atrevido, siempre manteniendo el rol de una mujer "
    "que ofrece contenido privado de alto nivel (+18). No menciones que eres una IA."
)

# --- BASE DE DATOS ---
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

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Registro automático
    usuario_existente = SUPABASE.table("usuarios").select("id").eq("id", user.id).execute().data
    if not usuario_existente:
        SUPABASE.table("usuarios").insert({"id": user.id, "username": user.username, "plan": "gratis"}).execute()
    
    keyboard = [
        [InlineKeyboardButton("🔥 Comprar Pack Hot 18🔞", callback_data='comprar')],
        [InlineKeyboardButton("💬 Chatear con la IA", callback_data='chat')]
    ]
    await update.message.reply_text("¡Bienvenido al espacio exclusivo! ¿Qué deseas hacer hoy?", reply_markup=InlineKeyboardMarkup(keyboard))

async def anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    usuarios = SUPABASE.table("usuarios").select("id").execute().data
    
    enviados = 0
    for u in usuarios:
        try:
            if update.message.photo:
                await context.bot.send_photo(u['id'], update.message.photo[-1].file_id, caption=update.message.caption.replace("/anuncio ", ""))
            elif update.message.video:
                await context.bot.send_video(u['id'], update.message.video.file_id, caption=update.message.caption.replace("/anuncio ", ""))
            else:
                texto = update.message.text.replace("/anuncio ", "")
                await context.bot.send_message(u['id'], texto)
            enviados += 1
        except: continue
    await update.message.reply_text(f"✅ Anuncio enviado a {enviados} usuarios.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if update.message.photo:
        keyboard = [[InlineKeyboardButton("✅ Activar Plan (1 Mes)", callback_data=f"activar_{user.id}")]]
        await context.bot.send_message(ADMIN_ID, f"Pago pendiente de @{user.username}", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("¡Recibido! Estoy verificando tu pago.")
        return

    if not es_premium(user.id):
        await update.message.reply_text("Primero debes comprar el acceso premium para hablar conmigo.")
        return

    respuesta = CLIENT.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}],
        model="llama3-8b-8192"
    ).choices[0].message.content
    await update.message.reply_text(respuesta)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'comprar':
        texto = "🔥 *Pack Hot 18🔞 - Acceso Exclusivo*\n\nRealiza el pago al QR y envíame el comprobante."
        await query.message.reply_photo(photo=QR_URL_AQUI, caption=texto, parse_mode='Markdown')
    elif query.data == 'chat':
        if es_premium(query.from_user.id):
            await query.edit_message_text("✅ Ahora puedes escribirme, estoy lista para escucharte...")
        else:
            await query.edit_message_text("⚠️ No tienes acceso premium. Usa el botón de comprar.")
    elif query.data.startswith("activar_"):
        user_id = int(query.data.split("_")[1])
        vencimiento = (datetime.now() + timedelta(days=30)).isoformat()
        SUPABASE.table("usuarios").update({"plan": "premium", "vencimiento": vencimiento}).eq("id", user_id).execute()
        await context.bot.send_message(user_id, "¡Plan activado! Ya puedes disfrutar de todo el contenido.")
        await query.edit_message_text("✅ Usuario activado.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("anuncio", anuncio))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    app.run_polling()
