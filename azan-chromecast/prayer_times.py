import time
import csv
import os
import sys
import threading
import http.server
import socketserver
import pychromecast
import calendar
from datetime import datetime
from prayer_times_calculator import PrayerTimesCalculator

# --- CONFIGURATION ---
SPEAKER_NAME = "Living Room Display"
LOCAL_IP = "192.168.1.221" 
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
FAJR_VOLUME = 0.4  # 40% for early morning
STANDARD_VOLUME = 0.7  # 70% for other prayers

# 1. Background Web Server
def start_server():
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print(f"HTTP server started on port {PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"Warning: Could not start HTTP server on port {PORT}: {e}")
        print("If the server is already running, this is fine. Otherwise, check the port.")

threading.Thread(target=start_server, daemon=True).start()
time.sleep(1)  # Give server time to start

# 2. Monthly CSV Generator (Ensures offline reliability)
def generate_monthly_csv(year, month):
    filename = f"prayers_{year}_{month:02d}.csv"
    if os.path.exists(filename):
        return filename

    print(f"Generating local schedule for {calendar.month_name[month]} {year}...")
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
                print(f"Fetched times for {day:02d}/{month:02d}/{year}")
                
                # --- ADD THIS LINE ---
                time.sleep(1) # Wait 1 second between days to avoid API errors
                # ---------------------
                
            except Exception as e:
                print(f"Error fetching day {day}: {e}")
                # Optional: continue to next day or retry
    return filename

def play_azan(is_fajr, test_mode=False, prayer_name=None):
    try:
        chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=[SPEAKER_NAME])
        if not chromecasts:
            print(f"Device {SPEAKER_NAME} not found.")
            return
        cast = chromecasts[0]
        cast.wait()

        # Set volume based on prayer type
        volume = FAJR_VOLUME if is_fajr else STANDARD_VOLUME
        cast.set_volume(volume)
        print(f"Volume set to {int(volume * 100)}%")

        if test_mode:
            file = TEST_FILE
            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
                print(f"Playing {prayer_name} Azan (test)")
            else:
                title_text = "Test Azan"
                artist_text = f"{LOCATION} Prayer Time"
        else:
            file = FAJR_FILE if is_fajr else STANDARD_FILE
            if prayer_name:
                title_text = f"{prayer_name} Prayer"
                artist_text = f"It's time for {prayer_name} in {LOCATION}"
                print(f"Playing {prayer_name} Azan")
            else:
                title_text = "Fajr Azan" if is_fajr else "Prayer Azan"
                artist_text = f"{LOCATION} Prayer Time"

        url = f"http://{LOCAL_IP}:{PORT}/{file}"
        thumb_url = f"http://{LOCAL_IP}:{PORT}/{BG_IMAGE}"

        mc = cast.media_controller
        mc.play_media(
            url,
            'audio/mp3',
            title=title_text,
            thumb=thumb_url,
            current_time=0,
            autoplay=True,
            stream_type='BUFFERED',
            metadata={
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
        )
        mc.block_until_active()
        print(f"Started playing {title_text} on {SPEAKER_NAME}")

        # Wait for playback to complete in test mode
        if test_mode:
            time.sleep(2)  # Give playback time to start
            mc.update_status()
            while mc.status.player_state in ['PLAYING', 'BUFFERING']:
                time.sleep(1)
                mc.update_status()
            print(f"Finished playing {title_text}")

    except Exception as e:
        print(f"Cast Error: {e}")

# 3. Main Loop
print(f"Azan System Active for Stevenage coordinates.")

# Check for test mode
if '--test' in sys.argv:
    print("Running in test mode...")
    play_azan(is_fajr=False, test_mode=True)
    print("Test completed. Exiting.")
    sys.exit(0)

# Check for test prayer mode
if '--test-prayer' in sys.argv:
    try:
        prayer_index = sys.argv.index('--test-prayer')
        prayer_name = sys.argv[prayer_index + 1] if prayer_index + 1 < len(sys.argv) else "Maghrib"
    except (ValueError, IndexError):
        prayer_name = "Maghrib"

    print(f"Running test with {prayer_name} prayer display...")
    is_fajr = prayer_name.lower() == 'fajr'
    play_azan(is_fajr=is_fajr, test_mode=True, prayer_name=prayer_name)
    print("Test completed. Exiting.")
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
                        print(f"It is time for {prayer} ({now_time})")
                        play_azan(is_fajr=(prayer == 'Fajr'), prayer_name=prayer)
                        time.sleep(61)

    time.sleep(30)