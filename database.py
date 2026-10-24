import json
import os
import secrets
import threading
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
PORT = int(os.environ.get("PORT", "5000"))

if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("XATO: .env faylida BOT_TOKEN yoki DATABASE_URL topilmadi!")

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
        return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except Exception as e:
        if "channel_binding" in DATABASE_URL:
            fallback_url = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?")
            try:
                return psycopg2.connect(fallback_url, connect_timeout=5)
            except Exception as e2:
                print(f"⚠️ Neon DB ulanish xatosi: {e2}")
                return None
        print(f"⚠️ Neon DB ulanish xatosi: {e}")
        return None


_memory_chat_ids = set()
_memory_otp = {}
_memory_sessions = {}
_memory_custom_cars = []


def init_db():
    """Neon PostgreSQL bazasida jadvallarni avtomatik yaratish"""
    conn = get_db_connection()
    if not conn:
        print("⚠️ psycopg2 o'rnatilmagan yoki bazaga ulanib bo'lmadi. Lokal xotira ishlatiladi.")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    chat_id VARCHAR(64) PRIMARY KEY,
                    first_name VARCHAR(255),
                    username VARCHAR(255),
                    phone VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS custom_cars (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(64) NOT NULL,
                    tag VARCHAR(64) NOT NULL,
                    price VARCHAR(64) NOT NULL,
                    year VARCHAR(32) NOT NULL,
                    km VARCHAR(64) NOT NULL,
                    fuel VARCHAR(128) NOT NULL,
                    gear VARCHAR(64) NOT NULL,
                    img TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("SELECT chat_id FROM telegram_users;")
            for row in cur.fetchall():
                _memory_chat_ids.add(str(row[0]))

        conn.commit()
        print("✅ Neon PostgreSQL bazasi muvaffaqiyatli ulandi va jadvallar tayyor!")
        return True
    except Exception as e:
        print(f"⚠️ Neon DB jadvallarni yaratishda xatolik: {e}")
        return False
    finally:
        conn.close()


def save_telegram_user(chat_id, first_name="", username="", phone=""):
    _memory_chat_ids.add(str(chat_id))

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

    def _bg_save():
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

    threading.Thread(target=_bg_save, daemon=True).start()


def get_all_telegram_chat_ids():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in data.keys():
                    _memory_chat_ids.add(str(k))
        except Exception:
            pass

    if not _memory_chat_ids:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT chat_id FROM telegram_users;")
                    for row in cur.fetchall():
                        _memory_chat_ids.add(str(row[0]))
            except Exception as e:
                print(f"DB get_all_telegram_chat_ids xatosi: {e}")
            finally:
                conn.close()

    return list(_memory_chat_ids)


def save_otp_code(phone, name, code, telegram_id="", ttl_seconds=300):
    expires_at = time.time() + ttl_seconds
    _memory_otp[phone] = {
        "phone": phone,
        "name": name,
        "code": str(code).strip(),
        "telegram_id": telegram_id,
        "attempts": 0,
        "expires_at": expires_at,
    }


def verify_otp_code(phone, code):
    record = _memory_otp.get(phone)
    if not record:
        return False, "Avval tasdiqlash kodini so'rang!", None
    if str(record["code"]).strip() != str(code).strip():
        return False, "Kiritilgan kod noto'g'ri!", None

    session_token = secrets.token_hex(32)
    user_info = {
        "name": record["name"],
        "phone": record["phone"],
        "telegram_id": record.get("telegram_id") or "",
        "session_token": session_token,
    }
    save_registered_site_user(user_info["name"], user_info["phone"], user_info["telegram_id"], session_token)
    _memory_otp.pop(phone, None)
    return True, "Muvaffaqiyatli ro'yxatdan o'tdingiz!", user_info


def save_registered_site_user(name, phone, telegram_id="", session_token=""):
    _memory_sessions[session_token] = {
        "name": name,
        "phone": phone,
        "telegram_id": telegram_id,
    }

    def _bg():
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

    threading.Thread(target=_bg, daemon=True).start()


def verify_session_token(session_token):
    if not session_token:
        return None
    if session_token in _memory_sessions:
        return _memory_sessions[session_token]

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
                    user_dict = dict(row)
                    _memory_sessions[session_token] = user_dict
                    return user_dict
        except Exception:
            pass
        finally:
            conn.close()
    return None


def save_car_order(car_name, car_price, user_name, user_phone):
    def _bg():
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

    threading.Thread(target=_bg, daemon=True).start()


# ==========================================
# ADMIN TOMONIDAN QO'SHILGAN MASHINALAR (NEON DB)
# ==========================================
def get_custom_cars():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, category, tag, price, year, km, fuel, gear, img FROM custom_cars ORDER BY id DESC;")
                rows = [dict(r) for r in cur.fetchall()]
                return rows
        except Exception as e:
            print(f"DB get_custom_cars xatosi: {e}")
        finally:
            conn.close()
    return list(_memory_custom_cars)


def add_custom_car(car_data):
    new_car = {
        "id": int(time.time() * 1000),
        "name": car_data.get("name", ""),
        "category": car_data.get("category", "chevrolet"),
        "tag": car_data.get("tag", "Yangi"),
        "price": car_data.get("price", "$0"),
        "year": car_data.get("year", "2025"),
        "km": car_data.get("km", "0 km"),
        "fuel": car_data.get("fuel", "Benzin"),
        "gear": car_data.get("gear", "Avtomat"),
        "img": car_data.get("img", ""),
    }
    _memory_custom_cars.insert(0, new_car)

    def _bg():
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO custom_cars (name, category, tag, price, year, km, fuel, gear, img)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        new_car["name"],
                        new_car["category"],
                        new_car["tag"],
                        new_car["price"],
                        new_car["year"],
                        new_car["km"],
                        new_car["fuel"],
                        new_car["gear"],
                        new_car["img"],
                    ),
                )
            conn.commit()
        except Exception as e:
            print(f"DB add_custom_car xatosi: {e}")
        finally:
            conn.close()

    threading.Thread(target=_bg, daemon=True).start()
    return new_car


def delete_custom_car(car_id):
    global _memory_custom_cars
    _memory_custom_cars = [c for c in _memory_custom_cars if str(c.get("id")) != str(car_id)]

    def _bg():
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM custom_cars WHERE id = %s;", (int(car_id),))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    threading.Thread(target=_bg, daemon=True).start()
