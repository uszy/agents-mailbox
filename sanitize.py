"""Sanitize arbitrary strings for safe terminal display.

The agent mailbox accepts message bodies and header values from hostile
HTTP clients. When read.py prints those fields to the operator's
terminal, an unsanitized value containing ANSI escape sequences would be
interpreted by the terminal -- enabling screen clearing, cursor-move hijack,
OSC 52 clipboard injection, and similar attacks.

This module provides sanitize_for_terminal, which replaces every control
character in 0x00-0x1F and 0x7F (with the exception of newline and tab)
with its literal \\xNN form.
"""

_ALLOW_CONTROL = frozenset({'\n', '\t'})


def sanitize_for_terminal(s: str) -> str:
    """Return a copy of s safe to print to a terminal.

    Replaces every character in 0x00-0x1F and 0x7F (except newline and tab)
    with a literal \\xNN sequence. All other characters (including full
    Unicode) pass through unchanged.
    """
    out: list[str] = []
    for ch in s:
        code = ord(ch)
        if ch in _ALLOW_CONTROL:
            out.append(ch)
        elif code < 0x20 or code == 0x7F:
            out.append(f'\\x{code:02x}')
        else:
            out.append(ch)
    return ''.join(out)
