#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-/dev/ttyUSB0}"
FQBN="${FQBN:-megaTinyCore:megaavr:tiny1616}"
PROGRAMMER="${PROGRAMMER:-jtag2updi}"
BURN_BOOTLOADER="${BURN_BOOTLOADER:-1}"
SKIP_UPLOAD="${SKIP_UPLOAD:-0}"

echo "Using:"
echo "  FQBN      = $FQBN"
echo "  PORT      = $PORT"
echo "  PROGRAMMER= $PROGRAMMER"

echo ""

echo "This flow is intended for a custom board using an ATtiny1616 over UPDI."

echo "It will:"
if [[ "$BURN_BOOTLOADER" == "1" ]]; then
  echo "  1) burn the bootloader / set fuses"
fi
echo "  2) upload flash_eeprom.ino"
echo "  3) upload drive_firmware.ino"

echo ""

if [[ "$SKIP_UPLOAD" != "0" ]]; then
  echo "SKIP_UPLOAD=1 set; skipping sketch uploads."
  exit 0
fi

SKETCHES=(
  "$ROOT_DIR/flash_eeprom/flash_eeprom.ino"
  "$ROOT_DIR/drive_firmware/drive_firmware.ino"
)

for sketch in "${SKETCHES[@]}"; do
  if [[ ! -f "$sketch" ]]; then
    echo "Missing sketch: $sketch"
    exit 1
  fi
done

if [[ "$BURN_BOOTLOADER" == "1" ]]; then
  echo "=================================================="
  echo "Burning bootloader / setting fuses"
  echo "=================================================="
  arduino-cli burn-bootloader \
    --fqbn "$FQBN" \
    --port "$PORT" \
    --programmer "$PROGRAMMER"
  echo
fi

for sketch in "${SKETCHES[@]}"; do
  echo "=================================================="
  echo "Uploading: $(basename "$sketch")"
  echo "=================================================="

  arduino-cli upload \
    --fqbn "$FQBN" \
    --port "$PORT" \
    --programmer "$PROGRAMMER" \
    "$sketch"

  echo
  echo "Upload complete: $(basename "$sketch")"
  echo
 done

echo "All firmware operations completed successfully."
