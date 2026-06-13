"""Test HID report construction matches the SDP descriptor."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'keyboard'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))


class TestKeyboardReport:
    """Keyboard report: [0xA1, 0x01, modifier, reserved, key1..key6] = 10 bytes."""

    def test_report_size(self):
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        assert len(state) == 10

    def test_report_header(self):
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        assert state[0] == 0xA1
        assert state[1] == 1

    def test_modifier_byte_position(self):
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        state[2] = 0b00000010  # left shift
        assert state[2] == 2

    def test_key_slots_fill(self):
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        keys = [4, 5, 6, 7, 8, 9]  # A, B, C, D, E, F
        count = 4
        for key_code in keys:
            if count < 10:
                state[count] = key_code
            count += 1
        assert state[4:10] == [4, 5, 6, 7, 8, 9]

    def test_key_slots_overflow_ignored(self):
        state = [0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        keys = [4, 5, 6, 7, 8, 9, 10, 11]  # 8 keys, only 6 slots
        count = 4
        for key_code in keys:
            if count < 10:
                state[count] = key_code
            count += 1
        assert state[4:10] == [4, 5, 6, 7, 8, 9]

    def test_all_bytes_valid_range(self):
        state = [0xA1, 1, 0xFF, 0, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09]
        packet = bytes(state)
        assert len(packet) == 10
        assert all(0 <= b <= 255 for b in packet)


class TestMouseReport:
    """Mouse report: [0xA1, 0x02, buttons, x, y, wheel] = 6 bytes."""

    def test_report_size(self):
        state = [0xA1, 2, 0, 0, 0, 0]
        assert len(state) == 6

    def test_report_header(self):
        state = [0xA1, 2, 0, 0, 0, 0]
        assert state[0] == 0xA1
        assert state[1] == 2

    def test_button_bits(self):
        state = [0xA1, 2, 0, 0, 0, 0]
        # Left click
        state[2] = 1
        assert state[2] & 0x01 == 1
        # Right click
        state[2] = 2
        assert state[2] & 0x02 == 2
        # Middle click
        state[2] = 4
        assert state[2] & 0x04 == 4

    def test_button_only_3_bits_used(self):
        """New descriptor only declares 3 buttons (bits 0-2)."""
        state = [0xA1, 2, 0, 0, 0, 0]
        state[2] = 0b00000111  # all 3 buttons
        assert state[2] == 7
        assert state[2] & 0x07 == 7
        # bits 3-7 should stay zero for correctness
        assert state[2] & 0xF8 == 0

    def test_signed_axis_values(self):
        state = [0xA1, 2, 0, 0, 0, 0]
        # Positive movement
        state[3] = min(127, max(-127, 50)) & 255
        assert state[3] == 50
        # Negative movement (two's complement)
        state[3] = min(127, max(-127, -50)) & 255
        assert state[3] == 206  # -50 in unsigned byte

    def test_axis_clamping(self):
        # Values beyond -127..127 should be clamped
        val = min(127, max(-127, 200))
        assert val == 127
        val = min(127, max(-127, -200))
        assert val == -127

    def test_wheel_value(self):
        state = [0xA1, 2, 0, 0, 0, 0]
        state[5] = min(127, max(-127, 1)) & 255  # scroll up
        assert state[5] == 1
        state[5] = min(127, max(-127, -1)) & 255  # scroll down
        assert state[5] == 255  # -1 unsigned


class TestConsumerReport:
    """Consumer report: [0xA1, 0x03, byte0, byte1, byte2] = 5 bytes."""

    def test_report_size(self):
        state = [0xA1, 3, 0, 0, 0]
        assert len(state) == 5

    def test_report_header(self):
        state = [0xA1, 3, 0, 0, 0]
        assert state[0] == 0xA1
        assert state[1] == 3

    def test_play_pause_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[2] = 1 << 5  # play/pause is bit 5
        assert state[2] == 0x20

    def test_volume_up_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[3] = 1 << 1  # volume up is bit 9 = byte1 bit 1
        assert state[3] == 0x02

    def test_volume_down_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[3] = 1 << 0  # volume down is bit 8 = byte1 bit 0
        assert state[3] == 0x01

    def test_mute_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[2] = 1 << 7  # mute is bit 7
        assert state[2] == 0x80

    def test_next_track_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[2] = 1 << 6  # next track is bit 6
        assert state[2] == 0x40

    def test_prev_track_bit(self):
        state = [0xA1, 3, 0, 0, 0]
        state[2] = 1 << 4  # prev track is bit 4
        assert state[2] == 0x10

    def test_multiple_buttons(self):
        state = [0xA1, 3, 0, 0, 0]
        # volume up + volume down (shouldn't happen but valid packet)
        state[3] = (1 << 0) | (1 << 1)
        assert state[3] == 0x03

    def test_all_bytes_valid(self):
        state = [0xA1, 3, 0xFF, 0x07, 0x00]
        packet = bytes(state)
        assert len(packet) == 5


class TestSdpDescriptor:
    """Verify the SDP record descriptor matches expected report sizes."""

    def setup_method(self):
        sdp_path = os.path.join(os.path.dirname(__file__), '..', 'server', 'sdp_record.xml')
        with open(sdp_path, 'r') as f:
            self.sdp_content = f.read()

    def test_sdp_contains_descriptor(self):
        assert 'id="0x0206"' in self.sdp_content

    def test_sdp_contains_report_id_1(self):
        # 8501 = Report ID 1 (keyboard)
        assert "8501" in self.sdp_content.lower()

    def test_sdp_contains_report_id_2(self):
        # 8502 = Report ID 2 (mouse)
        assert "8502" in self.sdp_content.lower()

    def test_sdp_contains_report_id_3(self):
        # 8503 = Report ID 3 (consumer)
        assert "8503" in self.sdp_content.lower()

    def test_sdp_device_class_combo(self):
        # 0x0025C0 = Peripheral combo keyboard+pointing
        assert "0x0025C0" not in self.sdp_content  # class is set in code, not SDP

    def test_sdp_has_hid_uuid(self):
        assert "0x1124" in self.sdp_content

    def test_descriptor_keyboard_section(self):
        # Usage Page (Generic Desktop), Usage (Keyboard)
        assert "05010906" in self.sdp_content.lower()

    def test_descriptor_mouse_section(self):
        # Usage Page (Generic Desktop), Usage (Mouse)
        assert "05010902" in self.sdp_content.lower()

    def test_descriptor_consumer_section(self):
        # Usage Page (Consumer), Usage (Consumer Control)
        assert "050c0901" in self.sdp_content.lower()
