#!/usr/bin/python3
#
# Bluetooth keyboard/Mouse emulator DBUS Service
#

from __future__ import absolute_import, print_function
from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
from logging import debug, info, warning, error
import bluetooth
from bluetooth import *

logging.basicConfig(level=logging.DEBUG)

# @todo fill your host mac here manually
TARGET_ADDRESS = "74:97:79:E3:6E:A2"

class BTKbDevice():
    # change these constants
    MY_ADDRESS = "B0:AC:82:FB:BE:EC"
    MY_DEV_NAME = "ISer"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Interrupt port - must match port configured in SDP record
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        print("2. Setting up BT device")
        self.init_bt_device()
        self.init_bluez_profile()
        self.setup_autoconnect()

    # configure the bluetooth hardware device
    def init_bt_device(self):
        print("3. Configuring Device name " + BTKbDevice.MY_DEV_NAME)
        # set the device class to a keybord and set the name
        os.system("hciconfig hci0 up")
        os.system("hciconfig hci0 name " + BTKbDevice.MY_DEV_NAME)
        # make the device discoverable
        os.system("hciconfig hci0 piscan")

    # set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        # setup profile options
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        # retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object(
            "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        manager.RegisterProfile("/org/bluez/hci0", BTKbDevice.UUID, opts)
        print("6. Profile registered ")
        os.system("hciconfig hci0 class 0x002540")

    # read and return an sdp record from a file
    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")
        return fh.read()

    def setup_socket(self):
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind these sockets to a port - port zero to select next available
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
        self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))

    def setup_autoconnect(self):
        print("7. Profile registered ")
        os.system("bt-agent -c NoInputNoOutput -d")

    # listen for incoming client connections
    def listen(self):
        print("\033[0;33m8. Waiting for connections\033[0m")

        # key point: use connect to get the host request for the accept() below
        # it work, I just dont care for having been into it for 2days
        self.setup_socket()
        try:
            # must be ahead of listen or 'File descriptor in bad state'
            self.scontrol.connect((TARGET_ADDRESS, self.P_CTRL))
        except socket.error as err:
            # it was expect to failed
            print("Connect failed: "+str(err))

        # this may not work
        # os.system("bluetoothctl connect " + TARGET_ADDRESS)
        # os.system("bluetoothctl trust " + TARGET_ADDRESS)

        self.setup_socket()

        # Start listening on the server sockets
        self.scontrol.listen(5)
        self.sinterrupt.listen(5)

        self.ccontrol, cinfo = self.scontrol.accept()
        print (
            "\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])

        self.cinterrupt, cinfo = self.sinterrupt.accept()
        print (
            "\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])

    # send a string to the bluetooth host machine
    def send_string(self, message):
        try:
            self.cinterrupt.send(bytes(message))
        except OSError as err:
            error(err)
            self.listen()


class BTKbService(dbus.service.Object):

    def __init__(self):
        print("1. Setting up service")
        # set up as a dbus service
        bus_name = dbus.service.BusName(
            "org.thanhle.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(
            self, bus_name, "/org/thanhle/btkbservice")
        # create and setup our device
        self.device = BTKbDevice()
        # start listening for connections
        self.device.listen()

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_keys(self, modifier_byte, keys):
        print("Get send_keys request through dbus")
        print("key msg: ", keys)
        state = [ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if(count < 10):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_mouse(self, modifier_byte, keys):
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if(count < 6):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)


# main routine
if __name__ == "__main__":
    # we an only run as root
    try:
        if not os.geteuid() == 0:
            sys.exit("Only root can run this script")

        if TARGET_ADDRESS == "":
            sys.exit("Please fill your host mac address in line 26")

        DBusGMainLoop(set_as_default=True)
        myservice = BTKbService()
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        sys.exit()
