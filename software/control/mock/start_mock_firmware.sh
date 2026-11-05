#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-splitflap-mock}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOFTWARE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session '$SESSION_NAME' already exists. Attaching..."
  tmux attach -t "$SESSION_NAME"
  exit 0
fi

# Create a tmux session with two named windows:
# - usb: fake USB bridge (socat)
# - firmware: mock firmware

tmux new-session -d -s "$SESSION_NAME" -n "usb"
tmux send-keys -t "$SESSION_NAME:usb" "cd '$SOFTWARE_DIR' && socat -d -d PTY,link=/tmp/vcom_host,raw,echo=0 PTY,link=/tmp/vcom_firmware,raw,echo=0" C-m

tmux new-window -t "$SESSION_NAME" -n "firmware"
tmux send-keys -t "$SESSION_NAME:firmware" "cd '$SOFTWARE_DIR' && python3 control/mock/mock_drive_firmware.py" C-m

tmux select-window -t "$SESSION_NAME:usb"
tmux attach -t "$SESSION_NAME"
