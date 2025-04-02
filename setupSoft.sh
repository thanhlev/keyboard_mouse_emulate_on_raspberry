#!/bin/bash
sudo apt-get update -y
sudo apt-get install -y --ignore-missing git tmux bluez bluez-tools bluez-firmware
sudo apt-get install -y --ignore-missing python3 python3-dev python3-pip python3-dbus python3-pyudev python3-evdev python3-gi

sudo apt-get install -y libbluetooth-dev
sudo PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install git+https://github.com/pybluez/pybluez.git#egg=pybluez

sudo cp dbus/org.thanhle.btkbservice.conf /etc/dbus-1/system.d
sudo systemctl restart dbus.service

sudo sed -i '/^ExecStart=/ s/$/ --noplugin=input/' /lib/systemd/system/bluetooth.service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth.service
