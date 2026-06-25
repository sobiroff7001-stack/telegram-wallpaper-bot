import math

def calculate_wallpaper(room_width, room_length, room_height, roll_width=1.06, roll_length=10.0, pattern_repeat=0):
    """
    Xona o'lchamlari bo'yicha kerakli aboy (gulqog'oz) rulonlari sonini hisoblaydi.
    
    Parametrlar:
    - room_width (float): Xonaning kengligi (metrda).
    - room_length (float): Xonaning uzunligi (metrda).
    - room_height (float): Xonaning balandligi (metrda).
    - roll_width (float): Aboy rulonining eni (metrda, standart: 1.06m yoki 0.53m).
    - roll_length (float): Aboy rulonining uzunligi (metrda, standart: 10.0m).
    - pattern_repeat (float): Aboy guli (naqsh) takrorlanishi (metrda, agar gulini to'g'rilash kerak bo'lsa).
    
    Qaytaradi:
    - dict: Hisoblash natijalari va tafsilotlari.
    """
    perimeter = 2 * (room_width + room_length)
    
    # Xona perimetrini qoplash uchun kerak bo'ladigan chiziqlar (polosa) soni
    stripes_needed = math.ceil(perimeter / roll_width)
    
    # Bitta rulondan chiqadigan to'liq chiziqlar soni
    # Agar gulini to'g'rilash (pattern matching) kerak bo'lsa, har bir chiziqqa guli takrorlanishi qo'shiladi
    cut_length = room_height
    if pattern_repeat > 0:
        cut_length = room_height + pattern_repeat
        
    stripes_per_roll = math.floor(roll_length / cut_length)
    
    # Agar xona balandligi juda baland bo'lsa (bitta rulondan ham uzun bo'lsa), kamida 1 deb olamiz
    if stripes_per_roll < 1:
        stripes_per_roll = 1
        
    # Jami kerak bo'ladigan rulonlar soni
    rolls_needed = math.ceil(stripes_needed / stripes_per_roll)
    
    # Umumiy devor yuzasi (eshik va oynalarni hisobga olmaganda)
    total_area = perimeter * room_height
    
    return {
        'perimeter': round(perimeter, 2),
        'stripes_needed': stripes_needed,
        'stripes_per_roll': stripes_per_roll,
        'rolls_needed': rolls_needed,
        'total_area': round(total_area, 2)
    }

def calculate_wallpaper_by_perimeter(perimeter, room_height, roll_width=1.06, roll_length=10.0, pattern_repeat=0):
    """
    Perimetr va balandlik bo'yicha kerakli aboy rulonlari sonini hisoblaydi.
    """
    stripes_needed = math.ceil(perimeter / roll_width)
    cut_length = room_height
    if pattern_repeat > 0:
        cut_length = room_height + pattern_repeat
        
    stripes_per_roll = math.floor(roll_length / cut_length)
    if stripes_per_roll < 1:
        stripes_per_roll = 1
        
    rolls_needed = math.ceil(stripes_needed / stripes_per_roll)
    total_area = perimeter * room_height
    
    return {
        'perimeter': round(perimeter, 2),
        'stripes_needed': stripes_needed,
        'stripes_per_roll': stripes_per_roll,
        'rolls_needed': rolls_needed,
        'total_area': round(total_area, 2)
    }
