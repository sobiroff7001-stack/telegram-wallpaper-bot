import os
from dotenv import load_dotenv

# .env faylidan o'zgaruvchilarni yuklash
load_dotenv()

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Do'kon manzili haqida ma'lumot
STORE_ADDRESS = (
    "📍 **Do'konimiz manzili:**\n"
    "Андижон шахар, Сой, маззавод кичик саноат зонаси 5-уй"
)

# Do'kon koordinatalari (Xaritada yuborish uchun)
STORE_LATITUDE = 40.804377
STORE_LONGITUDE = 72.351327
STORE_MAP_LINK = f"https://yandex.com/maps/?pt={STORE_LONGITUDE},{STORE_LATITUDE}&z=16&l=map"

# Aloqa ma'lumotlari
STORE_CONTACTS = (
    "📞 **Biz bilan aloqa:**\n\n"
    "📱 Telefon: +998 (90) 141-43-43\n"
    "💬 Telegram: @StroyBazan1uz\n\n"
    "Savollaringiz bo'lsa, istalgan vaqtda murojaat qilishingiz mumkin!"
)

# Katalog mahsulotlari (Aboylar)
CATALOG = [
    {
        "id": 1,
        "name": "Modern Minimalist (Kulrang)",
        "price": "180,000 so'm",
        "description": "Zamonaviy minimalist uslubdagi yashash xonasi va yotoqxona uchun mos keladigan kulrang teksturali sifatli aboy.",
        "image_filename": "modern_grey.png",
        "roll_size": "1.06m x 10m"
    },
    {
        "id": 2,
        "name": "Classic Gold (Klassik Oltin)",
        "price": "220,000 so'm",
        "description": "Premium klassik naqshli, oltin rangli va yaltiroq effektli mehmonxona uchun mo'ljallangan aboy.",
        "image_filename": "classic_gold.png",
        "roll_size": "1.06m x 10m"
    },
    {
        "id": 3,
        "name": "Loft Brick (G'ishtli Loft)",
        "price": "150,000 so'm",
        "description": "Loft uslubidagi dekorativ g'isht ko'rinishidagi aboy. Oshxona va koridorlar uchun juda mos keladi.",
        "image_filename": "loft_brick.png",
        "roll_size": "0.53m x 10m"
    },
    {
        "id": 4,
        "name": "Kids Stars (Bolalar uchun Yulduzchalar)",
        "price": "160,000 so'm",
        "description": "Ekologik toza va bolalar xonasi uchun mo'ljallangan, qorong'uda yaltiraydigan mayda yulduzchali aboy.",
        "image_filename": "kids_stars.png",
        "roll_size": "1.06m x 10m"
    }
]
