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
from datetime import datetime, timedelta
from prayer_times_calculator import PrayerTimesCalculator

# Ensure we always serve files from the script's own directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force unbuffered output for logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

def log(message):
    """Print with explicit flush for immediate logging"""
    print(message, flush=True)

def get_local_ip():
    """Auto-detect the local IP address"""
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
# Load from config.json (gitignored) with defaults as fallback
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        _cfg = json.load(f)
else:
    print("⚠️  No config.json found — using defaults. Copy config.example.json to config.json and edit it.")
    _cfg = {}

SPEAKER_OR_GROUP_NAME = _cfg.get("speaker_or_group_name", ["HomeGroup"])
LOCAL_IP = get_local_ip()
PORT = _cfg.get("port", 8000)
FAJR_FILE = _cfg.get("fajr_file", "fajr_azan.mp3")
STANDARD_FILE = _cfg.get("standard_file", "standard_azan.mp3")
TEST_FILE = _cfg.get("test_file", "test-mp3.mp3")
BG_IMAGE = _cfg.get("bg_image", "makkah-1-wide-optimized.jpeg")

LAT = _cfg.get("lat", 51.5074)
LON = _cfg.get("lon", -0.1278)
LOCATION = _cfg.get("location", "London")

FAJR_VOLUME = _cfg.get("fajr_volume", 0.0)
STANDARD_VOLUME = _cfg.get("standard_volume", 0.5)

# --- TERMINAL COLORS ---
class Colors:
    GREEN  = '\033[92m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def get_device_color(device_name):
    """Return a color for a device name in terminal output"""
    return Colors.CYAN

def colorize_device_name(device_name):
    """Return the device name with its unique color"""
    color = get_device_color(device_name)
    return f"{color}{device_name}{Colors.END}"

# 1. Background Web Server
def start_server():
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print(f"{Colors.GREEN}🌐 HTTP server started on port {PORT}{Colors.END}")
            httpd.serve_forever()
    except OSError as e:
        print(f"{Colors.YELLOW}⚠️  Warning: Could not start HTTP server on port {PORT}: {e}{Colors.END}")
        print(f"{Colors.YELLOW}   If the server is already running, this is fine. Otherwise, check the port.{Colors.END}")

def ensure_server_running():
    """Start HTTP server if not already running"""
    if not hasattr(ensure_server_running, '_started'):
        threading.Thread(target=start_server, daemon=True).start()
        time.sleep(1)
        ensure_server_running._started = True

# 2. Monthly CSV Generator (Ensures offline reliability)
def is_csv_complete(filename, year, month):
    """Return True only if the CSV exists and has a row for every day in the month."""
    if not os.path.exists(filename):
        return False
    expected_days = calendar.monthrange(year, month)[1]
    try:
        with open(filename, mode='r') as f:
            row_count = sum(1 for _ in csv.DictReader(f))
        return row_count == expected_days
    except Exception:
        return False

def generate_monthly_csv(year, month, force=False):
    filename = f"prayers_{year}_{month:02d}.csv"
    if is_csv_complete(filename, year, month) and not force:
        return filename

    if os.path.exists(filename):
        os.remove(filename)
        if force:
            print(f"{Colors.YELLOW}🗑️  Removed existing file: {filename}{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  Incomplete CSV detected ({filename}), regenerating...{Colors.END}")

    print(f"{Colors.BLUE}📅 Generating local schedule for {calendar.month_name[month]} {year}...{Colors.END}")
    days_in_month = calendar.monthrange(year, month)[1]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"])

        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            try:
                calc = PrayerTimesCalculator(latitude=LAT, longitude=LON,
                                             calculation_method='mwl', date=date_str)
                p = calc.fetch_prayer_times()
                writer.writerow([f"{day:02d}/{month:02d}/{year}", p['Fajr'], p['Dhuhr'], p['Asr'], p['Maghrib'], p['Isha']])
                print(f"{Colors.CYAN}  ✓ Fetched times for {day:02d}/{month:02d}/{year}{Colors.END}")

                time.sleep(1)  # Avoid API rate limiting

            except Exception as e:
                print(f"{Colors.RED}  ✗ Error fetching day {day}: {e}{Colors.END}")
                # Optional: continue to next day or retry
    return filename

PRAYER_NAMES = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']

def load_today_prayers(csv_file):
    """Load today's prayer times from CSV. Returns dict like {'Fajr': '05:45', ...} or None."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    with open(csv_file, mode='r') as f:
        for row in csv.DictReader(f):
            if row['Date'] == today_str:
                return {p: row[p] for p in PRAYER_NAMES}
    return None

def get_next_prayer(prayers):
    """Find the next prayer from now. Returns (name, datetime) or (None, None) if all passed."""
    now = datetime.now()
    today = now.date()
    for name in PRAYER_NAMES:
        h, m = map(int, prayers[name].split(':'))
        prayer_dt = datetime.combine(today, datetime.min.time().replace(hour=h, minute=m))
        if prayer_dt > now:
            return name, prayer_dt
    return None, None

def play_azan(is_fajr, test_mode=False, prayer_name=None):
    chromecasts = []
    browser = None
    try:
        log(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        log(f"{Colors.CYAN}Starting playback request at {datetime.now().strftime('%H:%M:%S')}{Colors.END}")

        chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=list(SPEAKER_OR_GROUP_NAME), discovery_timeout=10)
        if not chromecasts:
            log(f"{Colors.RED}❌ No devices found from list: {SPEAKER_OR_GROUP_NAME}{Colors.END}")
            return

        device_list = [colorize_device_name(cast.name) for cast in chromecasts]
        log(f"{Colors.GREEN}✅ Found {len(chromecasts)} device(s):{Colors.END}")
        for device_info in device_list:
            log(f"   {device_info}")

        # Set volume based on prayer type
        volume = FAJR_VOLUME if is_fajr else STANDARD_VOLUME

        if test_mode:
            # Use the real azan file — test-mp3.mp3 is too short (3s) for group sync delay
            file = FAJR_FILE if is_fajr else STANDARD_FILE
            if not os.path.exists(file):
                file = STANDARD_FILE
            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
                log(f"{Colors.BOLD}{Colors.BLUE}🎵 Playing {prayer_name} Azan (test){Colors.END}")
            else:
                title_text = "Test Azan"
                artist_text = f"{LOCATION} Prayer Time"
        else:
            file = FAJR_FILE if is_fajr else STANDARD_FILE
            # Fallback to standard file if Fajr file doesn't exist
            if not os.path.exists(file):
                if is_fajr:
                    log(f"{Colors.YELLOW}⚠️  Note: {FAJR_FILE} not found, using {STANDARD_FILE}{Colors.END}")
                file = STANDARD_FILE

            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
                log(f"{Colors.BOLD}{Colors.BLUE}🕌 Playing {prayer_name} Azan{Colors.END}")
            else:
                title_text = "Fajr Azan" if is_fajr else "Prayer Azan"
                artist_text = f"{LOCATION} Prayer Time"

        url = f"http://{LOCAL_IP}:{PORT}/{file}"
        thumb_url = f"http://{LOCAL_IP}:{PORT}/{BG_IMAGE}"

        log(f"{Colors.CYAN}📡 Audio URL: {url}{Colors.END}")
        log(f"{Colors.CYAN}🖼️  Image URL: {thumb_url}{Colors.END}")

        # Play on all devices simultaneously
        media_controllers = []
        log(f"\n{Colors.BOLD}Attempting to play on {len(chromecasts)} device(s)...{Colors.END}\n")

        for cast in chromecasts:
            try:
                cast.wait()
                colored_name = colorize_device_name(cast.name)
                log(f"{Colors.CYAN}📱 Device: {colored_name}, Type: {cast.cast_type}, Model: {cast.model_name}{Colors.END}")

                # Stop any existing playback first
                mc = cast.media_controller
                mc.update_status()
                if mc.status.player_state in ['PLAYING', 'BUFFERING', 'PAUSED']:
                    log(f"{Colors.YELLOW}⏹️  Stopping existing playback on {colored_name}...{Colors.END}")
                    mc.stop()
                    time.sleep(0.3)

                cast.set_volume(volume)
                log(f"{Colors.GREEN}🔊 Volume set to {int(volume * 100)}% on {colored_name}{Colors.END}")

                # Groups broadcast metadata to every member including audio-only devices,
                # so skip images to avoid audio speakers dropping out.
                # Single display devices get full cover art.
                is_group = cast.cast_type == 'group'
                is_audio_only = 'audio' in cast.model_name.lower() or 'mini' in cast.model_name.lower()
                use_images = not is_group and not is_audio_only

                metadata = {
                    'metadataType': 3,
                    'title': title_text,
                    'artist': artist_text,
                    'albumName': 'Daily Prayers'
                }
                if use_images:
                    metadata['images'] = [{'url': thumb_url}]

                if is_group:
                    log(f"{Colors.CYAN}👥 Group cast — skipping cover art to keep all members in sync{Colors.END}")
                elif is_audio_only:
                    log(f"{Colors.CYAN}🎧 Audio-only device — no cover art{Colors.END}")

                log(f"{Colors.YELLOW}🎬 Sending play command to {colored_name}...{Colors.END}")
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
                # Wait for media to become active (with hard timeout)
                wait_start = time.time()
                while time.time() - wait_start < 15:
                    mc.update_status()
                    if mc.status and mc.status.player_state in ['PLAYING', 'BUFFERING']:
                        break
                    time.sleep(0.5)
                log(f"{Colors.GREEN}✅ Started playing {title_text} on {colored_name}{Colors.END}")
                media_controllers.append((mc, cast.name))

                # Small delay between devices to avoid conflicts
                time.sleep(0.5)
            except Exception as e:
                colored_name_err = colorize_device_name(cast.name)
                log(f"{Colors.RED}❌ Error playing on {colored_name_err}: {e}{Colors.END}")
                traceback.print_exc()

        log(f"\n{Colors.GREEN}✅ Playback initiated on {len(media_controllers)} device(s){Colors.END}")
        log(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

    except Exception as e:
        log(f"{Colors.RED}❌ Cast Error: {e}{Colors.END}")
        traceback.print_exc()

    finally:
        # Always disconnect cast objects — stops their background socket threads.
        # Without this, the socket client keeps trying to reconnect using a
        # zeroconf instance that has already been stopped, spinning the CPU.
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

# 3. Main Loop
print(f"{Colors.BOLD}{Colors.GREEN}🕌 Azan System Active for {LOCATION} coordinates{Colors.END}")
print(f"{Colors.CYAN}📡 Using IP address: {LOCAL_IP}:{PORT}{Colors.END}")

# Check for force regenerate CSV mode (no server needed)
if '--force' in sys.argv:
    print(f"{Colors.BLUE}🔄 Force regenerating CSV for current month...{Colors.END}")
    now = datetime.now()
    generate_monthly_csv(now.year, now.month, force=True)
    print(f"{Colors.GREEN}✅ CSV regeneration completed. Exiting.{Colors.END}")
    sys.exit(0)

# All modes below need the HTTP server
ensure_server_running()

# Check for test mode — mimics the real next azan
if '--test' in sys.argv:
    print(f"{Colors.BLUE}🧪 Test mode: finding next prayer to simulate...{Colors.END}")
    now = datetime.now()
    test_csv = generate_monthly_csv(now.year, now.month)
    test_prayers = load_today_prayers(test_csv)
    if test_prayers:
        test_name, _ = get_next_prayer(test_prayers)
        if test_name is None:
            test_name = 'Isha'  # Fallback if all prayers passed today
    else:
        test_name = 'Maghrib'  # Fallback if no CSV data
    print(f"{Colors.BLUE}🕌 Simulating {test_name} azan...{Colors.END}")
    play_azan(is_fajr=(test_name == 'Fajr'), test_mode=True, prayer_name=test_name)
    time.sleep(30)
    print(f"{Colors.GREEN}✅ Test completed. Exiting.{Colors.END}")
    sys.exit(0)

# Check for test prayer mode
if '--test-prayer' in sys.argv:
    try:
        prayer_index = sys.argv.index('--test-prayer')
        prayer_name = sys.argv[prayer_index + 1] if prayer_index + 1 < len(sys.argv) else "Maghrib"
    except (ValueError, IndexError):
        prayer_name = "Maghrib"

    print(f"{Colors.BLUE}🧪 Running test with {prayer_name} prayer display...{Colors.END}")
    is_fajr = prayer_name.lower() == 'fajr'
    play_azan(is_fajr=is_fajr, test_mode=True, prayer_name=prayer_name)
    time.sleep(30)
    print(f"{Colors.GREEN}✅ Test completed. Exiting.{Colors.END}")
    sys.exit(0)

# Normal scheduling mode
cached_date = None
prayers_today = None

while True:
    now = datetime.now()

    # Reload prayer times when the date changes
    if cached_date != now.date():
        cached_date = now.date()
        current_csv = generate_monthly_csv(now.year, now.month)
        prayers_today = load_today_prayers(current_csv)

        if prayers_today is None:
            log(f"{Colors.RED}❌ No prayer times found for {now.strftime('%d/%m/%Y')}{Colors.END}")
            time.sleep(60)
            continue

        log(f"\n{Colors.BOLD}{Colors.GREEN}📅 Prayer schedule for {now.strftime('%d/%m/%Y')}:{Colors.END}")
        for name in PRAYER_NAMES:
            log(f"   {Colors.CYAN}{name:10s} {prayers_today[name]}{Colors.END}")

        # Delete previous month's CSV on the 1st
        if now.day == 1:
            prev_month = now.replace(day=1) - timedelta(days=1)
            prev_csv = f"prayers_{prev_month.year}_{prev_month.month:02d}.csv"
            if os.path.exists(prev_csv):
                os.remove(prev_csv)
                log(f"{Colors.YELLOW}🗑️  Deleted old schedule: {prev_csv}{Colors.END}")

        # Pre-generate next month's CSV in the last 2 days of the month
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        if now.day >= days_in_month - 1:
            next_month = now.replace(day=1) + timedelta(days=days_in_month)
            generate_monthly_csv(next_month.year, next_month.month)

    # Find the next prayer
    next_name, next_dt = get_next_prayer(prayers_today)

    if next_name is None:
        # All prayers for today have passed — sleep until midnight
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        wait_secs = (tomorrow - now).total_seconds() + 1
        log(f"{Colors.YELLOW}🌙 All prayers done for today. Sleeping until midnight ({int(wait_secs)}s)...{Colors.END}")
        time.sleep(wait_secs)
        continue

    wait_secs = (next_dt - now).total_seconds()
    hours, remainder = divmod(int(wait_secs), 3600)
    minutes = remainder // 60
    log(f"{Colors.BOLD}{Colors.CYAN}⏳ Next prayer: {next_name} at {prayers_today[next_name]} (in {hours}h {minutes}m){Colors.END}")

    # Sleep until the prayer time
    time.sleep(max(wait_secs, 0))

    # Play the azan
    log(f"{Colors.BOLD}{Colors.BLUE}🕌 It is time for {next_name} ({prayers_today[next_name]}){Colors.END}")
    play_azan(is_fajr=(next_name == 'Fajr'), prayer_name=next_name)

    # Wait 61s to avoid re-triggering for the same prayer
    time.sleep(61)