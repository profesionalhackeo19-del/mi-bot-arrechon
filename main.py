import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from supabase import create_client

# Inicialización de clientes
client = Groq(api_key=os.environ["GROQ_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# Configuración de personalidad
SYSTEM_PROMPT = (
    "Eres una mujer fascinante, inteligente y sumamente seductora. "
    "Tu tono es femenino, coqueto, seguro y siempre con un toque de picardía. "
    "Responde siempre de forma envolvente y mantén el misterio. No menciones que eres una IA."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Registro en Supabase
    response = supabase.table("usuarios").select("id").eq("id", user.id).execute()
    if not response.data:
        supabase.table("usuarios").insert({"id": user.id, "username": user.username}).execute()
        await update.message.reply_text("¡Hola! Me alegra que hayas venido a buscarme.")
    else:
        await update.message.reply_text("¡Hola de nuevo! Estaba esperando a que volvieras.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}],
        model="llama3-8b-8192",
    )
    await update.message.reply_text(chat_completion.choices[0].message.content)

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
