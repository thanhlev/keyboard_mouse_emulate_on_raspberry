#!/usr/bin/python3
import logging
import sys
import termios
import time
import tty

import dbus.mainloop.glib
import dbus.service
import keymap

import dbus

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("proxy_keyboard")


class BtkStringClient:
    KEY_DOWN_TIME = 0.01
    KEY_DELAY = 0.01

    def __init__(self):
        self.state = [
            0xA1,
            0x01,
            [0, 0, 0, 0, 0, 0, 0, 0],
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
        self.scancodes = {
            " ": "KEY_SPACE",
            "!": "KEY_1",
            "@": "KEY_2",
            "#": "KEY_3",
            "$": "KEY_4",
            "%": "KEY_5",
            "^": "KEY_6",
            "&": "KEY_7",
            "*": "KEY_8",
            "(": "KEY_9",
            ")": "KEY_0",
            "-": "KEY_MINUS",
            "_": "KEY_MINUS",
            "=": "KEY_EQUAL",
            "+": "KEY_EQUAL",
            "[": "KEY_LEFTBRACE",
            "{": "KEY_LEFTBRACE",
            "]": "KEY_RIGHTBRACE",
            "}": "KEY_RIGHTBRACE",
            "\\": "KEY_BACKSLASH",
            "|": "KEY_BACKSLASH",
            ";": "KEY_SEMICOLON",
            ":": "KEY_SEMICOLON",
            "'": "KEY_APOSTROPHE",
            '"': "KEY_APOSTROPHE",
            "`": "KEY_GRAVE",
            "~": "KEY_GRAVE",
            ",": "KEY_COMMA",
            "<": "KEY_COMMA",
            ".": "KEY_DOT",
            ">": "KEY_DOT",
            "/": "KEY_SLASH",
            "?": "KEY_SLASH",
        }
        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            "org.thanhle.btkbservice", "/org/thanhle/btkbservice"
        )
        self.iface = dbus.Interface(self.btkservice, "org.thanhle.btkbservice")

    def send_key_state(self):
        bin_str = "".join(map(str, self.state[2]))
        self.iface.send_keys(int(bin_str, 2), self.state[4:10])

    def send_key_down(self, scancode, modifiers):
        self.state[2] = modifiers
        self.state[4] = scancode
        self.send_key_state()

    def send_key_up(self):
        self.state[4] = 0
        self.send_key_state()

    def send_char(self, c):
        modifiers = [0, 0, 0, 0, 0, 0, 0, 0]
        if c.isupper() or c in '!@#$%^&*()_+{}|:"~<>?':
            modifiers = [0, 0, 0, 0, 0, 0, 1, 0]

        scantablekey = f"KEY_{c.upper()}"
        if c in self.scancodes:
            scantablekey = self.scancodes[c]

        try:
            scancode = keymap.convert(scantablekey)
            self.send_key_down(scancode, modifiers)
            time.sleep(BtkStringClient.KEY_DOWN_TIME)
            self.send_key_up()
            time.sleep(BtkStringClient.KEY_DELAY)
        except KeyError:
            logger.warning("Unsupported character: %r", c)

    def send_enter(self):
        scancode = keymap.convert("KEY_ENTER")
        self.send_key_down(scancode, [0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(BtkStringClient.KEY_DOWN_TIME)
        self.send_key_up()
        time.sleep(BtkStringClient.KEY_DELAY)

    def send_backspace(self):
        self.send_key(keymap.convert("KEY_BACKSPACE"))

    def send_key(self, scancode):
        self.send_key_down(scancode, [0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(BtkStringClient.KEY_DOWN_TIME)
        self.send_key_up()
        time.sleep(BtkStringClient.KEY_DELAY)

    def send_up(self):
        self.send_key(keymap.convert("KEY_UP"))

    def send_down(self):
        self.send_key(keymap.convert("KEY_DOWN"))

    def send_left(self):
        self.send_key(keymap.convert("KEY_LEFT"))

    def send_right(self):
        self.send_key(keymap.convert("KEY_RIGHT"))


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


if __name__ == "__main__":
    logger.info("Starting Bluetooth Keyboard Proxy (Ctrl+C to exit)")
    client = BtkStringClient()

    while True:
        char = getch()
        if char == "\x1b[A":
            client.send_up()
        elif char == "\x1b[B":
            client.send_down()
        elif char == "\x1b[C":
            client.send_right()
        elif char == "\x1b[D":
            client.send_left()
        elif len(char) == 1 and ord(char) == 3:  # Ctrl+C
            break
        elif len(char) == 1 and ord(char) == 13:  # Enter
            client.send_enter()
            print()  # Move to the next line
        elif len(char) == 1 and ord(char) == 127:  # Backspace
            client.send_backspace()
            # Move cursor back, print space, and move back again
            print("\b \b", end="", flush=True)
        else:
            client.send_char(char)
            print(char, end="", flush=True)
