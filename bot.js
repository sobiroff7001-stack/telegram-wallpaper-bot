const fs = require('fs');
const path = require('path');
const config = require('./config');
const calculator = require('./calculator');

// SSL sertifikati tekshiruvini o'chirib qo'yish (SSL xatolarining oldini olish uchun)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const BOT_TOKEN = config.BOT_TOKEN;
const IMAGES_DIR = path.join(__dirname, 'images');

if (!BOT_TOKEN) {
    console.error("⚠️ BOT_TOKEN topilmadi! Iltimos, .env faylida tokeningizni belgilang.");
    process.exit(1);
}

// Foydalanuvchilar holati (State machine)
const userStates = {};

const SETTINGS_FILE = path.join(__dirname, 'settings.json');

function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
            store_address: config.STORE_ADDRESS,
            store_latitude: config.STORE_LATITUDE,
            store_longitude: config.STORE_LONGITUDE,
            store_contacts: config.STORE_CONTACTS,
            calculator_prices: [22000, 30000, 35000],
            custom_buttons: []
        };
        try {
            fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 2), 'utf8');
        } catch (e) {
            console.error("Error creating default settings:", e);
        }
    }
    
    try {
        const content = fs.readFileSync(SETTINGS_FILE, 'utf8');
        return JSON.parse(content);
    } catch (e) {
        console.error("Error reading settings.json:", e);
        return {};
    }
}

// Asosiy tugmalar (Reply Keyboard) - Dynamic via Javascript Getter
const mainKeyboard = {
    get keyboard() {
        const settings = loadSettings();
        const customButtons = settings.custom_buttons || [];
        const kb = [
            [{ text: "🧮 Xonani hisoblash" }, { text: "🏠 Mat hisoblash" }],
            [{ text: "📂 Katalog" }, { text: "📍 Manzil" }, { text: "📞 Aloqa" }]
        ];
        
        for (let i = 0; i < customButtons.length; i += 2) {
            const row = [];
            row.push({ text: customButtons[i].name });
            if (i + 1 < customButtons.length) {
                row.push({ text: customButtons[i + 1].name });
            }
            kb.push(row);
        }
        return kb;
    },
    resize_keyboard: true
};

// Telegram API so'rov yuborish
async function api(method, params = {}) {
    try {
        const response = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/${method}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return await response.json();
    } catch (e) {
        console.error(`Fetch API Error (${method}):`, e);
        return { ok: false };
    }
}

// Rasm yuborish (Multipart/form-data)
async function sendPhoto(chatId, filePath, caption, replyMarkup) {
    try {
        const formData = new FormData();
        formData.append('chat_id', chatId);
        formData.append('caption', caption);
        formData.append('parse_mode', 'Markdown');
        if (replyMarkup) {
            formData.append('reply_markup', JSON.stringify(replyMarkup));
        }
        
        const fileBuffer = fs.readFileSync(filePath);
        const blob = new Blob([fileBuffer], { type: 'image/png' });
        formData.append('photo', blob, path.basename(filePath));
        
        const response = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
            method: 'POST',
            body: formData
        });
        return await response.json();
    } catch (e) {
        console.error("Send Photo Error:", e);
        // Rasm yuborib bo'lmasa oddiy matn qilib yuboradi
        return api('sendMessage', {
            chat_id: chatId,
            text: caption,
            parse_mode: 'Markdown',
            reply_markup: replyMarkup
        });
    }
}

// Manzil tugmasi uchun
async function handleAddress(chatId) {
    delete userStates[chatId];
    const settings = loadSettings();
    // Kordinatani yuborish
    await api('sendLocation', {
        chat_id: chatId,
        latitude: settings.store_latitude || config.STORE_LATITUDE,
        longitude: settings.store_longitude || config.STORE_LONGITUDE
    });
    // Manzil matnini tagida yuborish
    await api('sendMessage', {
        chat_id: chatId,
        text: settings.store_address || config.STORE_ADDRESS,
        parse_mode: 'Markdown'
    });
}

// Aloqa tugmasi uchun
async function handleContact(chatId) {
    delete userStates[chatId];
    const settings = loadSettings();
    await api('sendMessage', {
        chat_id: chatId,
        text: settings.store_contacts || config.STORE_CONTACTS,
        parse_mode: 'Markdown',
        reply_markup: mainKeyboard
    });
}

// Mahsulotlarni yuklash (stroy-baza-catalog loyihasidan)
function loadProducts() {
    try {
        const filePath = path.join(__dirname, 'products.json');
        if (fs.existsSync(filePath)) {
            const content = fs.readFileSync(filePath, 'utf8');
            return JSON.parse(content);
        }
    } catch (e) {
        console.error("Error loading products:", e);
    }
    return [];
}

// Narxni formatlash
function formatPrice(value, currency) {
    if (value === null || value === undefined) {
        return "Bog'laning";
    }
    const formattedVal = value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    if (currency === 'USD') {
        return `$${formattedVal}`;
    }
    return `${formattedVal} so'm`;
}

// Katalog tugmasi uchun (Kategoriyalarni ko'rsatish)
async function handleCatalog(chatId) {
    delete userStates[chatId];
    const productsData = loadProducts();
    
    if (productsData.length === 0) {
        await api('sendMessage', {
            chat_id: chatId,
            text: "⚠️ Hozircha katalog bo'sh yoki yuklashda xatolik yuz berdi.",
            reply_markup: mainKeyboard
        });
        return;
    }
    
    const inlineKeyboard = {
        inline_keyboard: productsData.map((cat, index) => [
            { text: cat.category, callback_data: `cat_select_${index}` }
        ])
    };
    
    await api('sendMessage', {
        chat_id: chatId,
        text: "📂 **Katalog bo'limlari:**\n\nIltimos, mahsulot toifasini tanlang:",
        parse_mode: 'Markdown',
        reply_markup: inlineKeyboard
    });
}

// Gul moslashuvini so'rash
async function askPatternRepeat(chatId) {
    const inlineKeyboard = {
        inline_keyboard: [
            [{ text: "Tekis yoki naqshsiz (gulsiz) aboy", callback_data: "pattern_0" }],
            [{ text: "Kichik gul (32 sm rapport)", callback_data: "pattern_0.32" }],
            [{ text: "Katta gul (64 sm rapport)", callback_data: "pattern_0.64" }],
            [{ text: "Boshqa o'lcham kiritish", callback_data: "pattern_custom" }]
        ]
    };
    await api('sendMessage', {
        chat_id: chatId,
        text: "🌸 **Aboy naqshini moslashtirish (rapport):**\n\nGulini moslashtirish kerak bo'lgan aboylar kesilganda ko'proq chiqindi chiqadi. Aboy yorlig'ida yozilgan guli takrorlanish (rapport) o'lchamini tanlang:",
        reply_markup: inlineKeyboard
    });
}

// Hisob-kitobni yakunlash va chiqarish
async function calculateAndSendResult(chatId) {
    const data = userStates[chatId];
    if (!data) return;
    
    const width = data.room_width;
    const length = data.room_length;
    const height = data.room_height;
    const price = data.selected_price || 0;
    
    // calculator dan hisob-kitobni olamiz
    const calc = calculator.calculateWallpaper(width, length, height);
    const wallArea = calc.totalArea;
    
    const costBySqm = Math.floor(wallArea * price);
    
    const resultText = `🧱 Devorlar yuzasi (kvadrati): **${wallArea} kv.m**\n` +
        `💰 **Jami aboy ketish narxi:** **${costBySqm.toLocaleString('uz-UZ')} so'm**`;
        
    await api('sendMessage', {
        chat_id: chatId,
        text: resultText,
        parse_mode: 'Markdown',
        reply_markup: mainKeyboard
    });
    
    delete userStates[chatId];
}

// O'lchamlarni matndan aniqlash va hisoblash
function parseAndCalculate(text) {
    let cleanText = text.trim().replace(/,/g, '.');
    cleanText = cleanText.replace(/\s*[xX\*хХ]\s*/g, 'x');
    cleanText = cleanText.replace(/\s+/g, 'x');
    
    // Format 1: 5 ta o'lcham (xona_eni x xona_boyi x xona_balandligi x aboy_eni x aboy_boyi)
    // Masalan: 4x5x2.7x1.06x10
    const match5 = cleanText.match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$/);
    if (match5) {
        return {
            type: 'full',
            roomWidth: parseFloat(match5[1]),
            roomLength: parseFloat(match5[2]),
            roomHeight: parseFloat(match5[3]),
            rollWidth: parseFloat(match5[4]),
            rollLength: parseFloat(match5[5])
        };
    }
    
    // Format 2: 3 ta o'lcham (xona_eni x xona_boyi x xona_balandligi)
    // Masalan: 4x5x2.7
    const match3 = cleanText.match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$/);
    if (match3) {
        return {
            type: 'room_only',
            roomWidth: parseFloat(match3[1]),
            roomLength: parseFloat(match3[2]),
            roomHeight: parseFloat(match3[3])
        };
    }
    
    return null;
}

// Xabarlarga javob berish
async function handleMessage(message) {
    const chatId = message.chat.id;
    const text = (message.text || '').trim();
    
    // Check custom dynamic buttons first
    const settings = loadSettings();
    const customButtons = settings.custom_buttons || [];
    const matchedBtn = customButtons.find(b => b.name === text);
    if (matchedBtn) {
        delete userStates[chatId];
        await api('sendMessage', {
            chat_id: chatId,
            text: matchedBtn.reply_text,
            parse_mode: 'Markdown',
            reply_markup: mainKeyboard
        });
        return;
    }
    
    // Avtomatik o'lchamlarni matndan aniqlab hisoblash
    const parsedDim = parseAndCalculate(text);
    if (parsedDim) {
        delete userStates[chatId]; // Har qanday oraliq holatni o'chirib tashlaymiz
        
        const { roomWidth, roomLength, roomHeight } = parsedDim;
        
        userStates[chatId] = {
            room_width: roomWidth,
            room_length: roomLength,
            room_height: roomHeight
        };
        
        await calculateAndSendResult(chatId);
        return;
    }
    
    if (text === '/start') {
        delete userStates[chatId];
        await api('sendMessage', {
            chat_id: chatId,
            text: "👋 **Salom! Aboy do'konimiz botiga xush kelibsiz!**\n\n" +
                "Men sizga xonangiz uchun qancha aboy (gulqog'oz) kerakligini hisoblashda yordam beraman, " +
                "shuningdek do'konimizdagi mahsulotlar katalogi, manzilimiz va kontaktlarimiz bilan tanishtira olaman.\n\n" +
                "Boshlash uchun quyidagi tugmalardan birini bosing:",
            parse_mode: 'Markdown',
            reply_markup: mainKeyboard
        });
        return;
    }
    
    if (text === '/help') {
        await api('sendMessage', {
            chat_id: chatId,
            text: "🤖 **Botdan foydalanish yo'riqnomasi:**\n\n" +
                "🧮 **Xonani hisoblash** — Xonangiz o'lchamlarini kiritasiz va bot sizga qancha aboy ruloni ketishini hisoblab beradi.\n" +
                "📂 **Katalog** — Do'kondagi aboylar turlari va narxlari.\n" +
                "📍 **Manzil** — Do'konimiz joylashgan manzil va geografik lokatsiyasi.\n" +
                "📞 **Aloqa** — Telefon raqamlarimiz va ish vaqtlarimiz.\n\n" +
                "Agar kalkulyatorda adashib qolsangiz, shunchaki /start buyrug'ini yuboring.",
            parse_mode: 'Markdown'
        });
        return;
    }
    
    if (text === '📍 Manzil') {
        await handleAddress(chatId);
        return;
    }
    
    if (text === '📞 Aloqa') {
        await handleContact(chatId);
        return;
    }
    
    if (text === '📂 Katalog') {
        await handleCatalog(chatId);
        return;
    }
    
    if (text === '🧮 Xonani hisoblash' || text === '🧮 Aboy hisoblash') {
        userStates[chatId] = { state: 'SELECT_PRICE' };
        const settings = loadSettings();
        const prices = settings.calculator_prices || [22000, 30000, 35000];
        const inlineKeyboard = {
            inline_keyboard: prices.map(p => [
                { text: `${p.toLocaleString('uz-UZ')} so'm`, callback_data: `price_${p}` }
            ])
        };
        await api('sendMessage', {
            chat_id: chatId,
            text: "🧮 **Aboy hisoblash kalkulyatori**\n\n💵 Iltimos, aboy narxini tanlang:",
            parse_mode: 'Markdown',
            reply_markup: inlineKeyboard
        });
        return;
    }
    
    if (text === '🏠 Mat hisoblash') {
        userStates[chatId] = { state: 'MAT_SELECT_PRICE' };
        const settings = loadSettings();
        const matPrices = settings.mat_prices || [40000];
        const inlineKeyboard = {
            inline_keyboard: matPrices.map(p => [
                { text: `${p.toLocaleString('uz-UZ')} so'm`, callback_data: `mat_price_${p}` }
            ])
        };
        await api('sendMessage', {
            chat_id: chatId,
            text: "🏠 **Mat hisoblash kalkulyatori**\n\n💵 Iltimos, mat narxini tanlang:",
            parse_mode: 'Markdown',
            reply_markup: inlineKeyboard
        });
        return;
    }
    
    // Foydalanuvchi javob kiritayotgan bo'lsa
    if (userStates[chatId]) {
        const state = userStates[chatId].state;
        const val = parseFloat(text.replace(',', '.'));
        
        if (state === 'SELECT_PRICE') {
            await api('sendMessage', {
                chat_id: chatId,
                text: "⚠️ Iltimos, yuqoridagi tugmalardan birini bosib aboy narxini tanlang."
            });
            return;
        } else if (state === 'INPUT_ROOM_WIDTH') {
            if (isNaN(val) || val <= 0 || val > 100) {
                await api('sendMessage', {
                    chat_id: chatId,
                    text: "⚠️ Noto'g'ri qiymat. Xonangizning enini metrda kiriting (masalan: 4):"
                });
                return;
            }
            userStates[chatId].room_width = val;
            userStates[chatId].state = 'INPUT_ROOM_LENGTH';
            await api('sendMessage', {
                chat_id: chatId,
                text: "↕️ Xonangizning **uzunligini** kiriting (metrda, masalan: `5`):",
                parse_mode: 'Markdown'
            });
        } else if (state === 'INPUT_ROOM_LENGTH') {
            if (isNaN(val) || val <= 0 || val > 100) {
                await api('sendMessage', {
                    chat_id: chatId,
                    text: "⚠️ Noto'g'ri qiymat. Xonangizning uzunligini metrda kiriting (masalan: 5):"
                });
                return;
            }
            userStates[chatId].room_length = val;
            userStates[chatId].state = 'INPUT_ROOM_HEIGHT';
            await api('sendMessage', {
                chat_id: chatId,
                text: "📏 Xonangizning **balandligini** kiriting (metrda, masalan: `2.7`):",
                parse_mode: 'Markdown'
            });
        } else if (state === 'INPUT_ROOM_HEIGHT') {
            if (isNaN(val) || val <= 0 || val > 10) {
                await api('sendMessage', {
                    chat_id: chatId,
                    text: "⚠️ Noto'g'ri qiymat. Xona balandligini metrda kiriting (masalan: 2.7):"
                });
                return;
            }
            userStates[chatId].room_height = val;
            await calculateAndSendResult(chatId);
        }
        } else if (state === 'MAT_SELECT_PRICE') {
            await api('sendMessage', {
                chat_id: chatId,
                text: "⚠️ Iltimos, yuqoridagi tugmalardan birini bosib mat narxini tanlang."
            });
            return;
        } else if (state === 'MAT_INPUT_WIDTH') {
            if (isNaN(val) || val <= 0 || val > 100) {
                await api('sendMessage', { chat_id: chatId, text: "⚠️ Noto'g'ri qiymat. Xona enini metrda kiriting (masalan: 4):" });
                return;
            }
            userStates[chatId].room_width = val;
            userStates[chatId].state = 'MAT_INPUT_LENGTH';
            await api('sendMessage', {
                chat_id: chatId,
                text: "↕️ Xonaning **uzunligini** kiriting (metrda, masalan: `5`):",
                parse_mode: 'Markdown'
            });
        } else if (state === 'MAT_INPUT_LENGTH') {
            if (isNaN(val) || val <= 0 || val > 100) {
                await api('sendMessage', { chat_id: chatId, text: "⚠️ Noto'g'ri qiymat. Xona uzunligini metrda kiriting (masalan: 5):" });
                return;
            }
            const width = userStates[chatId].room_width;
            const price = userStates[chatId].selected_price || 0;
            const area = Math.round(width * val * 100) / 100;
            const totalCost = Math.floor(area * price);
            const resultText = `🏠 Xona yuzasi (kvadrati): **${area} kv.m**\n` +
                `💰 **Jami mat ketish narxi:** **${totalCost.toLocaleString('uz-UZ')} so'm**`;
            await api('sendMessage', {
                chat_id: chatId,
                text: resultText,
                parse_mode: 'Markdown',
                reply_markup: mainKeyboard
            });
            delete userStates[chatId];
            return;
        }
        return;
    }
    
    // Noma'lum xabarlar
    await api('sendMessage', {
        chat_id: chatId,
        text: "Iltimos, quyidagi menyu tugmalaridan birini tanlang:",
        reply_markup: mainKeyboard
    });
}

// Inline tugmalar bosilganda (Callback Query)
async function handleCallbackQuery(callbackQuery) {
    const chatId = callbackQuery.message.chat.id;
    const data = callbackQuery.data;
    const callbackQueryId = callbackQuery.id;
    const messageId = callbackQuery.message.message_id;
    
    await api('answerCallbackQuery', { callback_query_id: callbackQueryId });
    
    if (data.startsWith('mat_price_')) {
        const priceVal = parseInt(data.split('_')[2]);
        userStates[chatId] = {
            state: 'MAT_INPUT_WIDTH',
            selected_price: priceVal
        };
        await api('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: `💵 Tanlangan narx: **${priceVal.toLocaleString('uz-UZ')} so'm**\n\n↔️ Xonaning **enini (kengligini)** kiriting (metrda, masalan: \`4\`):`,
            parse_mode: 'Markdown'
        });
        return;
    }
    
    if (data.startsWith('price_')) {
        const priceVal = parseInt(data.split('_')[1]);
        userStates[chatId] = {
            state: 'INPUT_ROOM_WIDTH',
            selected_price: priceVal
        };
        await api('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: `💵 Tanlangan narx: **${priceVal.toLocaleString('uz-UZ')} so'm**\n\n↔️ Xonangizning **enini (kengligini)** kiriting (metrda, masalan: \`4\`):`,
            parse_mode: 'Markdown'
        });
        return;
    }
    
    const productsData = loadProducts();
    
    if (data.startsWith('cat_select_')) {
        const catIndex = parseInt(data.split('_')[2]);
        const cat = productsData[catIndex];
        if (!cat) return;
        
        const inlineKeyboard = {
            inline_keyboard: [
                ...cat.items.map(item => [
                    { text: `${item.name} - ${formatPrice(item.priceValue, item.currency)}`, callback_data: `prod_select_${catIndex}_${item.id}` }
                ]),
                [{ text: "⬅️ Orqaga", callback_data: "cat_back_to_list" }]
            ]
        };
        
        await api('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: `📂 **${cat.category}** bo'limidagi mahsulotlar:\n\nBatafsil ma'tot va rasmini ko'rish uchun mahsulotni tanlang:`,
            parse_mode: 'Markdown',
            reply_markup: inlineKeyboard
        });
    } else if (data === 'cat_back_to_list') {
        const inlineKeyboard = {
            inline_keyboard: productsData.map((cat, index) => [
                { text: cat.category, callback_data: `cat_select_${index}` }
            ])
        };
        
        await api('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: "📂 **Katalog bo'limlari:**\n\nIltimos, mahsulot toifasini tanlang:",
            parse_mode: 'Markdown',
            reply_markup: inlineKeyboard
        });
    } else if (data.startsWith('prod_select_')) {
        const parts = data.split('_');
        const catIndex = parseInt(parts[2]);
        const itemId = parts.slice(3).join('_');
        
        const cat = productsData[catIndex];
        if (!cat) return;
        
        const item = cat.items.find(i => i.id === itemId);
        if (!item) return;
        
        const detailText = `🌟 **${item.name}**\n\n` +
            `📐 **O'lchami:** ${item.size || '-'}\n` +
            `📦 **O'lchov birligi:** ${item.unit || '-'}\n` +
            `💰 **Narxi:** ${formatPrice(item.priceValue, item.currency)}\n`;
            
        const inlineKeyboard = {
            inline_keyboard: [
                [{ text: "⬅️ Orqaga", callback_data: `prod_back_to_cat_${catIndex}` }]
            ]
        };
        
        // Eski ro'yxat xabarini o'chirib tashlaymiz
        try {
            await api('deleteMessage', { chat_id: chatId, message_id: messageId });
        } catch(e) {}
        
        const imageFile = item.image_file;
        const imagePath = imageFile ? path.join(__dirname, 'images', imageFile) : null;
        
        if (imagePath && fs.existsSync(imagePath)) {
            await sendPhoto(chatId, imagePath, detailText, inlineKeyboard);
        } else {
            await api('sendMessage', {
                chat_id: chatId,
                text: detailText,
                parse_mode: 'Markdown',
                reply_markup: inlineKeyboard
            });
        }
    } else if (data.startsWith('prod_back_to_cat_')) {
        const catIndex = parseInt(data.split('_')[4]);
        const cat = productsData[catIndex];
        if (!cat) return;
        
        const inlineKeyboard = {
            inline_keyboard: [
                ...cat.items.map(item => [
                    { text: `${item.name} - ${formatPrice(item.priceValue, item.currency)}`, callback_data: `prod_select_${catIndex}_${item.id}` }
                ]),
                [{ text: "⬅️ Orqaga", callback_data: "cat_back_to_list" }]
            ]
        };
        
        // Eski rasm/detal xabarini o'chirib yuboramiz
        try {
            await api('deleteMessage', { chat_id: chatId, message_id: messageId });
        } catch(e) {}
        
        // Ro'yxatni yangi xabar qilib chiqaramiz
        await api('sendMessage', {
            chat_id: chatId,
            text: `📂 **${cat.category}** bo'limidagi mahsulotlar:\n\nBatafsil ma'lumot va rasmini ko'rish uchun mahsulotni tanlang:`,
            parse_mode: 'Markdown',
            reply_markup: inlineKeyboard
        });
    }
}

// Botni ishga tushirish (Long polling)
let lastUpdateId = 0;

async function startPolling() {
    console.log("Bot muvaffaqiyatli ishga tushdi (Node.js)...");
    while (true) {
        try {
            const response = await api('getUpdates', {
                offset: lastUpdateId + 1,
                timeout: 30
            });
            if (response.ok && response.result) {
                for (const update of response.result) {
                    lastUpdateId = update.update_id;
                    if (update.message) {
                        await handleMessage(update.message);
                    } else if (update.callback_query) {
                        await handleCallbackQuery(update.callback_query);
                    }
                }
            }
        } catch (e) {
            console.error("Polling error:", e);
            // Muammo bo'lsa 3 soniya kutib qayta ulanadi
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }
}

startPolling();
