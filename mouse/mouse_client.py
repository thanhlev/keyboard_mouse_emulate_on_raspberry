#!/usr/bin/python3

import logging
import re
import time
from select import select

import dbus.mainloop.glib
import dbus.service
import evdev
import pyudev
from evdev import ecodes

import dbus

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mouse_client")


class HIDInputDevice:
    inputs = []
    monitor = None

    @staticmethod
    def init():
        context = pyudev.Context()
        devs = context.list_devices(subsystem="input")
        HIDInputDevice.monitor = pyudev.Monitor.from_netlink(context)
        HIDInputDevice.monitor.filter_by(subsystem="input")
        HIDInputDevice.monitor.start()
        for d in [*devs]:
            HIDInputDevice.add_device(d)

    @staticmethod
    def add_device(dev):
        if dev.device_node is None or not re.match(r".*/event\d+", dev.device_node):
            return
        try:
            if "ID_INPUT_MOUSE" in dev.properties:
                logger.info("Detected mouse: %s", dev.device_node)
                HIDInputDevice.inputs.append(MouseInput(dev.device_node))
        except OSError:
            logger.error("Failed to connect to %s", dev.device_node)

    @staticmethod
    def remove_device(dev):
        if dev.device_node is None or not re.match(r".*/event\d+", dev.device_node):
            return
        HIDInputDevice.inputs = [
            i for i in HIDInputDevice.inputs if i.device_node != dev.device_node
        ]
        logger.info("Disconnected %s", dev)

    @staticmethod
    def set_leds_all(ledvalue):
        for dev in HIDInputDevice.inputs:
            dev.set_leds(ledvalue)

    @staticmethod
    def grab(on):
        for dev in HIDInputDevice.inputs:
            if on:
                dev.device.grab()
            else:
                dev.device.ungrab()

    def __init__(self, device_node):
        self.device_node = device_node
        self.device = evdev.InputDevice(device_node)
        self.device.grab()
        logger.info("Connected %s", self)

    def fileno(self):
        return self.device.fd

    def __str__(self):
        return "%s@%s (%s)" % (
            self.__class__.__name__,
            self.device_node,
            self.device.name,
        )


class MouseInput(HIDInputDevice):
    def __init__(self, device_node):
        super().__init__(device_node)
        self.state = [0, 0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.change = False
        self.last = 0
        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            "org.thanhle.btkbservice", "/org/thanhle/btkbservice"
        )
        self.iface = dbus.Interface(self.btkservice, "org.thanhle.btkbservice")

    def send_current(self, ir):
        try:
            self.iface.send_mouse(0, bytes(ir))
        except OSError as err:
            logger.error("Mouse send failed: %s", err)

    def change_state(self, event):
        if event.type == ecodes.EV_SYN:
            current = time.monotonic()
            diff = 20 / 1000
            if current - self.last < diff and not self.change:
                return
            self.last = current
            speed = 1
            self.state[1] = min(127, max(-127, int(self.x * speed))) & 255
            self.state[2] = min(127, max(-127, int(self.y * speed))) & 255
            self.state[3] = min(127, max(-127, self.z)) & 255
            self.x = 0
            self.y = 0
            self.z = 0
            self.change = False
            self.send_current(self.state)
        if event.type == ecodes.EV_KEY:
            logger.debug("Key event %s %d", ecodes.BTN[event.code], event.value)
            self.change = True
            if event.code >= 272 and event.code <= 276 and event.value < 2:
                button_no = event.code - 272
                if event.value == 1:
                    self.state[0] |= 1 << button_no
                else:
                    self.state[0] &= ~(1 << button_no)
        if event.type == ecodes.EV_REL:
            if event.code == 0:
                self.x += event.value
            if event.code == 1:
                self.y += event.value
            if event.code == 8:
                self.z += event.value

    def get_info(self):
        logger.debug("MouseInput info: %s", self)

    def set_leds(self, ledvalue):
        pass


if __name__ == "__main__":
    logger.info("Starting mouse client")
    HIDInputDevice.init()
    while True:
        descriptors = [*HIDInputDevice.inputs, HIDInputDevice.monitor]
        r = select(descriptors, [], [])
        for i in HIDInputDevice.inputs:
            try:
                for event in i.device.read():
                    i.change_state(event)
            except OSError as err:
                logger.warning("Read error: %s", err)
