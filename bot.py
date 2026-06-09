import os
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATA_FILE = "talabalar.json"
JAMI = 600000

def load():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fmt(n):
    return f"{int(n):,}".replace(",", " ")

def qarz(t):
    return max(0, JAMI - t)

# /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return
    await show_menu(update)

async def show_menu(update: Update):
    kb = [
        [InlineKeyboardButton("📋 Talabalar ro'yxati", callback_data="list")],
        [InlineKeyboardButton("➕ Talaba qo'shish", callback_data="add")],
        [InlineKeyboardButton("📢 Qarz xabar yuborish", callback_data="send_all")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    text = "👋 *Uniline Logistics — Undruv bo'limi*\n\nNimani qilmoqchisiz?"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data_cb = q.data
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await q.edit_message_text("⛔ Ruxsat yo'q.")
        return

    talabalar = load()

    if data_cb == "list":
        if not talabalar:
            await q.edit_message_text("📭 Talabalar yo'q.\n\n/menu — orqaga", parse_mode="Markdown")
            return
        text = "📋 *Talabalar ro'yxati:*\n\n"
        for i, t in enumerate(talabalar, 1):
            q_sum = qarz(t["tolangan"])
            holat = "✅ To'liq" if q_sum == 0 else f"⚠️ Qarz: {fmt(q_sum)} so'm"
            text += f"{i}. *{t['ism']}*\n📞 {t['tel']}\n💳 {holat}\n"
            if t.get("sana") and q_sum > 0:
                text += f"📅 Muddat: {t['sana']}\n"
            text += "\n"
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data_cb == "stats":
        full = sum(1 for t in talabalar if qarz(t["tolangan"]) == 0)
        qarzli = sum(1 for t in talabalar if qarz(t["tolangan"]) > 0)
        total_qarz = sum(qarz(t["tolangan"]) for t in talabalar)
        today = datetime.now().strftime("%Y-%m-%d")
        late = sum(1 for t in talabalar if qarz(t["tolangan"]) > 0 and t.get("sana", "") < today and t.get("sana", ""))
        text = (
            f"📊 *Statistika*\n\n"
            f"👥 Jami talabalar: *{len(talabalar)}*\n"
            f"✅ To'liq to'lagan: *{full}*\n"
            f"⚠️ Qarzli: *{qarzli}*\n"
            f"💰 Umumiy qarz: *{fmt(total_qarz)} so'm*\n"
            f"🔴 Muddati o'tgan: *{late}*"
        )
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data_cb == "send_all":
        qarzlilar = [t for t in talabalar if qarz(t["tolangan"]) > 0 and t.get("telegram_id")]
        if not qarzlilar:
            await q.edit_message_text(
                "📭 Qarzli talabalar yo'q yoki ularning Telegram ID si yo'q.\n\n"
                "Talabani qo'shishda Telegram ID ham kiriting.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]),
                parse_mode="Markdown"
            )
            return
        sent = 0
        for t in qarzlilar:
            q_sum = qarz(t["tolangan"])
            msg = (
                f"Assalomu alaykum, *{t['ism']}*!\n\n"
                f"📚 Uniline Logistics o'quv markazi\n\n"
                f"💳 Kurs narxi: *{fmt(JAMI)} so'm*\n"
                f"✅ To'langan: *{fmt(t['tolangan'])} so'm*\n"
                f"⚠️ Qolgan qarz: *{fmt(q_sum)} so'm*\n"
            )
            if t.get("sana"):
                msg += f"📅 To'lov muddati: *{t['sana']}*\n"
            msg += "\nIltimos, qarzingizni belgilangan muddatda to'lang.\n📞 Ma'lumot uchun: +998 XX XXX XX XX"
            try:
                await ctx.bot.send_message(chat_id=t["telegram_id"], text=msg, parse_mode="Markdown")
                sent += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                pass
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]
        await q.edit_message_text(
            f"✅ *{sent}* ta talabaga xabar yuborildi!",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )

    elif data_cb == "add":
        ctx.user_data["adding"] = {"step": "ism"}
        kb = [[InlineKeyboardButton("❌ Bekor qilish", callback_data="menu")]]
        await q.edit_message_text(
            "➕ *Yangi talaba qo'shish*\n\nIsm familiyasini yozing:",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )

    elif data_cb == "menu":
        await show_menu(update)

    elif data_cb.startswith("del_"):
        tid = int(data_cb.split("_")[1])
        talabalar = [t for t in talabalar if t["id"] != tid]
        save(talabalar)
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="list")]]
        await q.edit_message_text("🗑 Talaba o'chirildi.", reply_markup=InlineKeyboardMarkup(kb))

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    adding = ctx.user_data.get("adding")
    if not adding:
        await update.message.reply_text("Menyu uchun /menu yozing.")
        return

    text = update.message.text.strip()
    step = adding["step"]

    if step == "ism":
        adding["ism"] = text
        adding["step"] = "tel"
        await update.message.reply_text("📞 Telefon raqamini yozing:\n(masalan: +998 90 123 45 67)")

    elif step == "tel":
        adding["tel"] = text
        adding["step"] = "tolangan"
        await update.message.reply_text(f"💳 To'langan summani yozing (so'm):\nKurs narxi: {fmt(JAMI)} so'm")

    elif step == "tolangan":
        try:
            tolangan = int(text.replace(" ", "").replace(",", ""))
        except:
            await update.message.reply_text("❌ Raqam kiriting! Masalan: 300000")
            return
        adding["tolangan"] = tolangan
        q_sum = qarz(tolangan)
        if q_sum > 0:
            adding["step"] = "sana"
            await update.message.reply_text(
                f"⚠️ Qarz: {fmt(q_sum)} so'm\n\n📅 To'lov muddatini yozing:\n(masalan: 2026-07-15)"
            )
        else:
            adding["sana"] = ""
            adding["step"] = "telegram_id"
            await update.message.reply_text(
                "✅ To'liq to'langan!\n\n📱 Talabaning Telegram ID sini yozing:\n(bilmasangiz 0 yozing)\n\nID olish uchun talaba @userinfobot ga /start yuborsun."
            )

    elif step == "sana":
        adding["sana"] = text
        adding["step"] = "telegram_id"
        await update.message.reply_text(
            "📱 Talabaning Telegram ID sini yozing:\n(bilmasangiz 0 yozing)\n\nID olish uchun talaba @userinfobot ga /start yuborsun."
        )

    elif step == "telegram_id":
        try:
            tg_id = int(text.replace(" ", ""))
        except:
            tg_id = 0
        adding["telegram_id"] = tg_id if tg_id != 0 else None

        talabalar = load()
        new_id = max((t["id"] for t in talabalar), default=0) + 1
        talabalar.append({
            "id": new_id,
            "ism": adding["ism"],
            "tel": adding["tel"],
            "tolangan": adding["tolangan"],
            "sana": adding.get("sana", ""),
            "telegram_id": adding.get("telegram_id")
        })
        save(talabalar)
        ctx.user_data.pop("adding", None)

        q_sum = qarz(adding["tolangan"])
        holat = "✅ To'liq to'lagan" if q_sum == 0 else f"⚠️ Qarz: {fmt(q_sum)} so'm"
        kb = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")]]
        await update.message.reply_text(
            f"✅ *{adding['ism']}* qo'shildi!\n\n{holat}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )

async def menu_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await show_menu(update)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
