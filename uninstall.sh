#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BT_SERVICE="/lib/systemd/system/bluetooth.service"
BT_CONF="/etc/bluetooth/main.conf"
DBUS_CONF="/etc/dbus-1/system.d/org.thanhle.btkbservice.conf"

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (use sudo ./uninstall.sh)"
    exit 1
fi

echo "==> Restoring bluetooth service..."
if [ -f "$SCRIPT_DIR/bluetooth.service.bk" ]; then
    cp "$SCRIPT_DIR/bluetooth.service.bk" "$BT_SERVICE"
    rm "$SCRIPT_DIR/bluetooth.service.bk"
else
    echo "    No backup found, removing --noplugin flag manually..."
    sed -i '/^ExecStart=/ s/ --noplugin=[^ ]*//' "$BT_SERVICE"
fi

echo "==> Removing BlueZ config changes..."
if [ -f "$BT_CONF" ]; then
    sed -i '/^Disable=Source,Sink,Media/d' "$BT_CONF"
    sed -i '/^Class=0x0025C0/d' "$BT_CONF"
    sed -i '/^DiscoverableTimeout=0/d' "$BT_CONF"
fi

echo "==> Removing D-Bus policy..."
rm -f "$DBUS_CONF"

echo "==> Restarting services..."
systemctl daemon-reload
systemctl restart dbus.service
systemctl restart bluetooth.service

echo "==> Uninstall complete."
