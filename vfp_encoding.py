#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_encoding.py - central encoding policy for FoxBin2Prg SC2/VC2 text.

v0.2 assumed cp1252 globally. v0.3 reads the CPID from the FoxBin2Prg header:

    *< FOXBIN2PRG: Version="..." SourceFile="..." CPID="1250" />

and maps CPID → Python codec via a central table. Polish projects are common:
  CPID 1250 → cp1250 (Windows Latin-2)
  CPID 852  → cp852  (DOS Latin-2, often used in Mazovia/VFP9 Polish installs)
  CPID 1252 → cp1252 (default Windows Latin)
  CPID 437  → cp437  (legacy DOS Latin-1)
  CPID 932/936/949/950 → CJK codepages (pass-through)

POLICY (fail-loud):
  * If the CPID is in the table → decode with that codec, errors="strict".
  * If decoding fails with errors="strict", retry with errors="replace" and
    mark the file as SUSPECT (U+FFFD artifacts) — callers should surface a
    warning/FAIL (ENCODING_CORRUPTION), never silently pass.
  * Unknown CPID → do NOT guess: report ENCODING_CORRUPTION with the file.
"""

import re

RE_HEADER = re.compile(
    r'\*<\s*FOXBIN2PRG:\s*Version="([^"]*)"\s+SourceFile="([^"]*)"\s+CPID="([^"]*)"',
    re.IGNORECASE)

# CPID → codec. Deliberately minimal; extend with a test when a new CPID
# appears in the wild. Unknown CPIDs must FAIL, not silently map to cp1252.
CPID_CODECS = {
    1250: "cp1250",
    852: "cp852",
    1252: "cp1252",
    437: "cp437",
    850: "cp850",
    855: "cp855",
    932: "cp932",
    936: "cp936",
    949: "cp949",
    950: "cp950",
}

DEFAULT_CPID = 1250  # Polish-first toolchain (see docs/ENCODING policy)


def detect_cpid(text):
    """Return the CPID (int) from the FoxBin2Prg header, or None."""
    m = RE_HEADER.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(3))
    except ValueError:
        return None


def codec_for_cpid(cpid):
    """Codec name for a CPID, or None when the mapping is unknown/unsafe."""
    if cpid is None:
        return None
    return CPID_CODECS.get(int(cpid))


def decode_sc2(raw_bytes, cpid=None, default_cpid=DEFAULT_CPID):
    """Decode raw SC2/VC2 bytes.

    Returns (text, info) where info = {
        "cpid": int, "codec": str, "suspicious": bool,
        "error": str|None, "policy": "strict"|"replace"
    }.

    NEVER raises for decode errors: the policy is fail-loud via the returned
    info (callers decide whether that is a FAIL or a Warning).
    """
    text = raw_bytes.decode("latin-1")  # lossless 1:1, just to read the header
    header_cpid = detect_cpid(text)
    cpid = header_cpid if header_cpid is not None else cpid
    if cpid is None:
        cpid = default_cpid
    codec = codec_for_cpid(cpid)
    if codec is None:
        # Unknown CPID: refuse to guess. Return latin-1 view with a loud flag.
        return (raw_bytes.decode("latin-1", "replace"),
                {"cpid": int(cpid), "codec": None, "suspicious": True,
                 "error": "unknown CPID %s — no trusted codec mapping" % cpid,
                 "policy": "none"})
    try:
        decoded = raw_bytes.decode(codec, "strict")
        return decoded, {"cpid": int(cpid), "codec": codec,
                         "suspicious": "\ufffd" in decoded,
                         "error": None, "policy": "strict"}
    except UnicodeDecodeError as e:
        decoded = raw_bytes.decode(codec, "replace")
        return decoded, {"cpid": int(cpid), "codec": codec, "suspicious": True,
                         "error": "strict decode failed: %s" % e,
                         "policy": "replace"}


def read_sc2_text(path, cpid=None):
    """Read a .sc2/.vc2 file with the central encoding policy.

    Returns (text, info). OSError on unreadable file.
    """
    with open(path, "rb") as f:
        raw = f.read()
    return decode_sc2(raw, cpid=cpid)


def is_suspicious(info):
    """True when the decode result must be surfaced (U+FFFD / unknown codec)."""
    if not info:
        return True
    return bool(info.get("suspicious") or info.get("error") or info.get("codec") is None)
