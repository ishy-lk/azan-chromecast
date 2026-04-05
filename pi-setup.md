# Raspberry Pi 5 Setup Guide

Hardware notes and setup instructions for running this project on a Raspberry Pi 5 with NVMe SSD.

---

## Hardware Used

- Raspberry Pi 5 8GB
- Miniature PC-style case with NVMe M.2 SSD HAT (supports 2230, 2242, 2260, 2280)
- NVMe SSD (see compatibility list below)
- SONOFF Zigbee 3.0 USB Dongle Plus (for future Home Assistant / Zigbee use)

---

## NVMe SSD Compatibility

The M.2 HAT is just a signal and power bridge — SSD compatibility is between the SSD and the Pi 5 itself.

### Confirmed Compatible SSDs
- Samsung PM9A1, PM981, PM991, PM991a, PM9B1
- SK Hynix BC901, BC711
- Kioxia BG4, BG5 (2230), Kioxia Exceria
- **Crucial P2, P3, P3 Plus** (good budget option)
- AData Legend 700, Legend 800
- Lexar NM710
- Netac NV2000, NV3000
- Official Raspberry Pi NVMe SSD

### Known Incompatible SSDs
Avoid these — they use controllers that cause issues with Pi 5:
- WD Blue SN550 / SN580
- WD Green SN350
- WD Black SN850 / SN770
- Corsair MP600
- Kingston KC3000, OM8SEP4256Q-A0
- Micron 2450
- Inland TN446
- PNY CS1030
- Lexar NM620, NM790
- Transcend 110Q
- Kingspec series
- Any SSD using: SMI2263XT, SMI2263EN, MAP1202, or Phison controllers

> Before buying, search **"Pi Benchmarks [SSD model]"** online to verify compatibility.

---

## First-Time SSD Boot Setup

### 1. Assemble hardware
Fit the Pi 5 into the case with the M.2 HAT and SSD installed.

### 2. Boot from SD card first
Flash a microSD with Raspberry Pi OS using [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Mac. Boot the Pi from it.

### 3. Update the Pi and bootloader
```bash
sudo apt update && sudo apt full-upgrade
sudo apt install rpi-eeprom
sudo rpi-eeprom-update
```

### 4. Install Raspberry Pi Imager on the Pi
```bash
sudo apt install rpi-imager
rpi-imager
```

### 5. Flash the OS to your NVMe SSD
In Imager:
- Device: Raspberry Pi 5
- OS: Raspberry Pi OS (or Raspberry Pi OS Lite for headless)
- Storage: select your NVMe SSD

### 6. Set NVMe as boot drive
```bash
sudo raspi-config
```
Navigate to: **Advanced Options → Boot Order → NVMe/USB Boot**

### 7. Reboot
Remove the SD card. The Pi will now boot from the NVMe SSD.

---

## Setting Up This Project

Once booted from SSD:

```bash
# Install git
sudo apt install git -y

# Clone the repo
git clone https://github.com/ishy-lk/azan-chromecast.git
cd azan-chromecast

# Run setup (creates venv, installs dependencies)
./setup.sh

# Copy and edit config
cp config.example.json config.json
nano config.json

# Install and start the service (Linux/systemd)
sudo cp azan.service /etc/systemd/system/prayer-azan.service   # see README for full service file
sudo systemctl daemon-reload
sudo systemctl enable prayer-azan
sudo systemctl start prayer-azan

# Check logs
sudo journalctl -u prayer-azan -f
```

> See the main [README](README.md) for the full systemd service file and configuration options.

---

## Tips

- **Headless setup**: In Raspberry Pi Imager, click the settings gear before flashing — set hostname, enable SSH, and pre-configure your WiFi. No keyboard or monitor needed.
- **Find the Pi on your network**: `ping raspberrypi.local` or check your router's device list, then `ssh pi@<ip-address>`
- **Keep it updated**: Run `sudo apt update && sudo apt full-upgrade` periodically
