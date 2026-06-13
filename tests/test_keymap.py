import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'keyboard'))

import keymap


class TestKeymapConvert:
    def test_convert_letters(self):
        assert keymap.convert("KEY_A") == 4
        assert keymap.convert("KEY_Z") == 29
        assert keymap.convert("KEY_M") == 16

    def test_convert_numbers(self):
        assert keymap.convert("KEY_1") == 30
        assert keymap.convert("KEY_0") == 39

    def test_convert_special_keys(self):
        assert keymap.convert("KEY_ENTER") == 40
        assert keymap.convert("KEY_SPACE") == 44
        assert keymap.convert("KEY_BACKSPACE") == 42
        assert keymap.convert("KEY_TAB") == 43
        assert keymap.convert("KEY_ESC") == 41

    def test_convert_function_keys(self):
        assert keymap.convert("KEY_F1") == 58
        assert keymap.convert("KEY_F12") == 69
        assert keymap.convert("KEY_F24") == 115

    def test_convert_arrow_keys(self):
        assert keymap.convert("KEY_UP") == 82
        assert keymap.convert("KEY_DOWN") == 81
        assert keymap.convert("KEY_LEFT") == 80
        assert keymap.convert("KEY_RIGHT") == 79

    def test_convert_modifier_keys(self):
        assert keymap.convert("KEY_LEFTCTRL") == 224
        assert keymap.convert("KEY_LEFTSHIFT") == 225
        assert keymap.convert("KEY_LEFTALT") == 226
        assert keymap.convert("KEY_LEFTMETA") == 227

    def test_convert_invalid_key_raises(self):
        try:
            keymap.convert("KEY_NONEXISTENT")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass


class TestKeymapModkey:
    def test_modkey_left_modifiers(self):
        assert keymap.modkey("KEY_LEFTCTRL") == 7
        assert keymap.modkey("KEY_LEFTSHIFT") == 6
        assert keymap.modkey("KEY_LEFTALT") == 5
        assert keymap.modkey("KEY_LEFTMETA") == 4

    def test_modkey_right_modifiers(self):
        assert keymap.modkey("KEY_RIGHTCTRL") == 3
        assert keymap.modkey("KEY_RIGHTSHIFT") == 2
        assert keymap.modkey("KEY_RIGHTALT") == 1
        assert keymap.modkey("KEY_RIGHTMETA") == 0

    def test_modkey_non_modifier_returns_negative(self):
        assert keymap.modkey("KEY_A") == -1
        assert keymap.modkey("KEY_SPACE") == -1
        assert keymap.modkey("KEY_ENTER") == -1

    def test_modkey_unknown_key_returns_negative(self):
        assert keymap.modkey("KEY_NONEXISTENT") == -1


class TestKeymapCompleteness:
    def test_all_keytable_values_are_integers(self):
        for key, val in keymap.keytable.items():
            assert isinstance(val, int), f"{key} has non-int value: {val}"
            assert 0 <= val <= 255, f"{key} has out-of-range value: {val}"

    def test_all_modkeys_values_are_valid_indices(self):
        for key, val in keymap.modkeys.items():
            assert isinstance(val, int)
            assert 0 <= val <= 7, f"{key} has invalid index: {val}"

    def test_modkeys_are_in_keytable(self):
        for key in keymap.modkeys:
            assert key in keymap.keytable, f"Modifier {key} not in keytable"

    def test_no_duplicate_hid_codes(self):
        values = list(keymap.keytable.values())
        non_zero = [v for v in values if v != 0]
        assert len(non_zero) == len(set(non_zero)), "Duplicate HID codes in keytable"
