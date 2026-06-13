#!/usr/bin/python3

import logging
import sys

import dbus.mainloop.glib

import dbus

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mouse_emulate")


class MouseClient:
    def __init__(self):
        self.state = [0, 0, 0, 0]
        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            "org.thanhle.btkbservice", "/org/thanhle/btkbservice"
        )
        self.iface = dbus.Interface(self.btkservice, "org.thanhle.btkbservice")

    def send_current(self):
        try:
            self.iface.send_mouse(0, bytes(self.state))
        except OSError as err:
            logger.error("Mouse send failed: %s", err)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        logger.error("Usage: mouse_emulate [button_num dx dy dz]")
        sys.exit(1)
    client = MouseClient()
    client.state[0] = int(sys.argv[1])
    client.state[1] = int(sys.argv[2])
    client.state[2] = int(sys.argv[3])
    client.state[3] = int(sys.argv[4])
    logger.debug("State: %s", client.state)
    client.send_current()
