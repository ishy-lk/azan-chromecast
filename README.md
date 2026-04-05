# 🕌 Prayer Times Chromecast

Automatic prayer time notifications with Azan playback on Google Chromecast devices. Displays prayer information with a beautiful background image while playing the Azan audio.

## Quick Commands

```bash
python3 prayer_times.py                        # Run the scheduler
python3 prayer_times.py --test                 # Simulate the next upcoming prayer
python3 prayer_times.py --test-prayer Maghrib  # Simulate a specific prayer
python3 prayer_times.py --force                # Regenerate current month's CSV
```

## Features

- ✅ Automatic prayer time calculation based on your location
- ✅ Plays Azan on Chromecast at scheduled prayer times
- ✅ Different Azan for Fajr and other prayers
- ✅ Silent Fajr azan (casts with volume 0 so displays still show prayer info)
- ✅ Volume control per prayer type
- ✅ Beautiful visual display with prayer name and location
- ✅ Optimized background image display
- ✅ Monthly prayer time CSV generation for offline reliability
- ✅ Auto-detects local IP address
- ✅ Pre-generates next month's schedule near end of month
- ✅ Event-driven scheduling (sleeps until next prayer instead of polling)
- ✅ Test modes for easy debugging

## Requirements

- Python 3.8 or higher
- Google Chromecast device on the same network
- Your computer on the same WiFi network as the Chromecast

## Quick Setup

1. Clone the repository:
   ```bash
   git clone github-personal:ishy-lk/azan-chromecast.git
   cd azan-chromecast
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure `prayer_times.py`:
   ```python
   SPEAKER_OR_GROUP_NAME = ["HomeGroup"]  # Chromecast device/group name in Google Home
   LAT = 51.915949                        # Your latitude
   LON = -0.181703                        # Your longitude
   LOCATION = "Stevenage"                 # Your city
   ```
   The local IP is auto-detected.

4. Add your audio files:
   - `standard_azan.mp3` — Azan for all prayers (required)
   - `fajr_azan.mp3` — Optional: different Azan for Fajr (falls back to standard if missing)

## Running the Scheduler

### Foreground
```bash
python3 prayer_times.py
```
Press `Ctrl+C` to stop.

### Background (with logging)
```bash
nohup python3 prayer_times.py > /tmp/prayer_times.log 2>&1 &
```

### Check if Running
```bash
ps aux | grep prayer_times.py
tail -f /tmp/prayer_times.log
```

### Stop
```bash
pkill -f prayer_times.py
```

## Usage

### Test Mode
Simulates the next upcoming prayer using the real azan audio:
```bash
python3 prayer_times.py --test
```

### Test Specific Prayer
```bash
python3 prayer_times.py --test-prayer Fajr
python3 prayer_times.py --test-prayer Maghrib
```

### Force Regenerate CSV
Re-generates the current month's prayer schedule:
```bash
python3 prayer_times.py --force
```

## Configuration Options

Edit `prayer_times.py` to customise:

```python
# Volume settings (0.0 to 1.0)
FAJR_VOLUME = 0.0       # Silent (still casts to show on displays)
STANDARD_VOLUME = 0.5   # 50% for other prayers

# Files
FAJR_FILE = "fajr_azan.mp3"
STANDARD_FILE = "standard_azan.mp3"
BG_IMAGE = "makkah-1-wide-optimized.jpeg"
```

## File Structure

```
azan-chromecast/
├── prayer_times.py                    # Main script
├── requirements.txt                   # Python dependencies
├── setup.sh                          # Setup script
├── README.md                         # This file
├── makkah-1-wide-optimized.jpeg      # Background image
├── standard_azan.mp3                 # Standard prayer audio (required)
├── fajr_azan.mp3                     # Fajr prayer audio (optional)
├── test-mp3.mp3                      # Short test audio
└── prayers_YYYY_MM.csv               # Auto-generated prayer times
```

## How It Works

1. **Prayer Time Calculation**: Uses the `prayer-times-calculator` library with your coordinates
2. **Monthly CSV Generation**: Creates a CSV file with all prayer times for the month, validates row count equals days in month, and pre-generates next month in the last 2 days
3. **Event-Driven Scheduling**: Loads the day's prayer times once, finds the next prayer, and sleeps until that exact time (no polling)
4. **Azan Playback**: When a prayer time arrives, it:
   - Sets appropriate volume (silent for Fajr, configurable for others)
   - Displays prayer name and location on Chromecast
   - Plays the corresponding Azan audio
   - Shows the Makkah background image on display devices

## Troubleshooting

### Chromecast not found
- Ensure both devices are on the same WiFi network
- Check `SPEAKER_OR_GROUP_NAME` matches your Chromecast device/group name exactly (case-sensitive)

### Image not loading
- Ensure the HTTP server can reach the image file
- Check that `LOCAL_IP` is detected correctly in the startup log

### Prayer times incorrect
- Verify your `LAT` and `LON` coordinates
- Check the calculation method in `generate_monthly_csv()` (default: `mwl`)

## Running on Startup (Optional)

### macOS (LaunchAgent)
Create `~/Library/LaunchAgents/com.prayer.azan.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.prayer.azan</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/ishy/personal/azan-chromecast/prayer_times.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.prayer.azan.plist
```

### Linux (systemd)
Create `/etc/systemd/system/prayer-azan.service`:
```ini
[Unit]
Description=Prayer Times Azan Service
After=network.target

[Service]
Type=simple
User=ishy
WorkingDirectory=/home/ishy/azan-chromecast
ExecStart=/usr/bin/python3 prayer_times.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable prayer-azan
sudo systemctl start prayer-azan
```

## Credits

- Prayer times calculation: [prayer-times-calculator](https://github.com/DrKhalil/prayer-times-calculator)
- Chromecast control: [pychromecast](https://github.com/home-assistant-libs/pychromecast)

## License

MIT License - Feel free to modify and use for your needs.
