"""Test mouse state machine logic without hardware/dbus."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mouse'))


class FakeEvent:
    def __init__(self, type, code, value):
        self.type = type
        self.code = code
        self.value = value


# evdev ecodes constants (subset needed for tests)
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
BTN_LEFT = 272
BTN_RIGHT = 273
BTN_MIDDLE = 274
REL_X = 0
REL_Y = 1
REL_WHEEL = 8


class MouseState:
    """Replicate MouseInput.change_state logic for unit testing."""

    def __init__(self):
        self.state = [0, 0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.change = False
        self.last = 0
        self.sent = []

    def send_current(self, ir):
        self.sent.append(list(ir))

    def change_state(self, event):
        if event.type == EV_SYN:
            speed = 1
            self.state[1] = min(127, max(-127, int(self.x * speed))) & 255
            self.state[2] = min(127, max(-127, int(self.y * speed))) & 255
            self.state[3] = min(127, max(-127, self.z)) & 255
            self.x = 0
            self.y = 0
            self.z = 0
            self.change = False
            self.send_current(self.state)
        if event.type == EV_KEY:
            self.change = True
            if event.code >= 272 and event.code <= 274 and event.value < 2:
                button_no = event.code - 272
                if event.value == 1:
                    self.state[0] |= 1 << button_no
                else:
                    self.state[0] &= ~(1 << button_no)
        if event.type == EV_REL:
            if event.code == 0:
                self.x += event.value
            if event.code == 1:
                self.y += event.value
            if event.code == 8:
                self.z += event.value


class TestMouseButtons:
    def test_left_click(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_LEFT, 1))
        assert m.state[0] == 0x01

    def test_right_click(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_RIGHT, 1))
        assert m.state[0] == 0x02

    def test_middle_click(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_MIDDLE, 1))
        assert m.state[0] == 0x04

    def test_left_release(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_LEFT, 1))
        m.change_state(FakeEvent(EV_KEY, BTN_LEFT, 0))
        assert m.state[0] == 0x00

    def test_multiple_buttons(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_LEFT, 1))
        m.change_state(FakeEvent(EV_KEY, BTN_RIGHT, 1))
        assert m.state[0] == 0x03

    def test_button_beyond_3_ignored(self):
        m = MouseState()
        # Button 4 (code 275) should be ignored with clamped range
        m.change_state(FakeEvent(EV_KEY, 275, 1))
        assert m.state[0] == 0x00

    def test_button_5_ignored(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, 276, 1))
        assert m.state[0] == 0x00


class TestMouseMovement:
    def test_x_movement(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_X, 10))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][1] == 10

    def test_y_movement(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_Y, -20))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][2] == (-20 & 255)

    def test_wheel_scroll(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_WHEEL, 1))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][3] == 1

    def test_movement_accumulates(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_X, 5))
        m.change_state(FakeEvent(EV_REL, REL_X, 7))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][1] == 12

    def test_movement_resets_after_syn(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_X, 50))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][1] == 0

    def test_clamping_positive(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_X, 200))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][1] == 127

    def test_clamping_negative(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_REL, REL_X, -200))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][1] == (-127 & 255)

    def test_combined_movement_and_button(self):
        m = MouseState()
        m.change_state(FakeEvent(EV_KEY, BTN_LEFT, 1))
        m.change_state(FakeEvent(EV_REL, REL_X, 5))
        m.change_state(FakeEvent(EV_REL, REL_Y, -3))
        m.change_state(FakeEvent(EV_SYN, 0, 0))
        assert m.sent[-1][0] == 0x01
        assert m.sent[-1][1] == 5
        assert m.sent[-1][2] == (-3 & 255)
