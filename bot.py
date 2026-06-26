import os
import telebot
from telebot import types
import requests
from telebot import apihelper
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import base64
import json

import config
import calculator

# .env faylini yuklash
load_dotenv()

# SSL sertifikat xatolarini chetlab o'tish (agar kerak bo'lsa)
session = requests.Session()
session.verify = False
apihelper.session = session
apihelper.ENABLE_MIDDLEWARE = True

# Botni ishga tushirish
if not config.BOT_TOKEN:
    print("⚠️ DIQQAT: BOT_TOKEN .env faylida topilmadi. Iltimos bot tokenini kiriting.")

bot = telebot.TeleBot(config.BOT_TOKEN if config.BOT_TOKEN else "DUMMY_TOKEN")

# Foydalanuvchilar holati (kalkulyator va admin uchun)
user_states = {}

# DB va GitHub sozlamalari
DB_FILE = os.path.join(os.path.dirname(__file__), "bot_data.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization error: {e}")

init_db()

def log_user(message):
    try:
        user = message.from_user
        if not user:
            return
        chat_id = message.chat.id
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (chat_id,))
        exists = cursor.fetchone()
        if not exists:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO users (id, username, first_name, last_name, joined_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user.username, user.first_name, user.last_name, now_str)
            )
            conn.commit()
            print(f"🆕 Yangi foydalanuvchi qo'shildi: {user.first_name} (@{user.username or 'yoq'})")
        conn.close()
    except Exception as e:
        print(f"Foydalanuvchini log qilishda xato: {e}")

# Middleware to log users on every message
@bot.middleware_handler(update_types=['message'])
def log_incoming_message(bot_instance, message):
    log_user(message)

def is_admin(chat_id):
    # Check in config env first
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        try:
            admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            if chat_id in admin_ids:
                return True
        except ValueError:
            pass
            
    # Check SQLite admins table
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM admins WHERE id = ?", (chat_id,))
        exists = cursor.fetchone()
        conn.close()
        if exists:
            return True
    except Exception as e:
        print(f"Error checking admin in database: {e}")
    return False

def add_admin(chat_id, username=None):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM admins WHERE id = ?", (chat_id,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("INSERT INTO admins (id, username) VALUES (?, ?)", (chat_id, username))
            conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False

def get_statistics():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        # Today's date YYYY-MM-DD
        today_prefix = datetime.now().strftime("%Y-%m-%d") + "%"
        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (today_prefix,))
        today_users = cursor.fetchone()[0]
        conn.close()
        return f"📊 **Bot statistikasi:**\n\n👥 Jami foydalanuvchilar: **{total_users} ta**\n📅 Bugun qo'shilganlar: **{today_users} ta**"
    except Exception as e:
        return f"⚠️ Statistika olishda xatolik: {e}"

def send_users_list(chat_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, first_name, last_name, joined_at FROM users")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(chat_id, "Foydalanuvchilar topilmadi.")
            return
            
        data = []
        for u in users:
            data.append({
                "id": u[0],
                "username": u[1],
                "first_name": u[2],
                "last_name": u[3],
                "joined_at": u[4]
            })
            
        file_path = os.path.join(os.path.dirname(__file__), "users_backup.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        with open(file_path, "rb") as f:
            bot.send_document(chat_id, f, caption="📥 **Foydalanuvchilar ro'yxati (JSON formatda)**")
            
        try:
            os.remove(file_path)
        except Exception:
            pass
    except Exception as e:
        bot.send_message(chat_id, f"Foydalanuvchilar ro'yxatini yuklashda xatolik: {e}")

def sync_file_to_github(file_path, content_bytes, commit_msg):
    pat = config.GITHUB_PAT
    repo = config.GITHUB_REPO
    if not pat or not repo:
        print("⚠️ GITHUB_PAT yoki GITHUB_REPO sozlanmagan. GitHub'ga yuklab bo'lmadi.")
        return False
        
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Telegram-Bot-Syncer"
    }
    
    # 1. Get SHA if file exists
    r = requests.get(url, headers=headers, verify=False)
    sha = None
    if r.status_code == 200:
        sha = r.json().get("sha")
        
    # 2. Encode to base64
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    
    # 3. Put content
    payload = {
        "message": commit_msg,
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
        
    r_put = requests.put(url, headers=headers, json=payload, verify=False)
    if r_put.status_code in [200, 201]:
        print(f"✅ GitHub'ga yuklandi: {file_path}")
        return True
    else:
        print(f"❌ GitHub'ga yuklashda xato ({r_put.status_code}): {r_put.text}")
        return False

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_stats = types.KeyboardButton("📊 Statistika")
    btn_broadcast = types.KeyboardButton("📨 Xabar yuborish")
    btn_edit_cat = types.KeyboardButton("📂 Katalogni tahrirlash")
    btn_users = types.KeyboardButton("📥 Foydalanuvchilar ro'yxati")
    btn_exit = types.KeyboardButton("⬅️ Asosiy menyu")
    markup.add(btn_stats, btn_broadcast)
    markup.add(btn_edit_cat, btn_users)
    markup.add(btn_exit)
    return markup


# Rasmlar turgan papka
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")

# --- Tugmalar (Reply Keyboard) ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_calc = types.KeyboardButton("🧮 Aboy hisoblash")
    btn_catalog = types.KeyboardButton("📂 Katalog")
    btn_address = types.KeyboardButton("📍 Manzil")
    btn_contact = types.KeyboardButton("📞 Aloqa")
    markup.add(btn_calc, btn_catalog, btn_address, btn_contact)
    return markup

# --- Start buyrug'i ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)  # Holatni tozalash
    
    welcome_text = (
        "👋 **Salom! Aboy do'konimiz botiga xush kelibsiz!**\n\n"
        "Men sizga xonangiz uchun qancha aboy (gulqog'oz) kerakligini hisoblashda yordam beraman, "
        "shuningdek do'konimizdagi mahsulotlar katalogi, manzilimiz va kontaktlarimiz bilan tanishtira olaman.\n\n"
        "Boshlash uchun quyidagi tugmalardan birini bosing:"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# --- Help buyrug'i ---
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "🤖 **Botdan foydalanish yo'riqnomasi:**\n\n"
        "🧮 **Aboy hisoblash** — Xonangiz o'lchamlarini kiritasiz va bot sizga qancha aboy ruloni ketishini hisoblab beradi.\n"
        "📂 **Katalog** — Do'kondagi mavjud aboylar turlari va narxlari bilan tanishasiz.\n"
        "📍 **Manzil** — Do'konimiz joylashgan manzil va geografik lokatsiyasi.\n"
        "📞 **Aloqa** — Telefon raqamlarimiz va ish vaqtlarimiz.\n\n"
        "Agar kalkulyatorda adashib qolsangiz, shunchaki /start buyrug'ini yuboring."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# --- Admin auth va admin paneli handlerlari ---
@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    
    parts = message.text.split(maxsplit=1)
    password = parts[1].strip() if len(parts) > 1 else None
    
    if password and password == config.ADMIN_PASSWORD:
        add_admin(chat_id, message.from_user.username)
        bot.send_message(
            chat_id, 
            "✅ **Admin sifatida muvaffaqiyatli kirdingiz!**\n\nQuyidagi menyudan foydalaning:",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        return
        
    if is_admin(chat_id):
        bot.send_message(
            chat_id, 
            "👑 **Admin paneli**\n\nQuyidagi menyudan foydalaning:",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    else:
        bot.send_message(
            chat_id, 
            "⚠️ **Siz admin emassiz!**\n\nAdmin paneliga kirish uchun `/admin [parol]` shaklida yozing (masalan: `/admin stroy_admin_99`):",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Asosiy menyu" or msg.text == "/admin_exit")
def exit_admin_mode(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    bot.send_message(
        chat_id,
        "👋 Admin panelidan chiqdingiz. Asosiy menyuga qaytdik:",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "📊 Statistika")
def admin_stats(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        return
    stats_text = get_statistics()
    bot.send_message(chat_id, stats_text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📥 Foydalanuvchilar ro'yxati")
def admin_users_list(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        return
    send_users_list(chat_id)

@bot.message_handler(func=lambda msg: msg.text == "📨 Xabar yuborish")
def start_broadcast(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        return
    user_states[chat_id] = {'state': 'ADMIN_BROADCAST_MSG'}
    bot.send_message(
        chat_id,
        "📨 **Rassilka yuborish bo'limi**\n\nFoydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing yoki rasmli/videoli post yuboring (ko'chirib yuboriladi).\n\nBekor qilish uchun 'bekor qilish' deb yozing:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_BROADCAST_MSG', content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker'])
def handle_admin_broadcast(message):
    chat_id = message.chat.id
    if message.text and (message.text.lower() == 'bekor qilish' or message.text == '⬅️ Asosiy menyu'):
        bot.send_message(chat_id, "Rassilka bekor qilindi.", reply_markup=get_admin_keyboard())
        user_states.pop(chat_id, None)
        return
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        conn.close()
    except Exception as e:
        bot.send_message(chat_id, f"Foydalanuvchilarni olishda xatolik: {e}", reply_markup=get_admin_keyboard())
        user_states.pop(chat_id, None)
        return
        
    user_ids = [u[0] for u in users]
    if not user_ids:
        bot.send_message(chat_id, "Botda foydalanuvchilar mavjud emas.", reply_markup=get_admin_keyboard())
        user_states.pop(chat_id, None)
        return
        
    bot.send_message(chat_id, f"Rassilka boshlandi. Jami {len(user_ids)} ta foydalanuvchiga yuborilmoqda...", reply_markup=get_admin_keyboard())
    
    success = 0
    failed = 0
    for uid in user_ids:
        try:
            bot.copy_message(chat_id=uid, from_chat_id=chat_id, message_id=message.message_id)
            success += 1
        except Exception:
            failed += 1
            
    bot.send_message(chat_id, f"✅ **Rassilka yakunlandi!**\n\n👍 Muvaffaqiyatli yuborildi: {success}\n👎 Yuborilmadi (bloklanganlar): {failed}", parse_mode="Markdown")
    user_states.pop(chat_id, None)

@bot.message_handler(func=lambda msg: msg.text == "📂 Katalogni tahrirlash")
def edit_catalog_menu(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        return
    user_states.pop(chat_id, None)
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_add = types.InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="admin_prod_add")
    btn_del = types.InlineKeyboardButton(text="❌ Mahsulotni o'chirish", callback_data="admin_prod_del")
    markup.add(btn_add, btn_del)
    bot.send_message(chat_id, "📂 **Katalogni tahrirlash bo'limi:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot.answer_callback_query(call.id)
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "Siz admin emassiz.")
        return
        
    if call.data == "admin_prod_add":
        products_data = load_products()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for index, cat in enumerate(products_data):
            markup.add(types.InlineKeyboardButton(text=cat['category'], callback_data=f"admin_add_cat_select_{index}"))
        markup.add(types.InlineKeyboardButton(text="🆕 Yangi kategoriya yaratish", callback_data="admin_add_cat_new"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="➕ **Mahsulot qaysi kategoriyaga qo'shilsin?**\n\nKategoriyani tanlang:",
            reply_markup=markup
        )
        
    elif call.data == "admin_prod_del":
        products_data = load_products()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for index, cat in enumerate(products_data):
            markup.add(types.InlineKeyboardButton(text=cat['category'], callback_data=f"admin_del_cat_select_{index}"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ **Mahsulot o'chirish**\n\nQaysi kategoriyadan mahsulot o'chiramiz? Kategoriyani tanlang:",
            reply_markup=markup
        )
        
    elif call.data == "admin_add_cat_new":
        user_states[chat_id] = {'state': 'ADMIN_ADD_CAT_NEW_NAME', 'new_product': {}}
        bot.delete_message(chat_id, message_id)
        bot.send_message(chat_id, "📝 **Yangi kategoriya nomini kiriting:**", reply_markup=types.ReplyKeyboardRemove())
        
    elif call.data.startswith("admin_add_cat_select_"):
        cat_index = int(call.data.split('_')[4])
        products_data = load_products()
        if cat_index < len(products_data):
            cat_name = products_data[cat_index]['category']
            user_states[chat_id] = {
                'state': 'ADMIN_ADD_PROD_NAME', 
                'new_product': {'category': cat_name}
            }
            bot.delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                f"📂 Kategoriya: **{cat_name}**\n\n📝 **Mahsulot nomini kiriting:**", 
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
    elif call.data.startswith("admin_del_cat_select_"):
        cat_index = int(call.data.split('_')[4])
        products_data = load_products()
        if cat_index < len(products_data):
            cat = products_data[cat_index]
            markup = types.InlineKeyboardMarkup(row_width=1)
            for item in cat['items']:
                markup.add(types.InlineKeyboardButton(
                    text=f"{item['name']} - {format_price(item['priceValue'])}",
                    callback_data=f"admin_del_prod_select_{cat_index}_{item['id']}"
                ))
            markup.add(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_prod_del"))
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ **{cat['category']}** bo'limidan o'chirmoqchi bo'lgan mahsulotni tanlang:",
                reply_markup=markup
            )
            
    elif call.data.startswith("admin_del_prod_select_"):
        parts = call.data.split('_')
        cat_index = int(parts[4])
        item_id = '_'.join(parts[5:])
        
        products_data = load_products()
        if cat_index < len(products_data):
            cat = products_data[cat_index]
            item_to_delete = None
            for item in cat['items']:
                if item['id'] == item_id:
                    item_to_delete = item
                    break
                    
            if item_to_delete:
                cat['items'] = [item for item in cat['items'] if item['id'] != item_id]
                
                # Update local file
                file_path = os.path.join(os.path.dirname(__file__), 'products.json')
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(products_data, f, indent=2, ensure_ascii=False)
                    
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🔄 **{item_to_delete['name']}** o'chirilmoqda va GitHub'ga yuklanmoqda..."
                )
                
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
                success = sync_file_to_github('products.json', content_bytes, f"Delete product {item_to_delete['name']}")
                
                if success:
                    bot.send_message(
                        chat_id, 
                        f"✅ **{item_to_delete['name']}** muvaffaqiyatli o'chirildi va o'zgarishlar GitHub'ga yuklandi!\n\nRender 1-2 daqiqada botni qayta ishga tushiradi.",
                        reply_markup=get_admin_keyboard()
                    )
                else:
                    bot.send_message(
                        chat_id, 
                        f"⚠️ Mahsulot o'chirildi, lekin GitHub'ga yuklashda xatolik yuz berdi. Render'da yangilanmadi.",
                        reply_markup=get_admin_keyboard()
                    )

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_CAT_NEW_NAME')
def handle_admin_add_cat_new_name(message):
    chat_id = message.chat.id
    cat_name = message.text.strip()
    
    if not cat_name:
        bot.reply_to(message, "Kategoriya nomi bo'sh bo'lishi mumkin emas. Iltimos qaytadan kiriting:")
        return
        
    user_states[chat_id]['new_product']['category'] = cat_name
    user_states[chat_id]['state'] = 'ADMIN_ADD_PROD_NAME'
    bot.send_message(chat_id, f"📁 Yangi kategoriya: **{cat_name}**\n\n📝 Endi **mahsulot nomini** kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_PROD_NAME')
def handle_admin_add_prod_name(message):
    chat_id = message.chat.id
    prod_name = message.text.strip()
    
    if not prod_name:
        bot.reply_to(message, "Mahsulot nomi bo'sh bo'lishi mumkin emas. Qayta kiriting:")
        return
        
    user_states[chat_id]['new_product']['name'] = prod_name
    user_states[chat_id]['state'] = 'ADMIN_ADD_PROD_PRICE'
    bot.send_message(chat_id, f"📝 Mahsulot nomi: **{prod_name}**\n\n💰 Endi **narxini** kiriting (masalan, 35000):", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_PROD_PRICE')
def handle_admin_add_prod_price(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(" ", "").replace(",", "")
    
    try:
        price = int(text)
        if price < 0:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri narx. Iltimos faqat musbat son kiriting (masalan: 35000):")
        return
        
    user_states[chat_id]['new_product']['priceValue'] = price
    user_states[chat_id]['state'] = 'ADMIN_ADD_PROD_SIZE'
    bot.send_message(
        chat_id, 
        f"💰 Narxi: **{price:,} so'm**\n\n📐 Endi **o'lchamini** kiriting (masalan: `1200x600x50` yoki `1.06m x 10m`). O'tkazib yuborish/tashlab ketish uchun `/skip` yuboring:", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_PROD_SIZE')
def handle_admin_add_prod_size(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    size = None if text == "/skip" else text
    if size:
        user_states[chat_id]['new_product']['size'] = size
        
    user_states[chat_id]['state'] = 'ADMIN_ADD_PROD_UNIT'
    bot.send_message(
        chat_id, 
        f"📐 O'lchami: **{size or 'Tashlab ketildi'}**\n\n📦 Endi **o'lchov birligini** kiriting (masalan: `m2`, `Rulon`, `dona`). O'tkazib yuborish uchun `/skip` yuboring:", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_PROD_UNIT')
def handle_admin_add_prod_unit(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    unit = None if text == "/skip" else text
    if unit:
        user_states[chat_id]['new_product']['unit'] = unit
        
    user_states[chat_id]['state'] = 'ADMIN_ADD_PROD_PHOTO'
    bot.send_message(
        chat_id, 
        f"📦 O'lchov birligi: **{unit or 'Tashlab ketildi'}**\n\n🖼 Endi **mahsulot rasmini** yuboring (rasm formatida). Rasmsiz qoldirish uchun `/skip` yuboring:", 
        parse_mode="Markdown"
    )

import time
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'ADMIN_ADD_PROD_PHOTO', content_types=['text', 'photo'])
def handle_admin_add_prod_photo(message):
    chat_id = message.chat.id
    
    if message.text and message.text.strip() == '/skip':
        save_new_product(chat_id, image_file=None, image_data=None)
        return
        
    if message.content_type != 'photo':
        bot.reply_to(message, "⚠️ Iltimos mahsulot rasmini yuboring (yoki rasmsiz qoldirish uchun `/skip` yuboring):")
        return
        
    try:
        photo_info = message.photo[-1]
        file_info = bot.get_file(photo_info.file_id)
        
        file_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_info.file_path}"
        r = requests.get(file_url, verify=False)
        if r.status_code != 200:
            bot.reply_to(message, "⚠️ Telegram'dan rasmni yuklab olishda xatolik. Qaytadan urinib ko'ring:")
            return
            
        file_bytes = r.content
        filename = f"prod_{int(time.time())}.jpg"
        local_image_path = os.path.join(IMAGES_DIR, filename)
        
        os.makedirs(IMAGES_DIR, exist_ok=True)
        with open(local_image_path, 'wb') as f:
            f.write(file_bytes)
            
        save_new_product(chat_id, image_file=filename, image_data=file_bytes)
        
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Rasmni qayta ishlashda xatolik yuz berdi: {e}", reply_markup=get_admin_keyboard())
        user_states.pop(chat_id, None)

def save_new_product(chat_id, image_file=None, image_data=None):
    new_prod_info = user_states[chat_id]['new_product']
    cat_name = new_prod_info['category']
    prod_name = new_prod_info['name']
    price = new_prod_info['priceValue']
    size = new_prod_info.get('size')
    unit = new_prod_info.get('unit')
    
    import uuid
    prod_id = f"prod_{uuid.uuid4().hex[:8]}"
    
    new_item = {
        "id": prod_id,
        "name": prod_name,
        "priceValue": price,
        "currency": "UZS"
    }
    if size:
        new_item["size"] = size
    if unit:
        new_item["unit"] = unit
    if image_file:
        new_item["image_file"] = image_file
        
    products_data = load_products()
    
    target_cat = None
    for cat in products_data:
        if cat['category'].lower() == cat_name.lower():
            target_cat = cat
            break
            
    if not target_cat:
        target_cat = {"category": cat_name, "items": []}
        products_data.append(target_cat)
        
    target_cat['items'].append(new_item)
    
    file_path = os.path.join(os.path.dirname(__file__), 'products.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(products_data, f, indent=2, ensure_ascii=False)
        
    bot.send_message(chat_id, "🔄 Mahsulot saqlandi. Ma'lumotlar GitHub'ga yuklanmoqda...")
    
    image_sync_success = True
    if image_file and image_data:
        image_sync_success = sync_file_to_github(f"images/{image_file}", image_data, f"Add product image {image_file}")
        
    with open(file_path, 'rb') as f:
        content_bytes = f.read()
    json_sync_success = sync_file_to_github('products.json', content_bytes, f"Add product {prod_name} to category {cat_name}")
    
    if json_sync_success and image_sync_success:
        bot.send_message(
            chat_id,
            f"✅ **Yangi mahsulot muvaffaqiyatli qo'shildi va GitHub'ga yuklandi!**\n\n📌 **Nomi:** {prod_name}\n💰 **Narxi:** {price:,} so'm\n📂 **Kategoriya:** {cat_name}\n\nRender 1-2 daqiqada botni qayta ishga tushiradi.",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    else:
        bot.send_message(
            chat_id,
            f"⚠️ Mahsulot saqlandi, lekin GitHub'ga yuklashda xatolik yuz berdi. Render'da yangilanmadi.",
            reply_markup=get_admin_keyboard()
        )
        
    user_states.pop(chat_id, None)

# --- Manzil va Aloqa handlerlari ---
@bot.message_handler(func=lambda msg: msg.text == "📍 Manzil")
def send_address(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    
    # Geografik joylashuv (Location) yuboramiz
    try:
        bot.send_location(chat_id, config.STORE_LATITUDE, config.STORE_LONGITUDE)
    except Exception as e:
        print(f"Lokatsiya yuborishda xatolik: {e}")
        
    # Manzil matnini tagida yuboramiz
    bot.send_message(chat_id, config.STORE_ADDRESS, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📞 Aloqa")
def send_contact(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    bot.send_message(chat_id, config.STORE_CONTACTS, parse_mode="Markdown")

# --- Katalog handlerlari ---

import json

def load_products():
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'products.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading products: {e}")
    return []

def format_price(value, currency="UZS"):
    if value is None:
        return "Bog'laning"
    formatted = f"{value:,}".replace(",", " ")
    if currency == "USD":
        return f"${formatted}"
    return f"{formatted} so'm"

@bot.message_handler(func=lambda msg: msg.text == "📂 Katalog")
def send_catalog(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    
    products_data = load_products()
    if not products_data:
        bot.send_message(chat_id, "⚠️ Hozircha katalog bo'sh yoki yuklashda xatolik yuz berdi.")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for index, cat in enumerate(products_data):
        btn = types.InlineKeyboardButton(text=cat['category'], callback_data=f"cat_select_{index}")
        markup.add(btn)
        
    bot.send_message(
        chat_id, 
        "📂 **Katalog bo'limlari:**\n\nIltimos, mahsulot toifasini tanlang:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_select_') or call.data == 'cat_back_to_list')
def handle_cat_selection(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot.answer_callback_query(call.id)
    
    products_data = load_products()
    
    if call.data == 'cat_back_to_list':
        markup = types.InlineKeyboardMarkup(row_width=1)
        for index, cat in enumerate(products_data):
            btn = types.InlineKeyboardButton(text=cat['category'], callback_data=f"cat_select_{index}")
            markup.add(btn)
            
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
            
        bot.send_message(
            chat_id=chat_id,
            text="📂 **Katalog bo'limlari:**\n\nIltimos, mahsulot toifasini tanlang:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    cat_index = int(call.data.split('_')[2])
    if cat_index >= len(products_data):
        return
        
    cat = products_data[cat_index]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in cat['items']:
        btn = types.InlineKeyboardButton(
            text=f"{item['name']} - {format_price(item['priceValue'], item.get('currency', 'UZS'))}",
            callback_data=f"prod_select_{cat_index}_{item['id']}"
        )
        markup.add(btn)
    back_btn = types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cat_back_to_list")
    markup.add(back_btn)
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"📂 **{cat['category']}** bo'limidagi mahsulotlar:\n\nBatafsil ma'lumot olish uchun mahsulotni tanlang:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('prod_select_') or call.data.startswith('prod_back_to_cat_'))
def handle_product_detail(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot.answer_callback_query(call.id)
    
    products_data = load_products()
    
    if call.data.startswith('prod_back_to_cat_'):
        cat_index = int(call.data.split('_')[4])
        if cat_index >= len(products_data):
            return
        cat = products_data[cat_index]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for item in cat['items']:
            btn = types.InlineKeyboardButton(
                text=f"{item['name']} - {format_price(item['priceValue'], item.get('currency', 'UZS'))}",
                callback_data=f"prod_select_{cat_index}_{item['id']}"
            )
            markup.add(btn)
        back_btn = types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cat_back_to_list")
        markup.add(back_btn)
        
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
            
        bot.send_message(
            chat_id=chat_id,
            text=f"📂 **{cat['category']}** bo'limidagi mahsulotlar:\n\nBatafsil ma'lumot olish uchun mahsulotni tanlang:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    parts = call.data.split('_')
    cat_index = int(parts[2])
    item_id = '_'.join(parts[3:])
    
    if cat_index >= len(products_data):
        return
    cat = products_data[cat_index]
    
    selected_item = None
    for item in cat['items']:
        if item['id'] == item_id:
            selected_item = item
            break
            
    if not selected_item:
        return

    detail_text = (
        f"🌟 **{selected_item['name']}**\n\n"
        f"💰 **Narxi:** {format_price(selected_item['priceValue'], selected_item.get('currency', 'UZS'))}\n"
    )
    if 'size' in selected_item:
        detail_text += f"📐 **O'lchami:** {selected_item['size']}\n"
    if 'unit' in selected_item:
        detail_text += f"📦 **O'lchov birligi:** {selected_item['unit']}\n"
        
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"prod_back_to_cat_{cat_index}")
    markup.add(back_btn)
    
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass
        
    image_file = selected_item.get('image_file')
    image_path = os.path.join(IMAGES_DIR, image_file) if image_file else None
    
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=detail_text, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, detail_text, parse_mode="Markdown", reply_markup=markup)


# Oddiy kalkulyator boshlash (Asosiy menyudan bosilganda)
@bot.message_handler(func=lambda msg: msg.text == "🧮 Aboy hisoblash")
def start_calculator(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'state': 'INPUT_WIDTH'}
    bot.send_message(
        chat_id, 
        "🧮 **Aboy hisoblash kalkulyatori**\n\n↔️ Xonaning **kengligini (enini)** kiriting (metrda, masalan: `4`):",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Xona kengligini qabul qilish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_WIDTH')
def handle_width_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        width = float(text)
        if width <= 0 or width > 100:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona kengligini son bilan kiriting (masalan: 4):")
        return
        
    user_states[chat_id]['room_width'] = width
    user_states[chat_id]['state'] = 'INPUT_LENGTH'
    bot.send_message(
        chat_id,
        "↕️ Endi esa xonaning **uzunligini** kiriting (metrda, masalan: `5`):",
        parse_mode="Markdown"
    )

# Xona uzunligini qabul qilish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_LENGTH')
def handle_length_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        length = float(text)
        if length <= 0 or length > 100:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona uzunligini son bilan kiriting (masalan: 5):")
        return
        
    user_states[chat_id]['room_length'] = length
    user_states[chat_id]['state'] = 'INPUT_HEIGHT'
    bot.send_message(
        chat_id,
        "📏 Xonaning **balandligini** kiriting (metrda, masalan: `2.7`):",
        parse_mode="Markdown"
    )

# Xona balandligini qabul qilish va natijani chiqarish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_HEIGHT')
def handle_height_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        height = float(text)
        if height <= 0 or height > 10:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona balandligini son bilan kiriting (masalan: 2.7):")
        return
        
    width = user_states[chat_id]['room_width']
    length = user_states[chat_id]['room_length']
    
    # Devor yuzasini hisoblash
    perimeter = (width + length) * 2
    wall_area = round(perimeter * height, 2)
    
    result_text = f"🧱 Devorlar yuzasi (kvadrati): **{wall_area} kv.m**"
    
    bot.send_message(chat_id, result_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    user_states.pop(chat_id, None)


# --- Noto'g'ri kiritilgan matnlarni qayta ishlash ---
@bot.message_handler(func=lambda msg: True)
def handle_unknown_messages(message):
    chat_id = message.chat.id
    if chat_id in user_states:
        state = user_states[chat_id]['state']
        if state == 'INPUT_WIDTH':
            bot.reply_to(message, "⚠️ Xona kengligini (enini) son bilan kiriting (masalan: 4):")
        elif state == 'INPUT_LENGTH':
            bot.reply_to(message, "⚠️ Xona uzunligini son bilan kiriting (masalan: 5):")
        elif state == 'INPUT_HEIGHT':
            bot.reply_to(message, "⚠️ Xona balandligini son bilan kiriting (masalan: 2.7):")
        elif state.startswith('ADMIN_'):
            bot.reply_to(message, "⚠️ Kiritishda xatolik. Iltimos, ko'rsatmaga amal qiling yoki orqaga qaytish uchun /admin_exit yuboring.")
        else:
            bot.send_message(chat_id, "Iltimos, o'lchamlarni to'g'ri kiriting.", reply_markup=get_main_keyboard())
    else:
        if is_admin(chat_id):
            bot.send_message(
                chat_id, 
                "Iltimos, quyidagi admin panel tugmalaridan birini tanlang:", 
                reply_markup=get_admin_keyboard()
            )
        else:
            bot.send_message(
                chat_id, 
                "Iltimos, quyidagi menyu tugmalaridan birini tanlang:", 
                reply_markup=get_main_keyboard()
            )


import keep_alive

# Botni uzluksiz ishlash rejimida ishga tushirish
if __name__ == '__main__':
    print("Bot muvaffaqiyatli ishga tushdi...")
    # Cloud serverlarda doimiy ishlashi uchun veb-serverni ishga tushiramiz
    keep_alive.keep_alive()
    # Cheksiz ishlashi uchun polling yoqiladi
    bot.infinity_polling()

