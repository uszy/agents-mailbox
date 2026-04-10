"""Tests for the terminal-output sanitization function."""
from sanitize import sanitize_for_terminal


def test_plain_ascii_unchanged():
    assert sanitize_for_terminal('hello world') == 'hello world'


def test_newlines_and_tabs_preserved():
    assert sanitize_for_terminal('hello\nworld\ttab') == 'hello\nworld\ttab'


def test_unicode_preserved():
    assert sanitize_for_terminal('café résumé 日本語') == 'café résumé 日本語'


def test_escape_character_is_replaced():
    """ESC (0x1b) is the core of ANSI attacks and must be neutralized."""
    result = sanitize_for_terminal('\x1b[2Jhacked')
    assert '\x1b' not in result
    assert '\\x1b' in result
    assert 'hacked' in result


def test_all_control_chars_except_newline_tab_replaced():
    """Every control char 0x00-0x1F and 0x7F except \\n (0x09→tab, 0x0a→newline) gets escaped."""
    for code in list(range(0x00, 0x20)) + [0x7F]:
        if code in (0x09, 0x0a):
            continue
        ch = chr(code)
        result = sanitize_for_terminal(f'before{ch}after')
        assert ch not in result, f'control char 0x{code:02x} leaked through'
        assert f'\\x{code:02x}' in result


def test_osc_52_clipboard_hijack_neutralized():
    """OSC 52 clipboard injection sequence must be broken."""
    payload = '\x1b]52;c;cm0gLXJmIH4=\x07'
    result = sanitize_for_terminal(payload)
    assert '\x1b' not in result
    assert '\x07' not in result


def test_cursor_move_sequence_neutralized():
    """Cursor movement sequences can hide content — must be broken."""
    result = sanitize_for_terminal('top\x1b[1A\x1b[Koverwritten')
    assert '\x1b' not in result


def test_empty_string():
    assert sanitize_for_terminal('') == ''


def test_only_control_chars():
    result = sanitize_for_terminal('\x1b\x1b\x1b')
    assert result == '\\x1b\\x1b\\x1b'
