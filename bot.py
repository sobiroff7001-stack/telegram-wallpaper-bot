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
    
    # Manzil matni va Yandex Xarita havolasi
    address_text = (
        f"{config.STORE_ADDRESS}\n\n"
        f"🔗 [Yandex Xaritada ko'rish]({config.STORE_MAP_LINK})"
    )
    bot.send_message(chat_id, address_text, parse_mode="Markdown", disable_web_page_preview=False)
    
    # Geografik joylashuv (Location)
    try:
        bot.send_location(chat_id, config.STORE_LATITUDE, config.STORE_LONGITUDE)
    except Exception as e:
        print(f"Lokatsiya yuborishda xatolik: {e}")

@bot.message_handler(func=lambda msg: msg.text == "📞 Aloqa")
def send_contact(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    bot.send_message(chat_id, config.STORE_CONTACTS, parse_mode="Markdown")

# --- Katalog handlerlari ---
@bot.message_handler(func=lambda msg: msg.text == "📂 Katalog")
def send_catalog(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in config.CATALOG:
        btn = types.InlineKeyboardButton(text=f"{item['name']} - {item['price']}", callback_data=f"catalog_detail_{item['id']}")
        markup.add(btn)
        
    bot.send_message(
        chat_id, 
        "📂 **Mavjud aboylarimiz katalogi:**\n"
        "Batafsil ma'lumot va rasmini ko'rish uchun aboy nomini tanlang:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# Katalogdan biror aboy tanlangandagi callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("catalog_detail_"))
def handle_catalog_detail(call):
    chat_id = call.message.chat.id
    item_id = int(call.data.split("_")[-1])
    
    # Mahsulotni topish
    selected_item = None
    for item in config.CATALOG:
        if item['id'] == item_id:
            selected_item = item
            break
            
    if not selected_item:
        bot.answer_callback_query(call.id, "Mahsulot topilmadi.")
        return
        
    bot.answer_callback_query(call.id)
    
    # Batafsil ma'lumot matni
    detail_text = (
        f"🌟 **{selected_item['name']}**\n\n"
        f"💰 **Narxi:** {selected_item['price']} (1 rulon)\n"
        f"📐 **Rulon o'lchami:** {selected_item['roll_size']}\n"
        f"📝 **Tavsif:** {selected_item['description']}\n"
    )
    
    # Rulon eni qiymatini ajratib olish (kalkulyator uchun)
    width_val = 1.06 if "1.06m" in selected_item['roll_size'] else 0.53
    
    # Inline keyboard yaratish
    markup = types.InlineKeyboardMarkup()
    btn_calc_this = types.InlineKeyboardButton(
        text="🧮 Ushbu aboydan xonaga hisoblash", 
        callback_data=f"calc_prefilled_{width_val}"
    )
    markup.add(btn_calc_this)
    
    # Rasm bilan birga yuborish
    image_path = os.path.join(IMAGES_DIR, selected_item['image_filename'])
    if os.path.exists(image_path):
        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=detail_text, parse_mode="Markdown", reply_markup=markup)
    else:
        # Rasm topilmasa oddiy matn yuboriladi
        bot.send_message(chat_id, detail_text, parse_mode="Markdown", reply_markup=markup)

# --- Kalkulyator Bosqichlari (State Machine) ---

# Prefilled kalkulyator boshlash (Katalog orqali kirilganda)
@bot.callback_query_handler(func=lambda call: call.data.startswith("calc_prefilled_"))
def handle_calc_prefilled(call):
    chat_id = call.message.chat.id
    roll_width = float(call.data.split("_")[-1])
    bot.answer_callback_query(call.id)
    
    user_states[chat_id] = {
        'state': 'INPUT_HEIGHT',
        'roll_width': roll_width
    }
    
    # Keyingi bosqich: balandlik so'rash
    bot.send_message(
        chat_id, 
        f"✅ Rulon eni **{roll_width} metr** qilib belgilandi.\n\n"
        "📏 **Xonaning balandligini** kiriting (metrda, masalan: `2.7` yoki `3`):",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove() # Vaqtinchalik asosiy tugmalarni yashiramiz
    )

# Oddiy kalkulyator boshlash (Asosiy menyudan bosilganda)
@bot.message_handler(func=lambda msg: msg.text == "🧮 Aboy hisoblash")
def start_calculator(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'state': 'CHOOSE_WIDTH'}
    
    # Rulon enini tanlash inline tugmalari
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_wide = types.InlineKeyboardButton("Standart keng (1.06 m)", callback_data="width_1.06")
    btn_narrow = types.InlineKeyboardButton("Standart tor (0.53 m)", callback_data="width_0.53")
    markup.add(btn_wide, btn_narrow)
    
    bot.send_message(
        chat_id, 
        "🧮 **Aboy hisoblash kalkulyatori**\n\n"
        "Birinchi bo'lib aboy **rulonining enini** tanlang:", 
        reply_markup=markup
    )

# Rulon enini tanlash callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("width_"))
def handle_width_selection(call):
    chat_id = call.message.chat.id
    if chat_id not in user_states or user_states[chat_id]['state'] != 'CHOOSE_WIDTH':
        bot.answer_callback_query(call.id)
        return
        
    roll_width = float(call.data.split("_")[-1])
    bot.answer_callback_query(call.id)
    
    user_states[chat_id]['roll_width'] = roll_width
    user_states[chat_id]['state'] = 'INPUT_HEIGHT'
    
    # Balandlik so'rash
    bot.edit_message_text(
        text=f"📐 Tanlangan rulon eni: **{roll_width} metr**.\n\n"
             "📏 Endi esa **xonaning balandligini** kiriting (metrda, masalan: `2.7` yoki `3`):",
        chat_id=chat_id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )

# Xona balandligini qabul qilish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_HEIGHT')
def handle_height_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        height = float(text)
        if height <= 0 or height > 10:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat kiritildi. Xona balandligini metrda kiriting (masalan: 2.7):")
        return
        
    user_states[chat_id]['room_height'] = height
    user_states[chat_id]['state'] = 'CHOOSE_METHOD'
    
    # O'lcham kiritish usulini tanlash
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_dim = types.InlineKeyboardButton("Uzunlik va kenglik bo'yicha", callback_data="method_dimensions")
    btn_per = types.InlineKeyboardButton("Umumiy perimetr bo'yicha", callback_data="method_perimeter")
    markup.add(btn_dim, btn_per)
    
    bot.send_message(
        chat_id,
        "📐 Devor o'lchamlarini qanday kiritmoqchisiz?\n"
        "Xonaning kengligi va uzunligini alohida kiritish qulayroq, "
        "lekin tayyor perimetr bo'lsa uni ham kiritishingiz mumkin.",
        reply_markup=markup
    )

# Kiritish usulini tanlash callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("method_"))
def handle_method_selection(call):
    chat_id = call.message.chat.id
    if chat_id not in user_states or user_states[chat_id]['state'] != 'CHOOSE_METHOD':
        bot.answer_callback_query(call.id)
        return
        
    method = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    
    if method == "dimensions":
        user_states[chat_id]['state'] = 'INPUT_WIDTH'
        bot.edit_message_text(
            text="↔️ Xonaning **kengligini** kiriting (metrda, masalan: `4` yoki `3.5`):",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        user_states[chat_id]['state'] = 'INPUT_PERIMETER'
        bot.edit_message_text(
            text="🔄 Xonaning **umumiy perimetrini** (barcha devorlar uzunliklari yig'indisini) kiriting (metrda, masalan: `18`):",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )

# Xona kengligini qabul qilish (agar dimensions tanlangan bo'lsa)
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_WIDTH')
def handle_width_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        width = float(text)
        if width <= 0 or width > 100:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona kengligini metrda kiriting (masalan: 4):")
        return
        
    user_states[chat_id]['room_width'] = width
    user_states[chat_id]['state'] = 'INPUT_LENGTH'
    
    bot.send_message(
        chat_id,
        "↕️ Endi esa xonaning **uzunligini** kiriting (metrda, masalan: `5` yoki `4.5`):",
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
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona uzunligini metrda kiriting (masalan: 5):")
        return
        
    user_states[chat_id]['room_length'] = length
    user_states[chat_id]['state'] = 'CHOOSE_PATTERN'
    
    ask_pattern_repeat(chat_id)

# Umumiy perimetrni qabul qilish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_PERIMETER')
def handle_perimeter_input(message):
    chat_id = message.chat.id
    text = message.text.strip().replace(",", ".")
    
    try:
        perimeter = float(text)
        if perimeter <= 0 or perimeter > 400:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Xona perimetrini metrda kiriting (masalan: 18):")
        return
        
    user_states[chat_id]['perimeter'] = perimeter
    user_states[chat_id]['state'] = 'CHOOSE_PATTERN'
    
    ask_pattern_repeat(chat_id)

# Naqsh takrorlanishi (gulini to'g'rilash) haqida so'rash
def ask_pattern_repeat(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_no = types.InlineKeyboardButton("Tekis yoki naqshsiz (gulsiz) aboy", callback_data="pattern_0")
    btn_32 = types.InlineKeyboardButton("Kichik gul (32 sm rapport)", callback_data="pattern_0.32")
    btn_64 = types.InlineKeyboardButton("Katta gul (64 sm rapport)", callback_data="pattern_0.64")
    btn_custom = types.InlineKeyboardButton("Boshqa o'lcham kiritish", callback_data="pattern_custom")
    markup.add(btn_no, btn_32, btn_64, btn_custom)
    
    bot.send_message(
        chat_id,
        "🌸 **Aboy naqshini moslashtirish (rapport):**\n\n"
        "Gulini moslashtirish kerak bo'lgan aboylar kesilganda ko'proq chiqindi chiqadi. "
        "Aboy yorlig'ida yozilgan guli takrorlanish (rapport) o'lchamini tanlang:",
        reply_markup=markup
    )

# Naqsh tanlash callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("pattern_"))
def handle_pattern_selection(call):
    chat_id = call.message.chat.id
    if chat_id not in user_states or user_states[chat_id]['state'] != 'CHOOSE_PATTERN':
        bot.answer_callback_query(call.id)
        return
        
    data = call.data.split("_")[-1]
    bot.answer_callback_query(call.id)
    
    if data == "custom":
        user_states[chat_id]['state'] = 'INPUT_PATTERN_CUSTOM'
        bot.edit_message_text(
            text="🌸 Aboy gulining takrorlanish o'lchamini **santimetrda** kiriting (masalan: `53` yoki `60`):",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        pattern_repeat = float(data)
        user_states[chat_id]['pattern_repeat'] = pattern_repeat
        calculate_and_send_result(chat_id)

# Custom naqsh o'lchamini qabul qilish
@bot.message_handler(func=lambda msg: msg.chat.id in user_states and user_states[msg.chat.id]['state'] == 'INPUT_PATTERN_CUSTOM')
def handle_pattern_custom_input(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    try:
        pattern_cm = float(text)
        if pattern_cm < 0 or pattern_cm > 200:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "⚠️ Noto'g'ri qiymat. Santimetrda butun yoki o'nlik son kiriting (masalan: 53):")
        return
        
    # Santimetrni metrga o'tkazamiz
    user_states[chat_id]['pattern_repeat'] = pattern_cm / 100.0
    calculate_and_send_result(chat_id)

# Hisoblash va natijani yuborish
def calculate_and_send_result(chat_id):
    data = user_states.get(chat_id)
    if not data:
        return
        
    roll_width = data['roll_width']
    room_height = data['room_height']
    pattern_repeat = data.get('pattern_repeat', 0.0)
    
    # Perimetr yoki kenglik/uzunlik bo'yicha hisoblashni aniqlash
    if 'perimeter' in data:
        result = calculator.calculate_wallpaper_by_perimeter(
            perimeter=data['perimeter'],
            room_height=room_height,
            roll_width=roll_width,
            pattern_repeat=pattern_repeat
        )
        dimensions_text = f"🔄 Xona perimetri: **{data['perimeter']} m**"
    else:
        result = calculator.calculate_wallpaper(
            room_width=data['room_width'],
            room_length=data['room_length'],
            room_height=room_height,
            roll_width=roll_width,
            pattern_repeat=pattern_repeat
        )
        dimensions_text = f"📐 Xona o'lchami: **{data['room_width']} x {data['room_length']} m** (Perimetri: {result['perimeter']} m)"
        
    # Natija matnini shakllantirish
    result_text = (
        "📊 **HISOB-KITOB NATIJASI:**\n\n"
        f"{dimensions_text}\n"
        f"📏 Devor balandligi: **{room_height} m**\n"
        f"📐 Rulon o'lchami: **{roll_width} m x 10 m**\n"
        f"🌸 Gul mosligi (rapport): **{int(pattern_repeat * 100)} sm**\n"
        f"🧱 Umumiy devor yuzasi: **{result['total_area']} kv.m**\n\n"
        "--- Hisoblash jarayoni ---\n"
        f"🔹 Kerakli jami chiziqlar (polosa) soni: **{result['stripes_needed']} ta**\n"
        f"🔹 Bitta rulondan chiqadigan to'liq chiziqlar: **{result['stripes_per_roll']} ta**\n\n"
        f"🛒 **Jami kerakli aboy: {result['rolls_needed']} rulon**\n\n"
        "💡 *Maslahat:* Ushbu hisob-kitob matematik formula asosida chiqarilgan bo'lib, xonadagi eshiklar va derazalarni hisobga olmaydi. "
        "Guli moslashtiriladigan aboylar kesilganda ortib qolishi mumkinligi va ustaning ishlash uslubini hisobga olgan holda, "
        "har doim hisobga **+1 rulon qo'shimcha** qo'shib olish tavsiya etiladi."
    )
    
    # Asosiy tugmalarni qaytarish
    bot.send_message(chat_id, result_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    # Holatni tozalash
    user_states.pop(chat_id, None)

# --- Noto'g'ri kiritilgan matnlarni qayta ishlash ---
@bot.message_handler(func=lambda msg: True)
def handle_unknown_messages(message):
    chat_id = message.chat.id
    # Agar kalkulyator holatida bo'lmasa, shunchaki xush kelibsiz xabarini yuboradi
    if chat_id in user_states:
        state = user_states[chat_id]['state']
        # Holatga qarab tegishli javob
        if state == 'INPUT_HEIGHT':
            bot.reply_to(message, "⚠️ Xona balandligini son bilan kiriting (masalan: 2.7):")
        elif state == 'INPUT_WIDTH':
            bot.reply_to(message, "⚠️ Xona kengligini son bilan kiriting (masalan: 4):")
        elif state == 'INPUT_LENGTH':
            bot.reply_to(message, "⚠️ Xona uzunligini son bilan kiriting (masalan: 5):")
        elif state == 'INPUT_PERIMETER':
            bot.reply_to(message, "⚠️ Xona perimetrini son bilan kiriting (masalan: 18):")
        elif state == 'INPUT_PATTERN_CUSTOM':
            bot.reply_to(message, "⚠️ Gul o'lchamini santimetrda son bilan kiriting (masalan: 53):")
        else:
            bot.send_message(chat_id, "Iltimos, tugmalardan birini bosing yoki o'lchamlarni to'g'ri kiriting.", reply_markup=get_main_keyboard())
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

