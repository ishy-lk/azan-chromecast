# 🕌 Prayer Times Chromecast

Automatically plays the Azan (Islamic call to prayer) on Google Chromecast devices at the correct prayer times. Supports two modes: fetch a full timetable from your masjid's [my-masjid.com](https://my-masjid.com) screen (includes Iqamah times), or calculate from your coordinates.

## Quick Commands

```bash
# JSON mode (my-masjid.com timetable)
python3 prayer_times.py --json
python3 prayer_times.py --json --test
python3 prayer_times.py --json --test-prayer Maghrib
python3 prayer_times.py --json --force   # re-fetch timetable from API

# Longlat mode (coordinate calculation)
python3 prayer_times.py --longlat
python3 prayer_times.py --longlat --test
python3 prayer_times.py --longlat --test-prayer Maghrib
python3 prayer_times.py --longlat --force   # regenerate current month's CSV
```

## Updating

Once installed, updating is just:

```bash
git pull
./service.sh restart   # macOS
# or
sudo systemctl restart prayer-azan   # Linux / Pi
```

`setup.sh` only needs to be run **once** on first install (or when `requirements.txt` changes). Your `config.json` is untouched by updates.

## Modes

### `--json` — My Masjid timetable (recommended)

Fetches your masjid's full yearly timetable once from [my-masjid.com](https://my-masjid.com) and saves it as `timetable_YYYY.json`. All prayer times, Iqamah times, Sunrise, and Jumu'ah come from this file — no recalculation needed. The file is re-fetched automatically when the year rolls over.

On Google Home displays it shows:
```
It's time for Asr in Stevenage | 🧎🏽‍♂️ Iqamah 18:15 🤲🏽
```

**Finding your GUID:** Go to your masjid's my-masjid.com timing screen. The GUID is in the URL:
```
https://time.my-masjid.com/timingscreen/3bf29ae9-f0ee-490f-bdb0-1a12695a2dd8
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                         this is the masjid_guid
```

### `--longlat` — Coordinate calculation

Calculates prayer times using the [prayer-times-calculator](https://github.com/DrKhalil/prayer-times-calculator) library (MWL method) from your `lat`/`lon`. Generates monthly CSVs for offline reliability. No Iqamah times (those are masjid-specific and not calculable).

## Service Management (macOS)

```bash
./service.sh install   # First-time: create the LaunchAgent plist (prompts for mode)
./service.sh start     # Start the service
./service.sh stop      # Stop the service
./service.sh restart   # Restart (e.g. after a git pull)
./service.sh status    # Check if running
./service.sh logs      # Tail the log file
```

## Features

- Two modes: my-masjid.com JSON timetable or coordinate-based calculation
- Plays Azan on Chromecast devices/groups at scheduled prayer times
- JSON mode: shows Iqamah time on Google Home displays alongside prayer name
- JSON mode: includes Sunrise and Jumu'ah times in terminal output
- Silent Fajr mode (casts with volume 0 so displays still show prayer info)
- Configurable volume per prayer type
- Visual display with prayer name, location, and background image
- Auto-detects local IP address
- Event-driven scheduling (sleeps until next prayer, no polling)
- JSON mode: full-year timetable cached locally, re-fetched once per year
- Longlat mode: monthly CSV with auto-validation and pre-generation
- Test modes for easy setup verification

## Requirements

- Python 3.8+
- A Mac, Linux machine, or Raspberry Pi on the same WiFi as your Chromecast
- One or more Google Chromecast devices (speakers, displays, or groups)

---

## Setup Guide — Mac

### 1. Clone and install

```bash
git clone https://github.com/ishy-lk/azan-chromecast.git
cd azan-chromecast
./setup.sh
```

This creates a Python virtual environment and installs dependencies.

### 2. Configure

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "speaker_or_group_name": ["My Speaker"],
  "location": "Stevenage",
  "fajr_volume": 0.0,
  "standard_volume": 0.5,

  "masjid_guid": "3bf29ae9-f0ee-490f-bdb0-1a12695a2dd8"
}
```

`config.json` is gitignored so your personal details stay out of version control. Only include the settings you want to override — defaults are built into the script.

**Finding your Chromecast name:** Open the Google Home app → tap your device → Settings → the name shown at the top is what you use. To cast to multiple devices at once, create a Speaker Group in Google Home and use the group name.

### 4. Test it

```bash
source venv/bin/activate
python3 prayer_times.py --json --test-prayer Dhuhr
```

You should hear the Azan on your Chromecast and see prayer info on any displays. Press `Ctrl+C` to stop.

### 5. Run the scheduler

```bash
python3 prayer_times.py --json
```

On first run it fetches `timetable_YYYY.json` from my-masjid.com, then shows today's schedule and sleeps until the next prayer.

### 6. Run as a background service (macOS)

```bash
./service.sh install   # prompts for --json or --longlat, creates the LaunchAgent plist
./service.sh start
```

The service auto-starts on boot and auto-restarts on crash. Logs go to `/tmp/prayer_times.log`.

```bash
./service.sh logs      # watch live logs
./service.sh restart   # after a git pull
```

<details>
<summary>Manual plist setup (if not using service.sh)</summary>

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
        <string>--json</string>
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
tail -f /tmp/prayer_times.log                                    # view logs
```
</details>

---

## Setup Guide — Raspberry Pi

If you already have a Raspberry Pi set up and running, this just adds the azan service alongside whatever else it's doing — it won't interfere with any existing services.

If you're starting fresh, a Pi is ideal for this: low power, always on, and permanently on your home WiFi.

### 1. (Fresh Pi only) Flash Raspberry Pi OS

Skip this step if your Pi is already running.

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS Bookworm (64-bit)** to your SD card. In the imager settings (the gear icon) configure:
- Hostname (e.g. `prayer-pi`)
- Username and password
- WiFi credentials
- Enable SSH

Then SSH in:
```bash
ssh your-username@prayer-pi.local
```

### 2. Clone and install

```bash
git clone https://github.com/ishy-lk/azan-chromecast.git
cd azan-chromecast
./setup.sh
```

When prompted, choose **yes** to create a virtual environment. On Raspberry Pi OS Bookworm, pip installs outside a venv are blocked by default — the venv handles this cleanly.

### 3. Configure

```bash
cp config.example.json config.json
vi config.json
```

```json
{
  "speaker_or_group_name": ["My Speaker"],
  "location": "Stevenage",
  "fajr_volume": 0.0,
  "standard_volume": 0.5,
  "masjid_guid": "3bf29ae9-f0ee-490f-bdb0-1a12695a2dd8"
}
```

### 4. Test it

```bash
source venv/bin/activate
python3 prayer_times.py --json --test-prayer Dhuhr
```

### 5. Set up the systemd service

Create `/etc/systemd/system/prayer-azan.service`:

```bash
sudo vi /etc/systemd/system/prayer-azan.service
```

Paste the following, replacing `your-username` with your Pi username:

```ini
[Unit]
Description=Prayer Times Azan Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/azan-chromecast
ExecStart=/home/your-username/azan-chromecast/venv/bin/python3 prayer_times.py --json
Restart=always
RestartSec=10
StandardOutput=append:/var/log/prayer_times.log
StandardError=append:/var/log/prayer_times.log

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable prayer-azan    # start on boot
sudo systemctl start prayer-azan     # start now
sudo systemctl status prayer-azan    # check it's running
sudo journalctl -u prayer-azan -f    # live logs
```

### Service management on Pi

```bash
sudo systemctl stop prayer-azan      # stop
sudo systemctl restart prayer-azan   # restart (e.g. after git pull)
sudo journalctl -u prayer-azan -f    # tail logs
sudo journalctl -u prayer-azan --since today   # today's logs only
```

### Keeping the Pi up to date

```bash
cd ~/azan-chromecast
git pull
sudo systemctl restart prayer-azan
```

---

## Configuration Reference

All settings in `config.json` (see `config.example.json`):

| Setting | Default | Description |
|---------|---------|-------------|
| `speaker_or_group_name` | `["HomeGroup"]` | Chromecast device/group name(s) |
| `location` | `"London"` | City name shown on display |
| `fajr_volume` | `0.0` | Fajr volume (0.0 = silent, still shows on display) |
| `standard_volume` | `0.5` | Volume for all other prayers |
| `fajr_file` | `"fajr_azan.mp3"` | Optional separate Fajr audio |
| `standard_file` | `"standard_azan.mp3"` | Main Azan audio |
| `port` | `8000` | HTTP server port for serving audio to Chromecasts |
| `masjid_guid` | — | **`--json` mode:** GUID from your my-masjid.com URL |
| `lat` / `lon` | `51.5074` / `-0.1278` | **`--longlat` mode:** coordinates ([latlong.net](https://www.latlong.net)) |

The longlat calculation method is MWL (Muslim World League) by default. Other options: `isna`, `egypt`, `makkah`, `karachi`, `tehran`, `jafari`.

---

## Monitoring with iPhone (Optional)

The script runs an HTTP server on port 8000 while active. You can use [Scriptable](https://apps.apple.com/app/scriptable/id1405459188) + iOS Shortcuts to get a daily push notification if the device goes offline.

### 1. Scriptable Script

Create a script called `CheckAzan` in Scriptable:

```javascript
let r = new Request("http://YOUR-HOSTNAME.local:8000")
r.timeoutInterval = 10
try {
  await r.loadString()
} catch (e) {
  let n = new Notification()
  n.title = "Azan Offline"
  n.body = "prayer-pi (or Mac) is unreachable — Azan may not be running"
  n.sound = "default"
  await n.schedule()
}
Script.complete()
```

Replace `YOUR-HOSTNAME` with your Pi's hostname (e.g. `prayer-pi`) or Mac's local hostname.

### 2. Shortcuts Automation

1. Open **Shortcuts** → **Automations** → **+**
2. **Time of Day** → pick a time → **Daily** → toggle off **Ask Before Running**
3. Add action: **Run Scriptable Script** → select `CheckAzan`

---

## File Structure

```
azan-chromecast/
├── prayer_times.py               # Main script
├── config.example.json           # Example config (tracked in git)
├── config.json                   # Your local config (gitignored)
├── requirements.txt              # Python dependencies
├── service.sh                    # macOS service manager (start/stop/restart)
├── setup.sh                      # Setup script (creates venv, installs deps)
├── README.md                     # This file
├── makkah-1-wide-optimized.jpeg  # Background image for Chromecast displays
├── standard_azan.mp3             # Azan audio (required, tracked in git)
├── fajr_azan.mp3                 # Fajr Azan audio (optional, tracked in git)
├── timetable_YYYY.json           # JSON mode: full-year timetable (gitignored)
└── prayers_YYYY_MM.csv           # Longlat mode: monthly schedule (gitignored)
```

---

## Troubleshooting

### Chromecast not found
- Ensure your device and Chromecast are on the same WiFi network
- Check `speaker_or_group_name` in `config.json` matches your device/group name exactly (case-sensitive)
- Run `python3 prayer_times.py --json --test` to verify discovery works
- mDNS discovery can occasionally fail (especially if the Cast group was idle). The service retries up to 3 times with a 20s timeout each (60s total) before giving up. The `playback_devices_found` log line includes `attempts` and `elapsed_seconds` so you can see how long discovery took

### No audio on some devices in a group
- The script automatically skips cover art for group casts to prevent audio-only devices (e.g. Nest Mini) from dropping out of sync

### JSON mode: timetable not fetching
- Check internet connectivity: `curl https://time.my-masjid.com`
- Verify your `masjid_guid` in `config.json` matches the URL of your my-masjid.com screen
- Run `python3 prayer_times.py --json --force` to retry the fetch

### Longlat mode: prayer times seem wrong
- Verify your `lat` and `lon` at [latlong.net](https://www.latlong.net)
- Try a different `calculation_method` in `generate_monthly_csv` — different methods are used in different regions
- Run `python3 prayer_times.py --longlat --force` to regenerate the CSV

### Pi: service not starting after reboot
- Check `sudo systemctl status prayer-azan` for the error
- Ensure the path in `ExecStart` matches your actual username and directory
- Check logs: `sudo journalctl -u prayer-azan -n 50`

### Pi: network not ready when service starts
- The service uses `After=network-online.target` — if the Pi connects slowly to WiFi, increase `RestartSec=10` to give it more time to reconnect on the first restart

---

## Credits

- Prayer times (longlat mode): [prayer-times-calculator](https://github.com/DrKhalil/prayer-times-calculator)
- Masjid timetables (JSON mode): [my-masjid.com](https://my-masjid.com)
- Chromecast: [pychromecast](https://github.com/home-assistant-libs/pychromecast)

## License

MIT License — feel free to modify and use for your needs.
