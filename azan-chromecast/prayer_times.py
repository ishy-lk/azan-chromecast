import time
import csv
import os
import sys
import threading
import http.server
import socketserver
import pychromecast
import calendar
import socket
from datetime import datetime
from prayer_times_calculator import PrayerTimesCalculator

# Force unbuffered output for logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

def log(message):
    """Print with explicit flush for immediate logging"""
    print(message, flush=True)

def get_local_ip():
    """Auto-detect the local IP address"""
    try:
        # Create a socket connection to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS, doesn't actually send data
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost

# --- CONFIGURATION ---
SPEAKER_NAMES = ["Living Room Display", "Red Room Mini"]  # Add your second device name here
LOCAL_IP = get_local_ip()  # Auto-detect local IP
PORT = 8000
FAJR_FILE = "fajr_azan.mp3"
STANDARD_FILE = "standard_azan.mp3"
TEST_FILE = "test-mp3.mp3"  # For testing purposes
BG_IMAGE = "makkah-1-wide-optimized.jpeg"  # Optimized image for faster loading

# Coordinates for Stevenage
LAT = 51.915949
LON = -0.181703
LOCATION = "Stevenage"

# Volume settings (0.0 to 1.0)
FAJR_VOLUME = 0.2  # 20% for early morning
STANDARD_VOLUME = 0.5  # 50% for other prayers

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
    """Return the appropriate color for a device name"""
    if 'Red Room' in device_name:
        return Colors.RED
    elif 'Living Room' in device_name:
        return Colors.YELLOW
    else:
        return Colors.CYAN  # Default color for other devices

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

threading.Thread(target=start_server, daemon=True).start()
time.sleep(1)  # Give server time to start

# 2. Monthly CSV Generator (Ensures offline reliability)
def generate_monthly_csv(year, month):
    filename = f"prayers_{year}_{month:02d}.csv"
    if os.path.exists(filename):
        return filename

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

                # --- ADD THIS LINE ---
                time.sleep(1) # Wait 1 second between days to avoid API errors
                # ---------------------

            except Exception as e:
                print(f"{Colors.RED}  ✗ Error fetching day {day}: {e}{Colors.END}")
                # Optional: continue to next day or retry
    return filename

def play_azan(is_fajr, test_mode=False, prayer_name=None):
    try:
        log(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        log(f"{Colors.CYAN}Starting playback request at {datetime.now().strftime('%H:%M:%S')}{Colors.END}")

        chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=SPEAKER_NAMES)
        if not chromecasts:
            log(f"{Colors.RED}❌ No devices found from list: {SPEAKER_NAMES}{Colors.END}")
            return

        device_list = [colorize_device_name(cast.name) for cast in chromecasts]
        log(f"{Colors.GREEN}✅ Found {len(chromecasts)} device(s):{Colors.END}")
        for device_info in device_list:
            log(f"   {device_info}")

        # Set volume based on prayer type
        volume = FAJR_VOLUME if is_fajr else STANDARD_VOLUME

        if test_mode:
            file = TEST_FILE
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

                # Check if device supports images (has a display)
                is_audio_only = 'audio' in cast.model_name.lower() or 'mini' in cast.model_name.lower()

                # Build metadata based on device capabilities
                if is_audio_only:
                    # Simpler metadata for audio-only devices
                    metadata = {
                        'metadataType': 3,
                        'title': title_text,
                        'artist': artist_text,
                        'albumName': 'Daily Prayers'
                    }
                    log(f"{Colors.CYAN}🎧 Using audio-only metadata for {colored_name}{Colors.END}")
                else:
                    # Full metadata with images for display-capable devices
                    metadata = {
                        'metadataType': 3,
                        'title': title_text,
                        'artist': artist_text,
                        'albumName': 'Daily Prayers',
                        'images': [
                            {
                                'url': thumb_url
                            }
                        ]
                    }

                log(f"{Colors.YELLOW}🎬 Sending play command to {colored_name}...{Colors.END}")
                mc.play_media(
                    url,
                    'audio/mp3',
                    title=title_text,
                    thumb=thumb_url if not is_audio_only else None,
                    current_time=0,
                    autoplay=True,
                    stream_type='BUFFERED',
                    metadata=metadata
                )
                mc.block_until_active()
                log(f"{Colors.GREEN}✅ Started playing {title_text} on {colored_name}{Colors.END}")
                media_controllers.append((mc, cast.name))

                # Small delay between devices to avoid conflicts
                time.sleep(0.5)
            except Exception as e:
                colored_name_err = colorize_device_name(cast.name)
                log(f"{Colors.RED}❌ Error playing on {colored_name_err}: {e}{Colors.END}")
                import traceback
                traceback.print_exc()

        log(f"\n{Colors.GREEN}✅ Playback initiated on {len(media_controllers)} device(s){Colors.END}")
        log(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

        # Wait for playback to complete in test mode
        if test_mode and media_controllers:
            time.sleep(2)  # Give playback time to start
            # Monitor the first device for completion
            first_mc = media_controllers[0][0]
            first_mc.update_status()
            while first_mc.status.player_state in ['PLAYING', 'BUFFERING']:
                time.sleep(1)
                first_mc.update_status()
            log(f"{Colors.GREEN}✅ Finished playing {title_text}{Colors.END}")

    except Exception as e:
        log(f"{Colors.RED}❌ Cast Error: {e}{Colors.END}")

# 3. Main Loop
print(f"{Colors.BOLD}{Colors.GREEN}🕌 Azan System Active for {LOCATION} coordinates{Colors.END}")
print(f"{Colors.CYAN}📡 Using IP address: {LOCAL_IP}:{PORT}{Colors.END}")

# Check for test mode
if '--test' in sys.argv:
    print(f"{Colors.BLUE}🧪 Running in test mode...{Colors.END}")
    play_azan(is_fajr=False, test_mode=True)
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
    print(f"{Colors.GREEN}✅ Test completed. Exiting.{Colors.END}")
    sys.exit(0)

# Normal scheduling mode
while True:
    now = datetime.now()
    current_csv = generate_monthly_csv(now.year, now.month)
    today_str = now.strftime("%d/%m/%Y")
    now_time = now.strftime("%H:%M")

    with open(current_csv, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Date'] == today_str:
                for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                    if now_time == row[prayer]:
                        log(f"{Colors.BOLD}{Colors.BLUE}🕌 It is time for {prayer} ({now_time}){Colors.END}")
                        play_azan(is_fajr=(prayer == 'Fajr'), prayer_name=prayer)
                        time.sleep(61)

    time.sleep(30)