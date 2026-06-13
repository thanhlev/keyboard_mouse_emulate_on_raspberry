#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BT_SERVICE="/lib/systemd/system/bluetooth.service"
BT_CONF="/etc/bluetooth/main.conf"
DBUS_CONF="/etc/dbus-1/system.d/org.thanhle.btkbservice.conf"

# --- Checks ---

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (use sudo ./setup.sh)"
    exit 1
fi

if ! grep -qi "raspberry\|bcm2" /proc/cpuinfo 2>/dev/null && [ ! -f /sys/firmware/devicetree/base/model ]; then
    echo "Warning: this doesn't look like a Raspberry Pi. Continuing anyway..."
fi

echo "==> Updating package list..."
apt-get update -y

# --- System dependencies ---

echo "==> Installing system packages..."
apt-get install -y --no-install-recommends \
    git \
    tmux \
    bluez \
    bluez-tools \
    python3 \
    python3-dev \
    python3-pip \
    python3-dbus \
    python3-pyudev \
    python3-evdev \
    python3-gi \
    libbluetooth-dev

# pybluez (needed for Bluetooth socket support in Python)
echo "==> Installing pybluez..."
PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install git+https://github.com/pybluez/pybluez.git#egg=pybluez

# --- D-Bus configuration ---

echo "==> Installing D-Bus policy..."
cp "$SCRIPT_DIR/dbus/org.thanhle.btkbservice.conf" "$DBUS_CONF"
systemctl restart dbus.service

# --- Bluetooth service configuration ---

echo "==> Configuring Bluetooth service..."

# Back up original bluetooth.service for uninstall
if [ ! -f "$SCRIPT_DIR/bluetooth.service.bk" ]; then
    cp "$BT_SERVICE" "$SCRIPT_DIR/bluetooth.service.bk"
fi

# Remove any existing --noplugin flag, then add ours
# Disable 'input' plugin so BlueZ doesn't grab HID devices before we do
sed -i '/^ExecStart=/ s/ --noplugin=[^ ]*//' "$BT_SERVICE"
sed -i '/^ExecStart=/ s/$/ --noplugin=input/' "$BT_SERVICE"

# --- BlueZ main.conf ---

echo "==> Configuring BlueZ main.conf..."
mkdir -p /etc/bluetooth

# Create main.conf if it doesn't exist
if [ ! -f "$BT_CONF" ]; then
    cat > "$BT_CONF" << 'CONF'
[General]
CONF
fi

# Ensure [General] section exists
if ! grep -q '^\[General\]' "$BT_CONF"; then
    echo "[General]" >> "$BT_CONF"
fi

# Disable audio profiles so host doesn't see device as audio sink
sed -i '/^Disable\s*=/d' "$BT_CONF"
sed -i '/^\[General\]/a Disable=Source,Sink,Media' "$BT_CONF"

# Set device class to combo keyboard+pointing peripheral
sed -i '/^Class\s*=/d' "$BT_CONF"
sed -i '/^\[General\]/a Class=0x0025C0' "$BT_CONF"

# Make device discoverable and pairable by default
sed -i '/^DiscoverableTimeout\s*=/d' "$BT_CONF"
sed -i '/^\[General\]/a DiscoverableTimeout=0' "$BT_CONF"

# --- Enable and restart services ---

echo "==> Enabling bluetooth service on boot..."
systemctl daemon-reload
systemctl enable bluetooth.service
systemctl restart bluetooth.service

# Wait for adapter to come up
sleep 2

# Make adapter discoverable and pairable
if command -v bluetoothctl &>/dev/null; then
    echo "==> Setting adapter discoverable and pairable..."
    bluetoothctl discoverable on 2>/dev/null || true
    bluetoothctl pairable on 2>/dev/null || true
fi

echo ""
echo "==> Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit server/btk_server.py and set TARGET_ADDRESS to your host's MAC"
echo "  2. Pair the Pi with your host device via 'bluetoothctl'"
echo "  3. Run: sudo ./boot.sh"
echo ""
