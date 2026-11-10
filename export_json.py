import gspread
import json
import re
import os

CREDS_FILE = 'creds.json'
SPREADSHEET_ID = '1BjqBFI80c9MrCZpH-9rS5fpXjdQyiIF4lOADrWOnHCU'
OUTPUT_DIR = 'data'

# Відповідність назви листа → українська назва міста
CITY_UA = {
    'Lviv': 'Львів',
    'IF': 'Івано-Франківськ',
    'Kyiv': 'Київ',
    'Ternopil': 'Тернопіль',
    'Dnipro': 'Дніпро',
    'Odesa': 'Одеса',
    'Kharkiv': 'Харків',
    'Rivne': 'Рівне',
    'Chernivtsi': 'Чернівці',
    'Lutsk': 'Луцьк',
    'Zhytomyr': 'Житомир',
    'Khmelnytskyi': 'Хмельницький',
    'Uzhgorod': 'Ужгород',
    'Vinnytsia': 'Вінниця',
    'Cherkasy': 'Черкаси',
    'Poltava': 'Полтава',
    'Chernihiv': 'Чернігів',
    'Sumy': 'Суми',
    'Kropyvnytskyi': 'Кропивницький',
    'Mykolaiv': 'Миколаїв',
    'Kherson': 'Херсон',
}

# Нормалізація назв днів → стандартні українські (як в index.html)
DAY_NORMALIZE = {
    "Понеділок": "Понеділок",
    "Вівторок": "Вівторок",
    "Середа": "Середа",
    "Четвер": "Четвер",
    "П'ятниця": "П'ятниця",   # звичайний апостроф
    "Пʼятниця": "П'ятниця",   # типографічний апостроф
    "Субота": "Субота",
    "Неділя": "Неділя",
    # англійські варіанти (на всяк випадок)
    "monday": "Понеділок",
    "tuesday": "Вівторок",
    "wednesday": "Середа",
    "thursday": "Четвер",
    "friday": "П'ятниця",
    "saturday": "Субота",
    "sunday": "Неділя",
}

def parse_day(raw):
    """Повертає (нормалізований_день, примітка)."""
    if not raw:
        return None, None
    raw = str(raw).strip()
    for key, normalized in DAY_NORMALIZE.items():
        if raw.lower().startswith(key.lower()):
            note = raw[len(key):].strip().lstrip("(").rstrip(")").strip()
            return normalized, note or None
    return None, raw  # невідомий день → день=None, примітка=весь рядок

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Підключення до Google Sheets...")
    gc = gspread.service_account(CREDS_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)

    all_data = {}

    # Беремо тільки листи *_All
    worksheets = [ws for ws in sh.worksheets() if ws.title.endswith('_All')]

    for ws in worksheets:
        sheet_city = ws.title.replace('_All', '')
        city_ua = CITY_UA.get(sheet_city, sheet_city)  # якщо немає в словнику — лишаємо як є
        print(f"Обробляємо {ws.title} → {city_ua}...")

        rows = ws.get_all_records()
        city_data = []

        for row in rows:
            address = str(row.get('Адреса', '') or '').strip()
            if not address:
                continue

            url = str(row.get('Посилання', '') or '').strip()
            raw_day = str(row.get('День оновлення', '') or '').strip()
            lat_raw = row.get('lat', '') or row.get('Lat', '') or ''
            lng_raw = row.get('lng', '') or row.get('Lng', '') or ''
            store_id = row.get('ID', '') or row.get('id', '') or ''
            network = str(row.get('Мережа', '') or row.get('network', '') or '').strip() or None
            lux_day_raw = str(row.get('День люкс', '') or row.get('lux_day', '') or '').strip()

            update_day, update_note = parse_day(raw_day)
            lux_day, _ = parse_day(lux_day_raw)

            entry = {
                'id': int(store_id) if str(store_id).strip().isdigit() else None,
                'address': address,
                'city': city_ua,
                'maps_url': url,
                'update_day': update_day,
                'update_note': update_note,
                'network': network,
                'lux_day': lux_day,
            }

            # Координати — беремо з таблиці якщо є
            if lat_raw and lng_raw:
                try:
                    entry['lat'] = float(str(lat_raw).replace(',', '.'))
                    entry['lng'] = float(str(lng_raw).replace(',', '.'))
                except (ValueError, TypeError):
                    pass

            city_data.append(entry)

        all_data[city_ua] = city_data
        print(f"  {len(city_data)} записів")

    # Зберігаємо один загальний файл
    output_path = os.path.join(OUTPUT_DIR, 'secondhands.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Збережено: {output_path}")
    print(f"Міст: {len(all_data)}, всього записів: {sum(len(v) for v in all_data.values())}")

if __name__ == '__main__':
    main()
