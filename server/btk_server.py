#!/usr/bin/python3
#
# Bluetooth keyboard/Mouse emulator DBUS Service
#

import logging
import os
import socket
import subprocess
import sys

import dbus.mainloop.glib
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

import dbus

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("btk_server")

# @todo fill your host mac here manually
TARGET_ADDRESS = ""


class BTKbDevice:
    # change these constants
    MY_ADDRESS = "B8:27:EB:C5:B3:27"
    MY_DEV_NAME = "ThanhLe_Keyboard_Mouse"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Interrupt port - must match port configured in SDP record
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        logger.info("Setting up BT device")
        self.init_bt_device()
        self.init_bluez_profile()

    def init_bt_device(self):
        logger.info("Configuring device name: %s", BTKbDevice.MY_DEV_NAME)
        subprocess.run(["hciconfig", "hci0", "up"], check=False)
        subprocess.run(
            ["hciconfig", "hci0", "name", BTKbDevice.MY_DEV_NAME], check=False
        )
        subprocess.run(["hciconfig", "hci0", "piscan"], check=False)

    def init_bluez_profile(self):
        logger.info("Configuring Bluez Profile")
        service_record = self.read_sdp_service_record()
        opts = {"AutoConnect": True, "ServiceRecord": service_record}
        bus = dbus.SystemBus()
        manager = dbus.Interface(
            bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1"
        )
        manager.RegisterProfile("/org/bluez/hci0", BTKbDevice.UUID, opts)
        logger.info("Profile registered")
        subprocess.run(["hciconfig", "hci0", "class", "0x002540"], check=False)

    def read_sdp_service_record(self):
        logger.debug("Reading SDP service record from %s", BTKbDevice.SDP_RECORD_PATH)
        try:
            with open(BTKbDevice.SDP_RECORD_PATH, "r") as fh:
                return fh.read()
        except OSError:
            logger.critical("Could not open the sdp record. Exiting...")
            sys.exit(1)

    def setup_socket(self):
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )  # BluetoothSocket(L2CAP)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )  # BluetoothSocket(L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind these sockets to a port - port zero to select next available
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
        self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))

    def listen(self):
        logger.warning("Waiting for connections...")

        self.setup_socket()
        try:
            self.scontrol.connect((TARGET_ADDRESS, self.P_CTRL))
        except socket.error as err:
            logger.debug("Initial connect attempt failed (expected): %s", err)

        self.setup_socket()

        self.scontrol.listen(5)
        self.sinterrupt.listen(5)

        self.ccontrol, cinfo = self.scontrol.accept()
        logger.info("Connection on control channel from %s", cinfo[0])

        self.cinterrupt, cinfo = self.sinterrupt.accept()
        logger.info("Connection on interrupt channel from %s", cinfo[0])

    def send_string(self, message):
        try:
            self.cinterrupt.send(bytes(message))
        except OSError as err:
            logger.error("Send failed: %s", err)
            self.reconnect()

    def reconnect(self):
        logger.warning("Reconnecting...")
        for sock in [
            getattr(self, "ccontrol", None),
            getattr(self, "cinterrupt", None),
            getattr(self, "scontrol", None),
            getattr(self, "sinterrupt", None),
        ]:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        self.listen()


class BTKbService(dbus.service.Object):

    def __init__(self):
        logger.info("Setting up DBus service")
        bus_name = dbus.service.BusName("org.thanhle.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, "/org/thanhle/btkbservice")
        self.device = BTKbDevice()
        self.device.listen()

    @dbus.service.method("org.thanhle.btkbservice", in_signature="yay")
    def send_keys(self, modifier_byte, keys):
        logger.debug("send_keys: modifier=%s keys=%s", modifier_byte, list(keys))
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if count < 10:
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)

    @dbus.service.method("org.thanhle.btkbservice", in_signature="yay")
    def send_mouse(self, modifier_byte, keys):
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if count < 6:
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)

    @dbus.service.method("org.thanhle.btkbservice", in_signature="ay")
    def send_consumer(self, keys):
        logger.debug("send_consumer: keys=%s", list(keys))
        state = [0xA1, 3, 0, 0, 0]
        state[2] = int(keys[0]) if len(keys) > 0 else 0
        state[3] = int(keys[1]) if len(keys) > 1 else 0
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
