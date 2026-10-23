import gspread
import json
import re
import os

CREDS_FILE = 'creds.json'
SPREADSHEET_ID = '1BjqBFI80c9MrCZpH-9rS5fpXjdQyiIF4lOADrWOnHCU'
OUTPUT_DIR = 'data'

def parse_update_day(raw):
    """Витягує основний день і частоту оновлення."""
    raw = raw.strip()
    day = re.sub(r'\(.*?\)', '', raw).strip()
    note = ''
    match = re.search(r'\((.*?)\)', raw)
    if match:
        note = match.group(1).strip()
    return day, note

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Підключення до Google Sheets...")
    gc = gspread.service_account(CREDS_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    all_data = {}
    
    # Беремо тільки листи *_All
    worksheets = [ws for ws in sh.worksheets() if ws.title.endswith('_All')]
    
    for ws in worksheets:
        city_key = ws.title.replace('_All', '').lower()
        print(f"Обробляємо {ws.title}...")
        
        rows = ws.get_all_records()
        city_data = []
        
        for row in rows:
            url = str(row.get('Посилання', '')).strip()
            address = str(row.get('Адреса', '')).strip()
            raw_day = str(row.get('День оновлення', '')).strip()
            lat = row.get('lat', '')
            lng = row.get('lng', '')
            
            if not address:
                continue
            
            day, note = parse_update_day(raw_day)
            
            entry = {
                'address': address,
                'maps_url': url,
                'update_day': day,
                'update_note': note,
            }
            
            if lat and lng:
                try:
                    entry['lat'] = float(lat)
                    entry['lng'] = float(lng)
                except:
                    pass
            
            city_data.append(entry)
        
        all_data[city_key] = city_data
        print(f"  {len(city_data)} записів")
    
    # Зберігаємо один загальний файл
    output_path = os.path.join(OUTPUT_DIR, 'secondhands.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Збережено: {output_path}")
    print(f"Міст: {len(all_data)}, всього записів: {sum(len(v) for v in all_data.values())}")

if __name__ == '__main__':
    main()