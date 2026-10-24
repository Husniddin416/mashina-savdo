import json
import os
import random
import sys
from http.server import BaseHTTPRequestHandler
import telebot
from telebot import types

# Asosiy papkani Python yo'liga qo'shamiz (database.py ni topishi uchun)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import (
    BOT_TOKEN,
    get_all_telegram_chat_ids,
    init_db,
    save_car_order,
    save_otp_code,
    save_telegram_user,
    verify_otp_code,
    verify_session_token,
)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Jadval mavjudligini tekshirish
try:
    init_db()
except Exception as e:
    print("DB init warning:", e)


def send_otp_to_telegram(name, phone, code, target_chat_id=None):
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
        except Exception:
            pass

    if sent_count == 0:
        for cid in chat_ids:
            try:
                bot.send_message(cid, text, parse_mode="HTML")
                sent_count += 1
            except Exception:
                pass
    return sent_count


def send_notification_to_telegram(text, target_chat_id=None):
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


class handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_json({"ok": True})

    def do_GET(self):
        clean_path = self.path.split("?")[0]
        if clean_path == "/api/bot-info":
            username = ""
            first_name = "Mashina Bot"
            try:
                me = bot.get_me()
                username = me.username or ""
                first_name = me.first_name or "Mashina Bot"
            except Exception:
                pass

            # Agar Vercel'da bo'lsa, Telegram Webhook'ni avtomatik ulab qo'yamiz
            host = self.headers.get("Host", "")
            if host and "vercel.app" in host:
                try:
                    bot.set_webhook(url=f"https://{host}/api/webhook")
                except Exception:
                    pass

            chat_ids = get_all_telegram_chat_ids()
            self.send_json(
                {
                    "ok": True,
                    "username": username,
                    "first_name": first_name,
                    "connected_users": len(chat_ids),
                }
            )
            return

        self.send_json({"ok": True, "status": "Vercel Python API ishlamoqda"})

    def do_POST(self):
        clean_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        # Telegram Webhook (/start bosilganda Vercel'da qabul qilish)
        if clean_path == "/api/webhook":
            if "message" in body:
                msg = body["message"]
                chat = msg.get("chat", {})
                from_user = msg.get("from", {})
                chat_id = chat.get("id")
                text_in = msg.get("text", "")
                if chat_id:
                    save_telegram_user(
                        chat_id=chat_id,
                        first_name=from_user.get("first_name", ""),
                        username=from_user.get("username", ""),
                    )
                    if text_in.startswith("/start"):
                        try:
                            bot.send_message(
                                chat_id,
                                f"Assalomu alaykum, <b>{from_user.get('first_name', 'Foydalanuvchi')}</b>! 🚗\n\n"
                                f"✅ Sizning Telegram hisobingiz <b>AutoUz (Neon PostgreSQL)</b> bazasiga ulandi!\n"
                                f"🆔 Sizning Telegram ID: <code>{chat_id}</code>\n\n"
                                f"Endi saytdagi <b>Ro'yxatdan o'tish</b> bo'limida <i>«Kod yuborish»</i> tugmasini bossangiz, "
                                f"tasdiqlash kodi shu yerga keladi!",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
            self.send_json({"ok": True})
            return

        # 1. Kod yuborish
        if clean_path == "/api/send-code":
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
                self.send_json(
                    {
                        "ok": False,
                        "need_start": True,
                        "message": "Avval Telegram botga kirib /start tugmasini bosing (yoki Telegram ID raqamingizni kiriting), so'ngra qayta urinib ko'ring!",
                    },
                    400,
                )
                return

            self.send_json({"ok": True, "message": "Tasdiqlash kodi Telegram botga yuborildi!"})
            return

        # 2. Kodni tekshirish
        if clean_path == "/api/verify-code":
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
            self.send_json({"ok": True, "message": message, "user": user_info})
            return

        # 3. Sessiya tekshirish
        if clean_path == "/api/check-session":
            session_token = body.get("session_token", "").strip()
            user = verify_session_token(session_token)
            if not user:
                self.send_json({"ok": False, "message": "Sessiya yaroqsiz"}, 401)
                return
            self.send_json({"ok": True, "user": user})
            return

        # 4. Buyurtma
        if clean_path == "/api/order":
            session_token = body.get("session_token", "").strip()
            verified_user = verify_session_token(session_token)
            if not verified_user:
                self.send_json({"ok": False, "message": "Avval ro'yxatdan o'ting!"}, 401)
                return

            car_name = body.get("car_name", "")
            car_price = body.get("car_price", "")
            save_car_order(car_name, car_price, verified_user["name"], verified_user["phone"])

            send_notification_to_telegram(
                f"🚘 <b>YANGI MASHINA BUYURTMASI (Neon DB)!</b>\n\n"
                f"🚗 <b>Model:</b> {car_name}\n"
                f"💰 <b>Narxi:</b> {car_price}\n"
                f"👤 <b>Xaridor:</b> {verified_user['name']}\n"
                f"📞 <b>Telefon:</b> {verified_user['phone']}"
            )
            self.send_json({"ok": True, "message": "Arizangiz yuborildi!"})
            return

        self.send_json({"ok": False, "message": "Topilmadi"}, 404)
