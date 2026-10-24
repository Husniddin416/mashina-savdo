import json
import os
import random
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import telebot
from telebot import types

from database import (
    BASE_DIR,
    BOT_TOKEN,
    PORT,
    get_all_telegram_chat_ids,
    init_db,
    save_car_order,
    save_otp_code,
    save_telegram_user,
    verify_otp_code,
    verify_session_token,
)

bot = telebot.TeleBot(BOT_TOKEN)
bot_info_cache = {"username": "", "first_name": "Mashina Bot"}

# Brauzerdan faqat ruxsat etilgan frontend fayllargina ochiladi (.env va .py fayllar bloklanadi!)
ALLOWED_PUBLIC_FILES = {"/", "/index.html", "/style.css", "/script.js", "/favicon.ico"}


# ==========================================
# TELEGRAM BOT HANDLERLARI
# ==========================================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    chat_id = message.chat.id
    save_telegram_user(
        chat_id=chat_id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username or "",
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_id = types.KeyboardButton("🆔 Mening ID raqamim")
    btn_site = types.KeyboardButton("🌐 Sayt haqida")
    markup.add(btn_id, btn_site)

    bot.send_message(
        chat_id,
        f"Assalomu alaykum, <b>{message.from_user.first_name}</b>! 🚗\n\n"
        f"✅ Sizning Telegram hisobingiz <b>AutoUz (Neon PostgreSQL)</b> bazasiga ulandi!\n"
        f"🆔 Sizning Telegram ID: <code>{chat_id}</code>\n\n"
        f"Endi saytdagi <b>Ro'yxatdan o'tish</b> bo'limida <i>«Kod yuborish»</i> tugmasini bossangiz, "
        f"tasdiqlash kodi shu yerga keladi!",
        parse_mode="HTML",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    save_telegram_user(
        chat_id=chat_id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username or "",
    )

    if message.text == "🆔 Mening ID raqamim":
        bot.send_message(
            chat_id,
            f"🆔 Sizning Telegram ID raqamingiz:\n<code>{chat_id}</code>\n\n"
            f"Saytda ro'yxatdan o'tayotganda ushbu ID ni kiritishingiz yoki bo'sh qoldirishingiz mumkin.",
            parse_mode="HTML",
        )
    elif message.text == "🌐 Sayt haqida":
        bot.send_message(
            chat_id,
            f"🚗 <b>AutoUz — Zamonaviy Mashinalar Savdosi</b>\n\n"
            f"🌐 Sayt manzili: http://127.0.0.1:{PORT}\n"
            f"🗄 Ma'lumotlar bazasi: <b>Neon PostgreSQL</b>\n"
            f"Ro'yxatdan o'tish kodlari va mashina buyurtmalari shu bot va Neon bazasi orqali qabul qilinadi.",
            parse_mode="HTML",
        )
    else:
        bot.send_message(
            chat_id,
            f"✅ Xabaringiz qabul qilindi! Sizning Telegram ID: <code>{chat_id}</code>",
            parse_mode="HTML",
        )


def send_otp_to_telegram(name, phone, code, target_chat_id=None):
    """Tasdiqlash kodini Telegram botga yuborish"""
    chat_ids = get_all_telegram_chat_ids()
    text = (
        f"🔐 <b>AUTO-UZ: Ro'yxatdan o'tish kodi!</b>\n\n"
        f"👤 <b>Ism:</b> {name}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"🔑 <b>Tasdiqlash kodi:</b> <code>{code}</code>\n\n"
        f"<i>Ushbu 6 xonali kodni saytdagi ro'yxatdan o'tish oynasiga kiriting.</i>"
    )

    sent_count = 0

    if target_chat_id and str(target_chat_id).strip():
        try:
            bot.send_message(str(target_chat_id).strip(), text, parse_mode="HTML")
            sent_count += 1
        except Exception as e:
            print(f"Aniq chat_id ({target_chat_id}) ga yuborishda xatolik: {e}")

    if sent_count == 0:
        for cid in chat_ids:
            try:
                bot.send_message(cid, text, parse_mode="HTML")
                sent_count += 1
            except Exception as e:
                print(f"Chat {cid} ga yuborishda xatolik: {e}")

    return sent_count


def send_notification_to_telegram(text, target_chat_id=None):
    """Muvaffaqiyatli ro'yxatdan o'tish yoki buyurtma haqida xabar yuborish"""
    chat_ids = get_all_telegram_chat_ids()
    sent = 0
    if target_chat_id and str(target_chat_id).strip():
        try:
            bot.send_message(str(target_chat_id).strip(), text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    if sent == 0:
        for cid in chat_ids:
            try:
                bot.send_message(cid, text, parse_mode="HTML")
            except Exception:
                pass


# ==========================================
# XAVFSIZ WEB SERVER VA BACKEND API HANDLER
# ==========================================
class MashinaRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        clean_path = self.path.split("?")[0]
        if clean_path == "/api/bot-info":
            chat_ids = get_all_telegram_chat_ids()
            self.send_json(
                {
                    "ok": True,
                    "username": bot_info_cache.get("username", ""),
                    "first_name": bot_info_cache.get("first_name", "Mashina Bot"),
                    "connected_users": len(chat_ids),
                }
            )
            return

        # XAVFSIZLIK: .env, .py, .json kabi maxfiy fayllarni brauzerdan o'qishni qat'iyan taqiqlaymiz!
        if clean_path not in ALLOWED_PUBLIC_FILES:
            self.send_json({"ok": False, "message": "Ruxsat yo'q (403 Forbidden)"}, 403)
            return

        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        # 1. Ro'yxatdan o'tish uchun kod yuborish
        if self.path == "/api/send-code":
            name = body.get("name", "").strip()
            phone = body.get("phone", "").strip()
            telegram_id = body.get("telegram_id", "").strip()

            if not name or not phone:
                self.send_json(
                    {"ok": False, "message": "Iltimos, ismingiz va telefon raqamingizni kiriting!"},
                    400,
                )
                return

            code = str(random.randint(100000, 999999))
            save_otp_code(phone=phone, name=name, code=code, telegram_id=telegram_id, ttl_seconds=300)

            sent_count = send_otp_to_telegram(name, phone, code, telegram_id)

            if sent_count == 0:
                bot_username = bot_info_cache.get("username", "")
                bot_link = f"@{bot_username}" if bot_username else "Telegram botimiz"
                self.send_json(
                    {
                        "ok": False,
                        "need_start": True,
                        "message": f"Avval Telegramda {bot_link} ga kirib /start tugmasini bosing, so'ngra qayta urinib ko'ring!",
                    },
                    400,
                )
                return

            self.send_json(
                {
                    "ok": True,
                    "message": "Tasdiqlash kodi Telegram botga yuborildi!",
                }
            )
            return

        # 2. Kodni Neon DB orqali tekshirish va kriptografik session_token berish
        if self.path == "/api/verify-code":
            phone = body.get("phone", "").strip()
            code = body.get("code", "").strip()

            ok, message, user_info = verify_otp_code(phone, code)
            if not ok:
                self.send_json({"ok": False, "message": message}, 400)
                return

            send_notification_to_telegram(
                f"✅ <b>Yangi foydalanuvchi ro'yxatdan o'tdi (Neon DB)!</b>\n\n"
                f"👤 <b>Ism:</b> {user_info['name']}\n"
                f"📞 <b>Telefon:</b> {user_info['phone']}\n"
                f"🎉 Saytga muvaffaqiyatli kirdi!",
                user_info["telegram_id"],
            )

            self.send_json(
                {
                    "ok": True,
                    "message": message,
                    "user": user_info,
                }
            )
            return

        # 3. Brauzerdagi sessiya tokenini Neon DB orqali haqiqiyligini tekshirish
        if self.path == "/api/check-session":
            session_token = body.get("session_token", "").strip()
            user = verify_session_token(session_token)
            if not user:
                self.send_json({"ok": False, "message": "Sessiya yaroqsiz"}, 401)
                return
            self.send_json({"ok": True, "user": user})
            return

        # 4. Mashina buyurtma qilish (faqat haqiqiy session_token egalariga ruxsat)
        if self.path == "/api/order":
            session_token = body.get("session_token", "").strip()
            verified_user = verify_session_token(session_token)
            if not verified_user:
                self.send_json({"ok": False, "message": "Avval ro'yxatdan o'ting!"}, 401)
                return

            car_name = body.get("car_name", "")
            car_price = body.get("car_price", "")
            user_name = verified_user["name"]
            user_phone = verified_user["phone"]

            save_car_order(car_name, car_price, user_name, user_phone)

            send_notification_to_telegram(
                f"🚘 <b>YANGI MASHINA BUYURTMASI (Neon DB)!</b>\n\n"
                f"🚗 <b>Model:</b> {car_name}\n"
                f"💰 <b>Narxi:</b> {car_price}\n"
                f"👤 <b>Xaridor:</b> {user_name}\n"
                f"📞 <b>Telefon:</b> {user_phone}"
            )
            self.send_json({"ok": True, "message": "Arizangiz Neon bazasiga saqlandi va Telegram botga yuborildi!"})
            return

        self.send_json({"ok": False, "message": "Topilmadi"}, 404)


def run_web_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), MashinaRequestHandler)
    print(f"🌐 Backend va Sayt orqa fonda (background) ishga tushdi: http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    print("🔄 Neon PostgreSQL bazasi tekshirilmoqda...")
    init_db()

    try:
        me = bot.get_me()
        bot_info_cache["username"] = me.username or ""
        bot_info_cache["first_name"] = me.first_name or "Mashina Bot"
        print(f"🤖 Telegram Bot ulandi: @{bot_info_cache['username']} ({bot_info_cache['first_name']})")
    except Exception as e:
        print(f"⚠️ Bot ma'lumotlarini olishda xatolik: {e}")

    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()

    print("🚀 Bot va Backend xavfsiz rejimda ishlamoqda... (To'xtatish uchun Ctrl+C bosing)")
    bot.infinity_polling()
