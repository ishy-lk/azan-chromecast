#!/bin/bash

# Prayer Times Chromecast — macOS LaunchAgent service manager
# Usage: ./service.sh [start|stop|restart|status|logs|install]

PLIST_NAME="com.prayer.azan"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
LOG_FILE="/tmp/prayer_times.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
CYAN='\033[96m'
BOLD='\033[1m'
END='\033[0m'

is_running() {
    launchctl list "$PLIST_NAME" &>/dev/null
}

cmd_install() {
    if [ -f "$PLIST_PATH" ]; then
        echo -e "${YELLOW}Plist already exists at $PLIST_PATH${END}"
        read -p "Overwrite? [y/N]: " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && return
    fi

    echo -e "${CYAN}Choose prayer times source:${END}"
    echo "  1) --json     Fetch timetable from my-masjid.com (once per year)"
    echo "  2) --longlat  Calculate from coordinates in config.json"
    read -p "Enter 1 or 2 [default: 1]: " -n 1 -r MODE_CHOICE
    echo
    if [[ "$MODE_CHOICE" == "2" ]]; then
        MODE_FLAG="--longlat"
    else
        MODE_FLAG="--json"
    fi

    cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/venv/bin/python3</string>
        <string>$SCRIPT_DIR/prayer_times.py</string>
        <string>$MODE_FLAG</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>
    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
</dict>
</plist>
PLIST

    echo -e "${GREEN}Installed plist at $PLIST_PATH (mode: $MODE_FLAG)${END}"
    echo -e "${CYAN}Run ${BOLD}./service.sh start${END}${CYAN} to start the service${END}"
}

show_startup_logs() {
    echo -e "${CYAN}── startup log (5s) ──────────────────────────────${END}"
    tail -f "$LOG_FILE" & TAIL_PID=$!
    sleep 5
    kill $TAIL_PID 2>/dev/null
    wait $TAIL_PID 2>/dev/null
    echo -e "${CYAN}── done — run ${BOLD}./service.sh logs${END}${CYAN} to follow live ──${END}"
}

cmd_start() {
    if ! [ -f "$PLIST_PATH" ]; then
        echo -e "${RED}Plist not found. Run ${BOLD}./service.sh install${END}${RED} first.${END}"
        return 1
    fi
    if is_running; then
        echo -e "${YELLOW}Service is already running${END}"
        return
    fi
    launchctl load "$PLIST_PATH"
    sleep 1
    if is_running; then
        echo -e "${GREEN}Started${END}"
        show_startup_logs
    else
        echo -e "${RED}Failed to start — check $LOG_FILE${END}"
    fi
}

cmd_stop() {
    if ! is_running; then
        echo -e "${YELLOW}Service is not running${END}"
        return
    fi
    launchctl unload "$PLIST_PATH"
    echo -e "${GREEN}Stopped${END}"
}

cmd_restart() {
    echo -e "${CYAN}Stopping...${END}"
    cmd_stop
    sleep 1
    echo -e "${CYAN}Starting...${END}"
    cmd_start
}

cmd_status() {
    if is_running; then
        echo -e "${GREEN}${BOLD}Running${END}"
        launchctl list "$PLIST_NAME"
    else
        echo -e "${RED}${BOLD}Not running${END}"
    fi
}

cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found at $LOG_FILE${END}"
    fi
}

case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    install) cmd_install ;;
    *)
        echo -e "${BOLD}Usage:${END} ./service.sh <command>"
        echo ""
        echo "Commands:"
        echo "  install   Create the LaunchAgent plist (first-time setup)"
        echo "  start     Start the service"
        echo "  stop      Stop the service"
        echo "  restart   Stop and start the service"
        echo "  status    Check if the service is running"
        echo "  logs      Tail the log file"
        ;;
esac
