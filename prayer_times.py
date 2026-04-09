#!/usr/bin/env python3
import time
import csv
import os
import sys
import json
import threading
import traceback
import http.server
import socketserver
import pychromecast
import calendar
import socket
import urllib.request
from datetime import datetime, timedelta

# --- MODE SELECTION ---
# Run with --json   to fetch timetable from my-masjid.com (once per year)
# Run with --longlat to calculate from coordinates using prayer_times_calculator
USE_JSON_MODE = '--json' in sys.argv

if not USE_JSON_MODE:
    try:
        from prayer_times_calculator import PrayerTimesCalculator
    except ImportError:
        print('{"level":"error","msg":"missing_dependency","package":"prayer-times-calculator","hint":"pip install prayer-times-calculator or use --json mode"}', flush=True)
        sys.exit(1)

# Ensure we always serve files from the script's own directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force unbuffered output for logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

def _log(level, msg, **fields):
    entry = {"ts": datetime.now().isoformat(timespec='seconds'), "level": level, "msg": msg}
    if fields:
        entry.update(fields)
    print(json.dumps(entry), flush=True)

def log_info(msg, **fields):  _log("info",  msg, **fields)
def log_warn(msg, **fields):  _log("warn",  msg, **fields)
def log_error(msg, **fields): _log("error", msg, **fields)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"

# --- CONFIGURATION ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        _cfg = json.load(f)
else:
    log_warn("config_missing", hint="copy config.example.json to config.json and edit it")
    _cfg = {}

SPEAKER_OR_GROUP_NAME = _cfg.get("speaker_or_group_name", ["HomeGroup"])
LOCAL_IP = get_local_ip()
PORT = _cfg.get("port", 8000)
FAJR_FILE = _cfg.get("fajr_file", "fajr_azan.mp3")
STANDARD_FILE = _cfg.get("standard_file", "standard_azan.mp3")
TEST_FILE = _cfg.get("test_file", "test-mp3.mp3")
BG_IMAGE = _cfg.get("bg_image", "makkah-1-wide-optimized.jpeg")
LOCATION = _cfg.get("location", "Stevenage")

FAJR_VOLUME = _cfg.get("fajr_volume", 0.0)
STANDARD_VOLUME = _cfg.get("standard_volume", 0.5)

# JSON mode config
MASJID_GUID = _cfg.get("masjid_guid", "3bf29ae9-f0ee-490f-bdb0-1a12695a2dd8")

# Longlat mode config
LAT = _cfg.get("lat", 51.5074)
LON = _cfg.get("lon", -0.1278)

# 1. Background Web Server
def start_server():
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            log_info("http_server_start", port=PORT)
            httpd.serve_forever()
    except OSError as e:
        log_warn("http_server_error", port=PORT, error=str(e))

def ensure_server_running():
    if not hasattr(ensure_server_running, '_started'):
        threading.Thread(target=start_server, daemon=True).start()
        time.sleep(1)
        ensure_server_running._started = True

# 2a. JSON mode — fetch once a year, store as timetable_{year}.json
def fetch_and_save_timetable(year):
    """Fetch full-year timetable from my-masjid.com and save to timetable_{year}.json."""
    url = (f"https://time.my-masjid.com/api/TimingsInfoScreen/"
           f"GetMasjidMultipleTimings?GuidId={MASJID_GUID}")
    log_info("timetable_fetch", source="my-masjid.com", year=year)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())

    model = data['model']
    jumah_time = model['masjidSettings'].get('jumahTime', '')
    masjid_name = model['masjidDetails'].get('name', '')

    days = {}
    for entry in model['salahTimings']:
        def _t(salah, field='salahTime', e=entry):
            items = e.get(salah, [])
            return items[0].get(field) or '' if items else ''
        key = f"{entry['day']:02d}/{entry['month']:02d}"
        days[key] = {
            'Fajr':           _t('fajr'),
            'Fajr_Iqamah':    _t('fajr',    'iqamahTime'),
            'Dhuhr':          _t('zuhr'),
            'Dhuhr_Iqamah':   _t('zuhr',    'iqamahTime'),
            'Asr':            _t('asr'),
            'Asr_Iqamah':     _t('asr',     'iqamahTime'),
            'Maghrib':        _t('maghrib'),
            'Maghrib_Iqamah': _t('maghrib', 'iqamahTime'),
            'Isha':           _t('isha'),
            'Isha_Iqamah':    _t('isha',    'iqamahTime'),
            'Sunrise':        _t('shouruq'),
            'Jumah':          jumah_time,
        }

    timetable = {
        'year': year,
        'fetched': datetime.now().strftime('%Y-%m-%d'),
        'masjid': masjid_name,
        'days': days,
    }
    filename = f"timetable_{year}.json"
    with open(filename, 'w') as f:
        json.dump(timetable, f, indent=2)
    log_info("timetable_saved", file=filename, days=len(days), masjid=masjid_name)
    return timetable

def ensure_timetable(year, force=False):
    """Return loaded timetable for year, fetching from API if the file is missing, forced, or stale (>30 days)."""
    filename = f"timetable_{year}.json"
    if not force and os.path.exists(filename):
        with open(filename) as f:
            timetable = json.load(f)
        try:
            fetched = datetime.strptime(timetable['fetched'], '%Y-%m-%d')
            if (datetime.now() - fetched).days <= 30:
                return timetable
            log_info("timetable_stale", last_fetched=timetable['fetched'], action="refreshing")
        except (KeyError, ValueError):
            pass
    return fetch_and_save_timetable(year)

# 2b. Longlat mode — monthly CSV from PrayerTimesCalculator
LONGLAT_CSV_FIELDS = ["Date", "Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

def is_csv_complete(filename, year, month):
    if not os.path.exists(filename):
        return False
    expected_days = calendar.monthrange(year, month)[1]
    try:
        with open(filename, mode='r') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != LONGLAT_CSV_FIELDS:
                return False
            row_count = sum(1 for _ in reader)
        return row_count == expected_days
    except Exception:
        return False

def generate_monthly_csv(year, month, force=False):
    filename = f"prayers_{year}_{month:02d}.csv"
    if is_csv_complete(filename, year, month) and not force:
        return filename

    if os.path.exists(filename):
        os.remove(filename)
        action = "force_regenerate" if force else "regenerate_incomplete"
        log_info("csv_removed", file=filename, reason=action)

    log_info("csv_generate", year=year, month=month, lat=LAT, lon=LON)
    days_in_month = calendar.monthrange(year, month)[1]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(LONGLAT_CSV_FIELDS)
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            try:
                utc_offset = datetime(year, month, day, 12).astimezone().utcoffset().total_seconds() / 3600
                calc = PrayerTimesCalculator(latitude=LAT, longitude=LON,
                                             calculation_method='mwl', date=date_str,
                                             time_zone=utc_offset)
                p = calc.fetch_prayer_times()
                writer.writerow([f"{day:02d}/{month:02d}/{year}",
                                  p['Fajr'], p['Dhuhr'], p['Asr'], p['Maghrib'], p['Isha']])
                log_info("csv_day_ok", date=date_str)
                time.sleep(1)  # Avoid API rate limiting
            except Exception as e:
                log_error("csv_day_error", date=date_str, error=str(e))
    return filename

def load_today_prayers_csv(csv_file):
    today_str = datetime.now().strftime("%d/%m/%Y")
    with open(csv_file, mode='r') as f:
        for row in csv.DictReader(f):
            if row['Date'] == today_str:
                return dict(row)
    return None

# 3. Shared scheduling
PRAYER_NAMES = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']

def get_next_prayer(prayers):
    now = datetime.now()
    today = now.date()
    for name in PRAYER_NAMES:
        h, m = map(int, prayers[name].split(':'))
        prayer_dt = datetime.combine(today, datetime.min.time().replace(hour=h, minute=m))
        if prayer_dt > now:
            return name, prayer_dt
    return None, None

def play_azan(is_fajr, test_mode=False, prayer_name=None, iqamah_time=None):
    chromecasts = []
    browser = None
    try:
        log_info("playback_start", prayer=prayer_name, test=test_mode)

        chromecasts, browser = pychromecast.get_listed_chromecasts(
            friendly_names=list(SPEAKER_OR_GROUP_NAME), discovery_timeout=10)
        if not chromecasts:
            log_error("playback_no_devices", targets=list(SPEAKER_OR_GROUP_NAME))
            return

        log_info("playback_devices_found", count=len(chromecasts),
                 devices=[c.name for c in chromecasts])

        volume = FAJR_VOLUME if is_fajr else STANDARD_VOLUME

        # Build display text across all 3 Cast metadata fields:
        #   title     → "{Prayer} Prayer"
        #   artist    → "It's time for {Prayer} in {Location}"
        #   albumName → "Iqamah {time}" if available, else "Daily Prayers"
        # Cast metadata is UTF-8; emoji render on Nest Hub screen and in the Home app.
        album_text = f"🧎🏽‍♂️ Iqamah {iqamah_time} 🤲🏽" if iqamah_time else "Daily Prayers"

        if test_mode:
            file = FAJR_FILE if is_fajr else STANDARD_FILE
            if not os.path.exists(file):
                file = STANDARD_FILE
            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
            else:
                title_text = "Test Azan"
                artist_text = f"{LOCATION} Prayer Time"
        else:
            file = FAJR_FILE if is_fajr else STANDARD_FILE
            if not os.path.exists(file):
                if is_fajr:
                    log_warn("fajr_file_missing", fallback=STANDARD_FILE, missing=FAJR_FILE)
                file = STANDARD_FILE

            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
            else:
                title_text = "Fajr Azan" if is_fajr else "Prayer Azan"
                artist_text = f"{LOCATION} Prayer Time"

        current_ip = get_local_ip()
        url = f"http://{current_ip}:{PORT}/{file}"
        thumb_url = f"http://{current_ip}:{PORT}/{BG_IMAGE}"

        log_info("playback_urls", audio=url, image=thumb_url, ip=current_ip)

        media_controllers = []

        for cast in chromecasts:
            try:
                cast.wait()
                log_info("playback_device_connect", device=cast.name,
                         type=cast.cast_type, model=cast.model_name)

                mc = cast.media_controller
                mc.update_status()
                if mc.status.player_state in ['PLAYING', 'BUFFERING', 'PAUSED']:
                    log_info("playback_stop_existing", device=cast.name,
                             state=mc.status.player_state)
                    mc.stop()
                    time.sleep(0.3)

                cast.set_volume(volume)
                log_info("playback_volume_set", device=cast.name, volume=round(volume, 2))

                is_group = cast.cast_type == 'group'
                is_audio_only = 'audio' in cast.model_name.lower() or 'mini' in cast.model_name.lower()
                use_images = not is_group and not is_audio_only

                metadata = {
                    'metadataType': 3,
                    'title': title_text,
                    'artist': artist_text,
                    'albumName': album_text,
                }
                if use_images:
                    metadata['images'] = [{'url': thumb_url}]

                if is_group:
                    log_info("playback_no_art", device=cast.name, reason="group_cast")
                elif is_audio_only:
                    log_info("playback_no_art", device=cast.name, reason="audio_only")

                log_info("playback_send", device=cast.name, title=title_text)
                mc.play_media(
                    url,
                    'audio/mpeg',
                    title=title_text,
                    thumb=thumb_url if use_images else None,
                    current_time=0,
                    autoplay=True,
                    stream_type='LIVE',
                    metadata=metadata
                )
                wait_start = time.time()
                while time.time() - wait_start < 15:
                    mc.update_status()
                    if mc.status and mc.status.player_state in ['PLAYING', 'BUFFERING']:
                        break
                    time.sleep(0.5)
                log_info("playback_ok", device=cast.name, title=title_text)
                media_controllers.append((mc, cast.name))

                time.sleep(0.5)
            except Exception as e:
                log_error("playback_device_error", device=cast.name, error=str(e))
                traceback.print_exc()

        log_info("playback_complete", devices_succeeded=len(media_controllers))

    except Exception as e:
        log_error("playback_error", error=str(e))
        traceback.print_exc()

    finally:
        for cast in chromecasts:
            try:
                cast.disconnect()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.stop_discovery()
            except Exception:
                pass

# --- STARTUP ---
mode_label = "my-masjid.com JSON" if USE_JSON_MODE else f"lon/lat ({LAT}, {LON})"
log_info("service_start",
         location=LOCATION,
         mode=mode_label,
         config=CONFIG_FILE,
         devices=list(SPEAKER_OR_GROUP_NAME),
         ip=LOCAL_IP,
         port=PORT)

# --force: re-fetch timetable (JSON mode) or regenerate current month CSV (longlat mode)
if '--force' in sys.argv:
    now = datetime.now()
    if USE_JSON_MODE:
        log_info("force_refresh", source="my-masjid.com")
        ensure_timetable(now.year, force=True)
    else:
        log_info("force_refresh", source="longlat_csv")
        generate_monthly_csv(now.year, now.month, force=True)
    log_info("force_refresh_done")
    sys.exit(0)

# All modes below need the HTTP server
ensure_server_running()

# --test: simulate the next upcoming prayer
if '--test' in sys.argv:
    log_info("test_mode_start")
    now = datetime.now()
    if USE_JSON_MODE:
        timetable = ensure_timetable(now.year)
        test_prayers = timetable['days'].get(now.strftime("%d/%m"))
    else:
        test_csv = generate_monthly_csv(now.year, now.month)
        test_prayers = load_today_prayers_csv(test_csv)

    if test_prayers:
        test_name, _ = get_next_prayer(test_prayers)
        if test_name is None:
            test_name = 'Isha'
    else:
        test_name = 'Maghrib'
    iqamah_time = (test_prayers.get(f'{test_name}_Iqamah') or None) if (USE_JSON_MODE and test_prayers) else None
    log_info("test_simulate", prayer=test_name)
    play_azan(is_fajr=(test_name == 'Fajr'), test_mode=True,
              prayer_name=test_name, iqamah_time=iqamah_time)
    time.sleep(30)
    log_info("test_complete")
    sys.exit(0)

# --test-prayer NAME: test a specific named prayer
if '--test-prayer' in sys.argv:
    try:
        prayer_index = sys.argv.index('--test-prayer')
        prayer_name = sys.argv[prayer_index + 1] if prayer_index + 1 < len(sys.argv) else "Maghrib"
    except (ValueError, IndexError):
        prayer_name = "Maghrib"

    log_info("test_prayer_start", prayer=prayer_name)
    is_fajr = prayer_name.lower() == 'fajr'
    iqamah_time = None
    try:
        now = datetime.now()
        if USE_JSON_MODE:
            timetable = ensure_timetable(now.year)
            today_prayers = timetable['days'].get(now.strftime("%d/%m"), {})
        else:
            test_csv = generate_monthly_csv(now.year, now.month)
            today_prayers = load_today_prayers_csv(test_csv) or {}
        iqamah_time = today_prayers.get(f'{prayer_name}_Iqamah') or None if USE_JSON_MODE else None
    except Exception:
        pass

    play_azan(is_fajr=is_fajr, test_mode=True, prayer_name=prayer_name, iqamah_time=iqamah_time)
    time.sleep(30)
    log_info("test_complete")
    sys.exit(0)

# Normal scheduling mode
cached_date = None
prayers_today = None
timetable = None   # JSON mode: full-year timetable kept in memory
cached_year = None  # JSON mode: year the timetable was loaded for

while True:
    now = datetime.now()

    # Reload prayer times when the date changes
    if cached_date != now.date():
        cached_date = now.date()

        if USE_JSON_MODE:
            # Re-check timetable daily; ensure_timetable will re-fetch if stale (>30d) or missing
            year_changed = cached_year != now.year
            timetable = ensure_timetable(now.year)
            cached_year = now.year
            if year_changed:
                prev_file = f"timetable_{now.year - 1}.json"
                if os.path.exists(prev_file):
                    os.remove(prev_file)
                    log_info("timetable_old_removed", file=prev_file)
            prayers_today = timetable['days'].get(now.strftime("%d/%m"))
        else:
            current_csv = generate_monthly_csv(now.year, now.month)
            prayers_today = load_today_prayers_csv(current_csv)

        if prayers_today is None:
            log_error("schedule_missing", date=now.strftime('%Y-%m-%d'))
            time.sleep(60)
            continue

        schedule = {name: prayers_today[name] for name in PRAYER_NAMES}
        sunrise = prayers_today.get('Sunrise')
        if sunrise:
            schedule['Sunrise'] = sunrise
        jumah = prayers_today.get('Jumah')
        if jumah:
            schedule['Jumah'] = jumah
        log_info("schedule_loaded", date=now.strftime('%Y-%m-%d'), **schedule)

        if not USE_JSON_MODE:
            # Delete previous month's CSV on the 1st
            if now.day == 1:
                prev_month = now.replace(day=1) - timedelta(days=1)
                prev_csv = f"prayers_{prev_month.year}_{prev_month.month:02d}.csv"
                if os.path.exists(prev_csv):
                    os.remove(prev_csv)
                    log_info("csv_old_removed", file=prev_csv)

            # Pre-generate next month's CSV in the last 2 days of the month
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            if now.day >= days_in_month - 1:
                next_month = now.replace(day=1) + timedelta(days=days_in_month)
                generate_monthly_csv(next_month.year, next_month.month)

    # Find the next prayer
    next_name, next_dt = get_next_prayer(prayers_today)

    if next_name is None:
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        wait_secs = (tomorrow - now).total_seconds() + 1
        log_info("prayers_done", wait_seconds=int(wait_secs))
        time.sleep(wait_secs)
        continue

    wait_secs = (next_dt - now).total_seconds()
    log_info("next_prayer", prayer=next_name, at=prayers_today[next_name],
             wait_seconds=int(wait_secs))

    time.sleep(max(wait_secs, 0))

    log_info("prayer_time", prayer=next_name, scheduled=prayers_today[next_name])
    iqamah_time = prayers_today.get(f'{next_name}_Iqamah') or None if USE_JSON_MODE else None
    play_azan(is_fajr=(next_name == 'Fajr'), prayer_name=next_name, iqamah_time=iqamah_time)

    # Wait 61s to avoid re-triggering for the same prayer
    time.sleep(61)
