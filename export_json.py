import gspread
import json
import re
import os
import requests
import time

CREDS_FILE = 'creds.json'
SPREADSHEET_ID = '1BjqBFI80c9MrCZpH-9rS5fpXjdQyiIF4lOADrWOnHCU'
OUTPUT_DIR = 'data'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    )
}

COORD_PATTERNS = [
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",
    r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)",
    r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)",
]

def extract_coordinates(url: str):
    for pattern in COORD_PATTERNS:
        match = re.search(pattern, url)
        if match:
            try:
                return float(match.group(1)), float(match.group(2))
            except ValueError:
                continue
    return None

def resolve_coords(session, maps_url: str):
    """Розгортає URL і витягує координати. Повертає (lat, lng) або None."""
    try:
        response = session.head(maps_url, allow_redirects=True, timeout=10)
        coords = extract_coordinates(response.url)
        if not coords:
            response = session.get(maps_url, allow_redirects=True, timeout=10)
            coords = extract_coordinates(response.url)
        return coords
    except Exception:
        return None

def parse_update_day(raw):
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

    session = requests.Session()
    session.headers.update(HEADERS)

    all_data = {}
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
            lat_sheet = row.get('lat', '')
            lng_sheet = row.get('lng', '')
            network = str(row.get('network', '')).strip()
            hours = str(row.get('hours', '')).strip()
            lux_day = str(row.get('lux_day', '')).strip()

            if not address:
                continue

            day, note = parse_update_day(raw_day)

            entry = {
                'address': address,
                'maps_url': url,
                'update_day': day,
                'update_note': note,
            }

            # Спочатку пробуємо витягти з URL, fallback — Sheets
            coords = None
            if url:
                coords = resolve_coords(session, url)
                time.sleep(0.2)

            if coords:
                entry['lat'] = coords[0]
                entry['lng'] = coords[1]
            elif lat_sheet and lng_sheet:
                try:
                    entry['lat'] = float(lat_sheet)
                    entry['lng'] = float(lng_sheet)
                except (ValueError, TypeError):
                    pass

            if network:
                entry['network'] = network
            if hours:
                entry['hours'] = hours
            if lux_day:
                entry['lux_day'] = lux_day

            city_data.append(entry)

        all_data[city_key] = city_data
        print(f"  {len(city_data)} записів")

    output_path = os.path.join(OUTPUT_DIR, 'secondhands.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Збережено: {output_path}")
    print(f"Міст: {len(all_data)}, всього записів: {sum(len(v) for v in all_data.values())}")

if __name__ == '__main__':
    main()
