# 🕌 Prayer Times Chromecast

Automatic prayer time notifications with Azan playback on Google Chromecast devices. Displays prayer information with a beautiful background image while playing the Azan audio.

## Features

- ✅ Automatic prayer time calculation based on your location
- ✅ Plays Azan on Chromecast at scheduled prayer times
- ✅ Different Azan for Fajr and other prayers
- ✅ Volume control (quieter for Fajr, normal for others)
- ✅ Beautiful visual display with prayer name and location
- ✅ Optimized background image display
- ✅ Monthly prayer time CSV generation for offline reliability
- ✅ Test modes for easy debugging

## Requirements

- Python 3.8 or higher
- Google Chromecast device on the same network
- Your computer on the same WiFi network as the Chromecast

## Quick Setup

1. Clone the repository:
   ```bash
   git clone git@github.com:ishyherts/myhacks.git
   cd myhacks/azan-chromecast
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```

3. Configure `prayer_times.py`:
   ```python
   SPEAKER_NAME = "Living Room Display"  # Your Chromecast name
   LOCAL_IP = "192.168.1.221"            # Your computer's IP
   LAT = 51.915949                        # Your latitude
   LON = -0.181703                        # Your longitude
   LOCATION = "Stevenage"                 # Your city
   ```

4. Add your audio files:
   - `standard_azan.mp3` - Azan for prayers (required)
   - `fajr_azan.mp3` - Optional: Different Azan for Fajr prayer (if not provided, uses standard_azan.mp3)

5. Find your computer's local IP address:
   ```bash
   # On macOS/Linux
   ipconfig getifaddr en0  # For WiFi
   # or
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

## Running the Scheduler

### Start the Scheduler (Foreground)
Activate the virtual environment and run:
```bash
source venv/bin/activate
python prayer_times.py
```
Press `Ctrl+C` to stop.

### Start the Scheduler (Background)
To keep it running in the background with logging:
```bash
source venv/bin/activate
nohup python prayer_times.py > /tmp/prayer_times.log 2>&1 &
```

### Check if Running
```bash
ps aux | grep prayer_times.py
# or view the log
tail -f /tmp/prayer_times.log
```

### Stop the Scheduler
```bash
pkill -f prayer_times.py
```

## Usage

### Test Mode
Test the system with a short audio clip:
```bash
python prayer_times.py --test
```

### Test Specific Prayer
Test how a specific prayer will display:
```bash
python prayer_times.py --test-prayer Fajr
python prayer_times.py --test-prayer Maghrib
```

### Run Scheduler
See the [Running the Scheduler](#running-the-scheduler) section above for:
- Running in foreground or background
- Viewing logs
- Stopping the scheduler

When running, the script will:
- Generate monthly prayer times CSV
- Monitor the clock every 30 seconds
- Play Azan automatically at prayer times
- Display prayer information on Chromecast

## Configuration Options

Edit `prayer_times.py` to customize:

```python
# Volume settings (0.0 to 1.0)
FAJR_VOLUME = 0.4       # 40% for early morning
STANDARD_VOLUME = 0.7   # 70% for other prayers

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
├── test-mp3.mp3                      # Test audio file
└── prayers_YYYY_MM.csv               # Auto-generated prayer times
```

## How It Works

1. **Prayer Time Calculation**: Uses the `prayer-times-calculator` library with your coordinates
2. **Monthly CSV Generation**: Creates a CSV file with all prayer times for the month
3. **Scheduler Loop**: Checks the current time every 30 seconds
4. **Azan Playback**: When a prayer time matches, it:
   - Sets appropriate volume (lower for Fajr)
   - Displays prayer name and location on Chromecast
   - Plays the corresponding Azan audio
   - Shows the Makkah background image

## Troubleshooting

### Chromecast not found
- Ensure both devices are on the same WiFi network
- Check the `SPEAKER_NAME` matches your Chromecast device name exactly

### Image not loading
- The image should be under 1MB and 1920x1535 pixels
- Ensure the HTTP server can access the image file
- Check that `LOCAL_IP` is correct

### Prayer times incorrect
- Verify your `LAT` and `LON` coordinates
- Check the calculation method in `generate_monthly_csv()` (default: 'mwl')

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
        <string>/usr/local/bin/python3</string>
        <string>/Users/YOUR_USERNAME/personal/azan-chromecast/prayer_times.py</string>
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
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/azan-chromecast
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
