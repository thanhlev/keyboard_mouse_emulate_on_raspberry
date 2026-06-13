"""Test send_string character-to-scancode logic without D-Bus."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'keyboard'))

import keymap


class FakeSendString:
    """Replicate BtkStringClient scancode logic for testing."""

    SCANCODES = {
        "-": "KEY_MINUS",
        "=": "KEY_EQUAL",
        ";": "KEY_SEMICOLON",
        "'": "KEY_APOSTROPHE",
        "`": "KEY_GRAVE",
        "\\": "KEY_BACKSLASH",
        ",": "KEY_COMMA",
        ".": "KEY_DOT",
        "/": "KEY_SLASH",
        "_": "key_minus",
        "+": "key_equal",
        ":": "key_semicolon",
        "\"": "key_apostrophe",
        "~": "key_grave",
        "|": "key_backslash",
        "<": "key_comma",
        ">": "key_dot",
        "?": "key_slash",
        " ": "KEY_SPACE",
    }

    @staticmethod
    def resolve_char(c):
        """Returns (scancode, needs_shift) or raises KeyError."""
        cu = c.upper()
        modifiers = [0, 0, 0, 0, 0, 0, 0, 0]
        if cu in FakeSendString.SCANCODES:
            scantablekey = FakeSendString.SCANCODES[cu]
            if scantablekey.islower():
                modifiers = [0, 0, 0, 0, 0, 0, 1, 0]
                scantablekey = scantablekey.upper()
        else:
            if c.isupper():
                modifiers = [0, 0, 0, 0, 0, 0, 1, 0]
            scantablekey = "KEY_" + cu
        scancode = keymap.keytable[scantablekey]
        needs_shift = modifiers[6] == 1
        return scancode, needs_shift


class TestSendStringResolution:
    def test_lowercase_letters(self):
        for c in "abcdefghijklmnopqrstuvwxyz":
            scancode, shift = FakeSendString.resolve_char(c)
            assert not shift
            assert scancode == keymap.keytable["KEY_" + c.upper()]

    def test_uppercase_letters(self):
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            scancode, shift = FakeSendString.resolve_char(c)
            assert shift
            assert scancode == keymap.keytable["KEY_" + c]

    def test_digits(self):
        for c in "0123456789":
            scancode, shift = FakeSendString.resolve_char(c)
            assert not shift
            assert scancode == keymap.keytable["KEY_" + c]

    def test_space(self):
        scancode, shift = FakeSendString.resolve_char(" ")
        assert scancode == keymap.keytable["KEY_SPACE"]
        assert not shift

    def test_shifted_symbols(self):
        shifted = {"_": "KEY_MINUS", "+": "KEY_EQUAL", ":": "KEY_SEMICOLON",
                   "\"": "KEY_APOSTROPHE", "~": "KEY_GRAVE", "|": "KEY_BACKSLASH",
                   "<": "KEY_COMMA", ">": "KEY_DOT", "?": "KEY_SLASH"}
        for char, expected_key in shifted.items():
            scancode, shift = FakeSendString.resolve_char(char)
            assert shift, f"'{char}' should require shift"
            assert scancode == keymap.keytable[expected_key]

    def test_unshifted_symbols(self):
        unshifted = {"-": "KEY_MINUS", "=": "KEY_EQUAL", ";": "KEY_SEMICOLON",
                     "'": "KEY_APOSTROPHE", "`": "KEY_GRAVE", "\\": "KEY_BACKSLASH",
                     ",": "KEY_COMMA", ".": "KEY_DOT", "/": "KEY_SLASH"}
        for char, expected_key in unshifted.items():
            scancode, shift = FakeSendString.resolve_char(char)
            assert not shift, f"'{char}' should not require shift"
            assert scancode == keymap.keytable[expected_key]

    def test_invalid_char_raises_keyerror(self):
        try:
            FakeSendString.resolve_char("\x01")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass


class TestProxyKeyboardResolution:
    """Test proxy_keyboard.py scancode resolution (uses different mapping)."""

    SCANCODES = {
        " ": "KEY_SPACE", "!": "KEY_1", "@": "KEY_2", "#": "KEY_3",
        "$": "KEY_4", "%": "KEY_5", "^": "KEY_6", "&": "KEY_7",
        "*": "KEY_8", "(": "KEY_9", ")": "KEY_0", "-": "KEY_MINUS",
        "_": "KEY_MINUS", "=": "KEY_EQUAL", "+": "KEY_EQUAL",
        "[": "KEY_LEFTBRACE", "{": "KEY_LEFTBRACE", "]": "KEY_RIGHTBRACE",
        "}": "KEY_RIGHTBRACE", "\\": "KEY_BACKSLASH", "|": "KEY_BACKSLASH",
        ";": "KEY_SEMICOLON", ":": "KEY_SEMICOLON", "'": "KEY_APOSTROPHE",
        "\"": "KEY_APOSTROPHE", "`": "KEY_GRAVE", "~": "KEY_GRAVE",
        ",": "KEY_COMMA", "<": "KEY_COMMA", ".": "KEY_DOT",
        ">": "KEY_DOT", "/": "KEY_SLASH", "?": "KEY_SLASH",
    }
    SHIFTED = '!@#$%^&*()_+{}|:"~<>?'

    @classmethod
    def resolve_char(cls, c):
        modifiers = [0, 0, 0, 0, 0, 0, 0, 0]
        if c.isupper() or c in cls.SHIFTED:
            modifiers = [0, 0, 0, 0, 0, 0, 1, 0]
        scantablekey = f"KEY_{c.upper()}"
        if c in cls.SCANCODES:
            scantablekey = cls.SCANCODES[c]
        scancode = keymap.convert(scantablekey)
        return scancode, modifiers[6] == 1

    def test_lowercase_letters(self):
        for c in "abcdefghijklmnopqrstuvwxyz":
            scancode, shift = self.resolve_char(c)
            assert not shift
            assert scancode > 0

    def test_uppercase_letters_need_shift(self):
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            scancode, shift = self.resolve_char(c)
            assert shift

    def test_number_row_symbols_need_shift(self):
        for c in "!@#$%^&*()":
            scancode, shift = self.resolve_char(c)
            assert shift, f"'{c}' should require shift"

    def test_bracket_chars(self):
        scancode_open, shift = self.resolve_char("[")
        assert not shift
        assert scancode_open == keymap.keytable["KEY_LEFTBRACE"]
        scancode_close, shift = self.resolve_char("{")
        assert shift
        assert scancode_close == keymap.keytable["KEY_LEFTBRACE"]

    def test_all_printable_ascii_resolve(self):
        failed = []
        for i in range(32, 127):
            c = chr(i)
            try:
                self.resolve_char(c)
            except KeyError:
                failed.append(c)
        assert failed == [], f"Characters without mapping: {failed}"
