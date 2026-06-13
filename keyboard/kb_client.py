#!/usr/bin/python3
#
# Thanhle Bluetooth keyboard emulation service
# keyboard copy client.
# Reads local key events and forwards them to the btk_server DBUS service
#
import time
import dbus
import dbus.service
import dbus.mainloop.glib
import evdev
from evdev import ecodes, InputDevice
import keymap


# Define a client to listen to local key events
class Keyboard():

    def __init__(self):
        # the structure for a bt keyboard input report (size is 10 bytes)

        self.state = [
            0xA1,  # this is an input report
            0x01,  # Usage report = Keyboard
            # Bit array for Modifier keys
            [0,  # Right GUI - Windows Key
             0,  # Right ALT
             0,  # Right Shift
             0,  # Right Control
             0,  # Left GUI
             0,  # Left ALT
             0,  # Left Shift
             0],  # Left Control
            0x00,  # Vendor reserved
            0x00,  # rest is space for 6 keys
            0x00,
            0x00,
            0x00,
            0x00,
            0x00]

        print("setting up DBus Client")

        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            'org.thanhle.btkbservice', '/org/thanhle/btkbservice')
        self.iface = dbus.Interface(self.btkservice, 'org.thanhle.btkbservice')
        print("waiting for keyboard")
        while True:
            try:
                self.dev = InputDevice("/dev/input/event0")
                print("found a keyboard")
                break
            except OSError:
                print("Keyboard not found, waiting 3 seconds and retrying")
                time.sleep(3)

    def change_state(self, event):
        evdev_code = ecodes.KEY[event.code]
        modkey_element = keymap.modkey(evdev_code)

        if modkey_element > 0:
            if self.state[2][modkey_element] == 0:
                self.state[2][modkey_element] = 1
            else:
                self.state[2][modkey_element] = 0
        else:
            # Get the keycode of the key
            hex_key = keymap.convert(ecodes.KEY[event.code])
            # Loop through elements 4 to 9 of the inport report structure
            for i in range(4, 10):
                if self.state[i] == hex_key and event.value == 0:
                    # Code 0 so we need to depress it
                    self.state[i] = 0x00
                elif self.state[i] == 0x00 and event.value == 1:
                    # if the current space if empty and the key is being pressed
                    self.state[i] = hex_key
                    break

    # poll for keyboard events
    def event_loop(self):
        for event in self.dev.read_loop():
            # only bother if we hit a key and its an up or down event
            if event.type == ecodes.EV_KEY and event.value < 2:
                self.change_state(event)
                self.send_input()

    # forward keyboard events to the dbus service
    def send_input(self):
        bin_str = ""
        element = self.state[2]
        for bit in element:
            bin_str += str(bit)
        a = self.state
        print(*a)
        self.iface.send_keys(int(bin_str, 2), self.state[4:10])


if __name__ == "__main__":

    print("Setting up keyboard")

    kb = Keyboard()

    print("starting event loop")
    kb.event_loop()
