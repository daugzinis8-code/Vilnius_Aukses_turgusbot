import os
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# Tokenas tik iš Render Environment - kode nieko klijuot nereikia!
BOT_TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@vilniaus_aukses_turgus")

if not BOT_TOKEN:
    print("❌ Nėra TOKEN! Eik į Render -> Environment -> pridėk TOKEN")

FOTO, PAVADINIMAS, KATEGORIJA, KAINA, APRASYMAS, VIETA, KONTAKTAS, PATVIRTINIMAS = range(8)
logging.basicConfig(level=logging.INFO)
KATEGORIJOS = [["🏠 Namai, buitis","👕 Drabužiai"],["📱 Technika","🚲 Transportas"],["🧸 Vaikams","🌱 Sodas"],["🛠️ Įrankiai","📚 Knygos"],["🎁 Dovanoju","💛 Kita"]]
laikini_skelbimai = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb=[[InlineKeyboardButton("➕ Įdėti skelbimą",callback_data="ideti")]]
    await update.message.reply_text("💛 **VILNIAUS AUKSĖS TURGUS** 💛\n\nDukrytės Auksės garbei!\n\n/ideti - Įdėti skelbimą",reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
async def ideti_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    if q: await q.answer()
    context.user_data.clear()
    await (q.message if q else update.message).reply_text("📸 1/7 - Foto (arba 'neturiu')",reply_markup=ReplyKeyboardRemove())
    return FOTO
async def gavo_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['foto']=update.message.photo[-1].file_id if update.message.photo else None
    await update.message.reply_text("📝 2/7 - Pavadinimas?"); return PAVADINIMAS
async def gavo_pavadinima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pavadinimas']=update.message.text; kb=[[InlineKeyboardButton(t,callback_data=f"kat_{t}") for t in r] for r in KATEGORIJOS]
    await update.message.reply_text("📦 3/7 - Kategorija",reply_markup=InlineKeyboardMarkup(kb)); return KATEGORIJA
async def gavo_kategorija(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); context.user_data['kategorija']=q.data.replace("kat_",""); await q.message.reply_text("💰 4/7 - Kaina"); return KAINA
async def gavo_kaina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kaina']=update.message.text; await update.message.reply_text("✍️ 5/7 - Aprašymas"); return APRASYMAS
async def gavo_aprasyma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['aprasymas']=update.message.text; await update.message.reply_text("📍 6/7 - Vieta"); return VIETA
async def gavo_vieta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['vieta']=update.message.text; await update.message.reply_text("📞 7/7 - Kontaktas"); return KONTAKTAS
async def gavo_kontakta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kontaktas']=update.message.text; d=context.user_data; laikini_skelbimai[update.effective_user.id]=d.copy()
    txt=f"✅ Peržiūra:\n\n📦 {d['pavadinimas']}\n🏷️ {d['kategorija']}\n💰 {d['kaina']}\n📍 {d['vieta']}\n📞 {d['kontaktas']}\n\n📝 {d['aprasymas']}\n"
    kb=[[InlineKeyboardButton("✅ TAIP, skelbti!",callback_data="patvirtinti")]]
    if d.get('foto'): await update.message.reply_photo(photo=d['foto'],caption=txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
    else: await update.message.reply_text(txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
    return PATVIRTINIMAS
async def patvirtinti_skelbima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); data=laikini_skelbimai.get(q.from_user.id) or context.user_data
    txt=f"💛 **{data['pavadinimas']}**\n\n🏷️ {data['kategorija']}\n💰 {data['kaina']}\n📍 {data['vieta']}\n📞 {data['kontaktas']}\n\n📝 {data['aprasymas']}\n\n#vilnius #auksesturgus #aukses"
    try:
        if data.get('foto'): await context.bot.send_photo(chat_id=CHANNEL_ID,photo=data['foto'],caption=txt,parse_mode="Markdown")
        else: await context.bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        await q.message.reply_text(f"🚀 Paskelbta į {CHANNEL_ID}!")
    except Exception as e: await q.message.reply_text(f"❌ Klaida: {e}\nAr botas adminas kanale {CHANNEL_ID}?")
    laikini_skelbimai.pop(q.from_user.id,None); context.user_data.clear(); return ConversationHandler.END
async def taisykles(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("📜 Taisyklės: nuo adatos iki šaldytuvo! 💛")
def run_bot():
    if not BOT_TOKEN: print("❌ Nėra TOKEN - įdėk Render Environment"); return
    print("💛 Auksės turgus startuoja...")
    app=Application.builder().token(BOT_TOKEN).build()
    conv=ConversationHandler(entry_points=[CommandHandler("ideti",ideti_start),CallbackQueryHandler(ideti_start,pattern="^ideti$")],states={FOTO:[MessageHandler(filters.PHOTO|filters.TEXT & ~filters.COMMAND,gavo_foto)],PAVADINIMAS:[MessageHandler(filters.TEXT & ~filters.COMMAND,gavo_pavadinima)],KATEGORIJA:[CallbackQueryHandler(gavo_kategorija,pattern="^kat_")],KAINA:[MessageHandler(filters.TEXT & ~filters.COMMAND,gavo_kaina)],APRASYMAS:[MessageHandler(filters.TEXT & ~filters.COMMAND,gavo_aprasyma)],VIETA:[MessageHandler(filters.TEXT & ~filters.COMMAND,gavo_vieta)],KONTAKTAS:[MessageHandler(filters.TEXT & ~filters.COMMAND,gavo_kontakta)],PATVIRTINIMAS:[CallbackQueryHandler(patvirtinti_skelbima,pattern="^patvirtinti$"),CallbackQueryHandler(ideti_start,pattern="^ideti$")]},fallbacks=[CommandHandler("start",start),CommandHandler("ideti",ideti_start)])
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("taisykles",taisykles)); app.add_handler(conv); app.add_handler(CallbackQueryHandler(patvirtinti_skelbima,pattern="^patvirtinti$")); print("✅ Botas veikia!"); app.run_polling()
flask_app=Flask(__name__)
@flask_app.route('/')
def home(): return "💛 Vilniaus Auksės Turgus veikia!"
if
