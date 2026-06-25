import os
import telebot
from telebot import types
import requests
from telebot import apihelper
from dotenv import load_dotenv

import config
import calculator

# .env faylini yuklash
load_dotenv()

# SSL sertifikat xatolarini chetlab o'tish (agar kerak bo'lsa)
session = requests.Session()
session.verify = False
apihelper.session = session

# Botni ishga tushirish
if not config.BOT_TOKEN:
    print("⚠️ DIQQAT: BOT_TOKEN .env faylida topilmadi. Iltimos bot tokenini kiriting.")

bot = telebot.TeleBot(config.BOT_TOKEN if config.BOT_TOKEN else "DUMMY_TOKEN")

# Foydalanuvchilar holati (kalkulyator uchun)
# Tuzilishi: {chat_id: {state: 'STATE_NAME', roll_width: 1.06, room_height: 2.7, ...}}
user_states = {}

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
        else:
            bot.send_message(chat_id, "Iltimos, o'lchamlarni to'g'ri kiriting.", reply_markup=get_main_keyboard())
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

