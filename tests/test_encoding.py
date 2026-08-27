"""Tests for the central encoding policy (CPID → codec, fail-loud)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_encoding as enc


def _sc2(cpid, body_bytes):
    header = ('*< FOXBIN2PRG: Version="5.x" SourceFile="X.SCX" CPID="%d" />' % cpid).encode("ascii")
    return header + b"\r\n" + body_bytes


def test_cpid_1250_decodes_polish():
    body = "Caption = 'W\u0142a\u015bci'"  # correct cp1250 polish
    raw = _sc2(1250, body.encode("cp1250"))
    text, info = enc.decode_sc2(raw)
    assert info["codec"] == "cp1250"
    assert info["suspicious"] is False
    assert "W\u0142a\u015bci" in text


def test_cpid_852_decodes():
    body = "x = 'szu\u0142ek'"
    raw = _sc2(852, body.encode("cp852"))
    text, info = enc.decode_sc2(raw)
    assert info["codec"] == "cp852"
    assert info["suspicious"] is False


def test_cpid_1252_decodes():
    raw = _sc2(1252, b"y = 1")
    _text, info = enc.decode_sc2(raw)
    assert info["codec"] == "cp1252"


def test_unknown_cpid_fails_loud():
    raw = _sc2(9999, b"z = 2")
    _text, info = enc.decode_sc2(raw)
    assert info["codec"] is None
    assert info["suspicious"] is True
    assert enc.is_suspicious(info) is True


def test_bad_bytes_marked_suspicious():
    # cp1250 file containing 0x81 (undefined in cp1250) -> strict fails ->
    # fallback to replace → U+FFFD → flagged suspicious
    raw = _sc2(1250, b"bad byte \x81 here")
    _text, info = enc.decode_sc2(raw)
    assert enc.is_suspicious(info) is True


def test_detect_cpid_from_header():
    text = '*< FOXBIN2PRG: Version="5.0" SourceFile="A.SCX" CPID="1250" />'
    assert enc.detect_cpid(text) == 1250
    assert enc.detect_cpid("no header") is None


def test_read_sc2_text_file(tmp_path):
    body = "Caption = 'W\u0142a\u015bci'"
    raw = _sc2(1250, body.encode("cp1250"))
    p = tmp_path / "form.sc2"
    p.write_bytes(raw)
    text, info = enc.read_sc2_text(str(p))
    assert info["codec"] == "cp1250"
    assert "W\u0142a\u015bci" in text
    assert enc.is_suspicious(info) is False
