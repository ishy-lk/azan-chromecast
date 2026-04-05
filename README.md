# 🕌 Prayer Times Chromecast

Automatically plays the Azan (Islamic call to prayer) on Google Chromecast devices at the correct prayer times for your location. Displays prayer information with a background image on Chromecast displays while playing audio on all devices in a group.

## Quick Commands

```bash
python3 prayer_times.py                        # Run the scheduler
python3 prayer_times.py --test                 # Simulate the next upcoming prayer
python3 prayer_times.py --test-prayer Maghrib  # Simulate a specific prayer
python3 prayer_times.py --force                # Regenerate current month's CSV
```

## Features

- Automatic prayer time calculation based on your coordinates
- Plays Azan on Chromecast devices/groups at scheduled times
- Silent Fajr mode (casts with volume 0 so displays still show prayer info)
- Configurable volume per prayer type
- Visual display with prayer name, location, and background image
- Monthly prayer schedule CSV for offline reliability
- Auto-detects local IP address
- Pre-generates next month's schedule near end of month
- Event-driven scheduling (sleeps until next prayer, no polling)
- CSV validation ensures complete schedules (row count = days in month)
- Test modes for easy setup verification

## Requirements

- Python 3.8+
- A Mac or Linux machine on the same WiFi as your Chromecast
- One or more Google Chromecast devices (speakers, displays, or groups)

## Setup Guide

### 1. Clone and install

```bash
git clone https://github.com/ishy-lk/azan-chromecast.git
cd azan-chromecast
./setup.sh
```

This creates a Python virtual environment and installs dependencies.

### 2. Add your Azan audio

Place your audio file(s) in the project directory:
- `standard_azan.mp3` — used for all prayers **(required)**
- `fajr_azan.mp3` — optional separate Azan for Fajr (falls back to standard if missing)

### 3. Configure your location and devices

Copy the example config and edit with your details:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "speaker_or_group_name": ["My Speaker"],
  "lat": 51.5074,
  "lon": -0.1278,
  "location": "London",
  "fajr_volume": 0.0,
  "standard_volume": 0.5
}
```

`config.json` is gitignored so your personal details stay out of version control. Only include the settings you want to override — defaults are built into the script.

**Finding your Chromecast name:** Open the Google Home app → tap your device → Settings → the name shown at the top is what you use. To cast to multiple devices at once, create a Speaker Group in Google Home and use the group name.

**Finding your coordinates:** Go to [latlong.net](https://www.latlong.net), search your city, and copy the latitude/longitude values.

### 4. Test it

```bash
source venv/bin/activate
python3 prayer_times.py --test-prayer Dhuhr
```

You should hear the Azan on your Chromecast and see prayer info on any displays. Press `Ctrl+C` to stop.

### 5. Run the scheduler

```bash
python3 prayer_times.py
```

The script will:
1. Generate a monthly prayer schedule CSV (if not already present)
2. Show today's prayer times in the terminal
3. Sleep until the next prayer time
4. Play the Azan, then move to the next prayer
5. At midnight, reload the next day's schedule

## Configuration Options

All settings in `config.json` (see `config.example.json` for the full list):

| Setting | Default | Description |
|---------|---------|-------------|
| `speaker_or_group_name` | `["HomeGroup"]` | Chromecast device/group name(s) |
| `lat` / `lon` | `51.5074` / `-0.1278` | Your coordinates ([latlong.net](https://www.latlong.net)) |
| `location` | `"London"` | City name shown on display |
| `fajr_volume` | `0.0` | Fajr volume (0.0 = silent, still shows on display) |
| `standard_volume` | `0.5` | Volume for other prayers |
| `fajr_file` | `"fajr_azan.mp3"` | Optional separate Fajr audio |
| `standard_file` | `"standard_azan.mp3"` | Main Azan audio |
| `port` | `8000` | HTTP server port |

The prayer calculation method is `mwl` by default. Other options: `isna`, `egypt`, `makkah`, `karachi`, `tehran`, `jafari`.

## Running as a Background Service (macOS)

To keep the scheduler running permanently (survives reboots and crashes), create a LaunchAgent:

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
        <string>/path/to/azan-chromecast/venv/bin/python3</string>
        <string>/path/to/azan-chromecast/prayer_times.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/prayer_times.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/prayer_times.log</string>
</dict>
</plist>
```

Replace `/path/to/azan-chromecast` with your actual path, then:

```bash
launchctl load ~/Library/LaunchAgents/com.prayer.azan.plist     # start
launchctl unload ~/Library/LaunchAgents/com.prayer.azan.plist   # stop
tail -f /tmp/prayer_times.log                                   # view logs
```

## Monitoring with iPhone (Optional)

The script runs an HTTP server on port 8000 while active. You can use [Scriptable](https://apps.apple.com/app/scriptable/id1405459188) + iOS Shortcuts to get a daily push notification if the Mac goes offline.

### 1. Scriptable Script

Create a script called `CheckMac` in Scriptable:

```javascript
let r = new Request("http://YOUR-MAC-HOSTNAME.local:8000")
r.timeoutInterval = 10
try {
  await r.loadString()
} catch (e) {
  let n = new Notification()
  n.title = "Mac Offline"
  n.body = "Azan may not be running — check your Mac"
  n.sound = "default"
  await n.schedule()
}
Script.complete()
```

Replace `YOUR-MAC-HOSTNAME` with your Mac's hostname (System Settings → General → Sharing → Local hostname).

### 2. Shortcuts Automation

1. Open **Shortcuts** → **Automations** → **+**
2. **Time of Day** → pick a time → **Daily** → toggle off **Ask Before Running**
3. Add action: **Run Scriptable Script** → select `CheckMac`

If the Mac is offline or the script isn't running, you'll get a notification. No notification means everything is working.

## File Structure

```
azan-chromecast/
├── prayer_times.py               # Main script
├── config.example.json           # Example config (tracked in git)
├── config.json                   # Your local config (gitignored)
├── requirements.txt              # Python dependencies
├── setup.sh                     # Setup script (creates venv)
├── README.md                    # This file
├── makkah-1-wide-optimized.jpeg # Background image for displays
├── standard_azan.mp3            # Azan audio (required)
├── fajr_azan.mp3                # Fajr Azan audio (optional)
├── test-mp3.mp3                 # Short test audio
└── prayers_YYYY_MM.csv          # Auto-generated monthly schedule (gitignored)
```

## Troubleshooting

### Chromecast not found
- Ensure Mac and Chromecast are on the same WiFi network
- Check `SPEAKER_OR_GROUP_NAME` matches your device/group name exactly (case-sensitive)
- Try `python3 prayer_times.py --test` to verify discovery

### No audio on some devices in a group
- The script automatically skips cover art for group casts to prevent audio-only devices (e.g. Nest Mini) from dropping out of sync

### Prayer times seem wrong
- Verify your `LAT` and `LON` coordinates at [latlong.net](https://www.latlong.net)
- Check the `calculation_method` — different methods are used in different regions
- Run `python3 prayer_times.py --force` to regenerate the CSV

### CSV incomplete
- The script validates that the CSV has one row per day in the month
- If incomplete (e.g. API was down during generation), it automatically regenerates on next run

## Credits

- Prayer times: [prayer-times-calculator](https://github.com/DrKhalil/prayer-times-calculator)
- Chromecast: [pychromecast](https://github.com/home-assistant-libs/pychromecast)

## License

MIT License — feel free to modify and use for your needs.
