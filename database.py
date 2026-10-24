import json
import os
import secrets
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def load_env_file():
    """python-dotenv o'rnatilgan bo'lsa undan, bo'lmasa o'zimiz .env faylni o'qiymiz"""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        pass

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_env_file()

# Maxfiy kalitlar faqat .env faylidan olinadi (kod ichida ochiq yozilmaydi)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
PORT = int(os.environ.get("PORT", "5000"))

if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("XATO: .env faylida BOT_TOKEN yoki DATABASE_URL topilmadi!")

# psycopg2 kutubxonasini tekshirish
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def get_db_connection():
    """Neon PostgreSQL bazasiga ulanish"""
    if not HAS_PSYCOPG2:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        if "channel_binding" in DATABASE_URL:
            fallback_url = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?")
            try:
                return psycopg2.connect(fallback_url)
            except Exception as e2:
                print(f"⚠️ Neon DB ulanish xatosi: {e2}")
                return None
        print(f"⚠️ Neon DB ulanish xatosi: {e}")
        return None


def init_db():
    """Neon PostgreSQL bazasida jadvallarni avtomatik yaratish"""
    conn = get_db_connection()
    if not conn:
        print("⚠️ psycopg2 o'rnatilmagan yoki bazaga ulanib bo'lmadi. Lokal xotira ishlatiladi.")
        print("👉 Neon bazani to'liq ishlatish uchun: pip install -r requirements.txt")
        return False

    try:
        with conn.cursor() as cur:
            # 1. Telegram botga /start bosgan foydalanuvchilar jadvali
            cur.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    chat_id VARCHAR(64) PRIMARY KEY,
                    first_name VARCHAR(255),
                    username VARCHAR(255),
                    phone VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Tasdiqlash kodlari (OTP) jadvali (attempts bilan brute-force himoyasi)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS otp_codes (
                    phone VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    code VARCHAR(16) NOT NULL,
                    telegram_id VARCHAR(64),
                    attempts INTEGER DEFAULT 0,
                    expires_at DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;")

            # 3. Saytda ro'yxatdan o'tgan foydalanuvchilar va xavfsiz sessiya tokenlari
            cur.execute("""
                CREATE TABLE IF NOT EXISTS site_users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    phone VARCHAR(64) UNIQUE NOT NULL,
                    telegram_id VARCHAR(64),
                    session_token VARCHAR(128),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("ALTER TABLE site_users ADD COLUMN IF NOT EXISTS session_token VARCHAR(128);")

            # 4. Mashina buyurtmalari jadvali
            cur.execute("""
                CREATE TABLE IF NOT EXISTS car_orders (
                    id SERIAL PRIMARY KEY,
                    car_name VARCHAR(255) NOT NULL,
                    car_price VARCHAR(64) NOT NULL,
                    user_name VARCHAR(255) NOT NULL,
                    user_phone VARCHAR(64) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        print("✅ Neon PostgreSQL bazasi muvaffaqiyatli ulandi va xavfsizlik jadvallari tayyor!")
        return True
    except Exception as e:
        print(f"⚠️ Neon DB jadvallarni yaratishda xatolik: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# TELEGRAM FOYDALANUVCHILAR BILAN ISHLASH
# ==========================================
def save_telegram_user(chat_id, first_name="", username="", phone=""):
    users = {}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = {}
    users[str(chat_id)] = {
        "chat_id": str(chat_id),
        "first_name": first_name,
        "username": username,
        "phone": phone,
    }
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO telegram_users (chat_id, first_name, username, phone)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE
                SET first_name = EXCLUDED.first_name,
                    username = EXCLUDED.username;
                """,
                (str(chat_id), first_name, username, phone),
            )
        conn.commit()
    except Exception as e:
        print(f"DB save_telegram_user xatosi: {e}")
    finally:
        conn.close()


def get_all_telegram_chat_ids():
    chat_ids = set()

    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in data.keys():
                    chat_ids.add(str(k))
        except Exception:
            pass

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT chat_id FROM telegram_users;")
                for row in cur.fetchall():
                    chat_ids.add(str(row[0]))
        except Exception as e:
            print(f"DB get_all_telegram_chat_ids xatosi: {e}")
        finally:
            conn.close()

    return list(chat_ids)


# ==========================================
# OTP TASDIQLASH VA SESSIYA XAVFSIZLIGI
# ==========================================
_memory_otp = {}
_memory_sessions = {}


def save_otp_code(phone, name, code, telegram_id="", ttl_seconds=300):
    expires_at = time.time() + ttl_seconds
    _memory_otp[phone] = {
        "phone": phone,
        "name": name,
        "code": code,
        "telegram_id": telegram_id,
        "attempts": 0,
        "expires_at": expires_at,
    }

    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO otp_codes (phone, name, code, telegram_id, attempts, expires_at)
                VALUES (%s, %s, %s, %s, 0, %s)
                ON CONFLICT (phone) DO UPDATE
                SET name = EXCLUDED.name,
                    code = EXCLUDED.code,
                    telegram_id = EXCLUDED.telegram_id,
                    attempts = 0,
                    expires_at = EXCLUDED.expires_at,
                    created_at = CURRENT_TIMESTAMP;
                """,
                (phone, name, code, telegram_id, expires_at),
            )
        conn.commit()
    except Exception as e:
        print(f"DB save_otp_code xatosi: {e}")
    finally:
        conn.close()


def verify_otp_code(phone, code):
    """
    Kodni Neon DB dan tekshiradi (maksimal 5 ta xato urinishdan so'ng bloklanadi).
    To'g'ri bo'lsa kriptografik session_token qaytaradi.
    """
    record = None

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM otp_codes WHERE phone = %s;", (phone,))
                row = cur.fetchone()
                if row:
                    record = dict(row)
        except Exception as e:
            print(f"DB verify_otp_code xatosi: {e}")
        finally:
            conn.close()

    if not record:
        record = _memory_otp.get(phone)

    if not record:
        return False, "Avval tasdiqlash kodini so'rang!", None

    if time.time() > float(record["expires_at"]):
        delete_otp_code(phone)
        return False, "Kodning amal qilish muddati tugagan. Qaytadan kod oling!", None

    attempts = int(record.get("attempts") or 0)
    if attempts >= 5:
        delete_otp_code(phone)
        return False, "Xavfsizlik: 5 marta xato kod kiritildi! Qaytadan yangi kod oling.", None

    if str(record["code"]).strip() != str(code).strip():
        increment_otp_attempts(phone, attempts + 1)
        left = 5 - (attempts + 1)
        return False, f"Kiritilgan kod noto'g'ri! (Qolgan urinishlar: {left} ta)", None

    # Kod to'g'ri -> Kriptografik xavfsiz session_token yaratamiz
    session_token = secrets.token_hex(32)
    user_info = {
        "name": record["name"],
        "phone": record["phone"],
        "telegram_id": record.get("telegram_id") or "",
        "session_token": session_token,
    }
    save_registered_site_user(
        user_info["name"],
        user_info["phone"],
        user_info["telegram_id"],
        session_token,
    )
    delete_otp_code(phone)

    return True, "Muvaffaqiyatli ro'yxatdan o'tdingiz!", user_info


def increment_otp_attempts(phone, new_attempts):
    if phone in _memory_otp:
        _memory_otp[phone]["attempts"] = new_attempts
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE otp_codes SET attempts = %s WHERE phone = %s;", (new_attempts, phone))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def delete_otp_code(phone):
    _memory_otp.pop(phone, None)
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM otp_codes WHERE phone = %s;", (phone,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def save_registered_site_user(name, phone, telegram_id="", session_token=""):
    _memory_sessions[session_token] = {
        "name": name,
        "phone": phone,
        "telegram_id": telegram_id,
    }
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO site_users (name, phone, telegram_id, session_token)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone) DO UPDATE
                SET name = EXCLUDED.name,
                    telegram_id = EXCLUDED.telegram_id,
                    session_token = EXCLUDED.session_token;
                """,
                (name, phone, telegram_id, session_token),
            )
        conn.commit()
    except Exception as e:
        print(f"DB save_registered_site_user xatosi: {e}")
    finally:
        conn.close()


def verify_session_token(session_token):
    """Brauzerdagi sessiya tokenini haqiqiyligini Neon DB orqali tekshirish"""
    if not session_token:
        return None

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT name, phone, telegram_id FROM site_users WHERE session_token = %s;",
                    (session_token,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            print(f"DB verify_session_token xatosi: {e}")
        finally:
            conn.close()

    return _memory_sessions.get(session_token)


def save_car_order(car_name, car_price, user_name, user_phone):
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO car_orders (car_name, car_price, user_name, user_phone)
                VALUES (%s, %s, %s, %s);
                """,
                (car_name, car_price, user_name, user_phone),
            )
        conn.commit()
    except Exception as e:
        print(f"DB save_car_order xatosi: {e}")
    finally:
        conn.close()
